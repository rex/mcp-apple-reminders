"""Hybrid list-icon suggester: curated table → MCP sampling → agent fallback.

`suggest_icons` is the pure, offline matcher — it tokenises a list title and
ranks SF Symbols from `icon_catalog.ICON_KEYWORDS`. `resolve_icon` is the async
policy the create tools use: it honours an explicit icon, else does silent
best-effort (confident table match; on a miss, MCP Sampling *constrained to the
catalog*; on a final miss, the agent-fallback glyph), or elicits a choice when
`icon="ask"`. `apply_list_icon` writes the chosen badge via the ReminderKit
helper, degrading gracefully (warn, don't fail) if the helper is unavailable.

Sampling and elicitation are best-effort: clients that don't support them fall
through to the deterministic table + fallback, so list creation never breaks.
"""

from __future__ import annotations

import re
from typing import Optional

from mcp import types as mcp_types
from mcp.server.fastmcp import Context
from pydantic import BaseModel, Field

from ._native.reminderkit import ReminderKitHelperError, ReminderKitHelperUnavailable
from ._native.reminderkit_lists import set_list_appearance as _helper_set_list_appearance
from .icon_catalog import AGENT_FALLBACK_SYMBOL, ICON_KEYWORDS

# `icon` argument sentinels (case-insensitive). Anything else is treated as an
# explicit SF Symbol name (ascii) or emoji.
_AUTO = "auto"
_ASK = "ask"
_NONE = {"none", "off", ""}

# SF Symbol names are lowercase letters, digits and dots; everything else
# (non-ascii) is treated as an emoji.
_SYMBOL_RE = re.compile(r"^[a-z0-9.]+$")
_WORD_RE = re.compile(r"[a-z0-9]+")

# Connective words that should never score.
_STOP = {"the", "a", "an", "and", "or", "of", "for", "to", "my", "our", "list", "lists"}

# Catalog symbols as the constrained option set for sampling.
ALL_SYMBOLS: tuple[str, ...] = tuple(ICON_KEYWORDS.keys())
_SYMBOL_SET = set(ALL_SYMBOLS)


class IconSuggestion(BaseModel):
    """One ranked icon candidate for a title."""

    symbol: str
    score: int
    matched: list[str] = Field(default_factory=list)


class IconSuggestionResult(BaseModel):
    """Ranked SF Symbol candidates for a list title, plus the agent fallback."""

    title: str
    candidates: list[IconSuggestion] = Field(default_factory=list)
    recommended: str
    fallback: str = AGENT_FALLBACK_SYMBOL
    confident: bool = False


class ResolvedIcon(BaseModel):
    """The icon the create tools should apply, and how it was chosen."""

    symbol: Optional[str] = None
    emoji: Optional[str] = None
    source: str  # explicit | matched | sampled | fallback | asked | none


class _IconChoice(BaseModel):
    """Elicitation schema — the user accepts the suggestion or edits the symbol."""

    symbol: str = Field(description="SF Symbol name (or emoji) for the list icon.")


def _tokens(title: str) -> list[str]:
    """Lowercase word tokens of a title, minus stopwords."""
    return [w for w in _WORD_RE.findall(title.lower()) if w not in _STOP]


def _singular(word: str) -> str:
    """Tiny plural→singular heuristic (no external dependency)."""
    if word.endswith("ies") and len(word) > 4:
        return word[:-3] + "y"
    if word.endswith("es") and len(word) > 4:
        return word[:-2]
    if word.endswith("s") and len(word) > 3:
        return word[:-1]
    return word


def suggest_icons(title: str, limit: int = 5) -> IconSuggestionResult:
    """Rank catalog SF Symbols for `title` (pure, offline, deterministic)."""
    toks = _tokens(title)
    forms = set(toks) | {_singular(t) for t in toks}
    ranked: list[IconSuggestion] = []
    for symbol, keywords in ICON_KEYWORDS.items():
        hits = sorted(forms & set(keywords))
        if hits:
            ranked.append(IconSuggestion(symbol=symbol, score=len(hits), matched=hits))
    # Stable sort by score desc keeps catalog order within a score tier.
    ranked.sort(key=lambda c: c.score, reverse=True)
    top = ranked[: max(0, limit)]
    confident = bool(top) and top[0].score >= 1
    recommended = top[0].symbol if confident else AGENT_FALLBACK_SYMBOL
    return IconSuggestionResult(
        title=title,
        candidates=top,
        recommended=recommended,
        fallback=AGENT_FALLBACK_SYMBOL,
        confident=confident,
    )


def _looks_like_emoji(value: str) -> bool:
    """True when `value` is not a bare SF Symbol name (so: treat it as emoji)."""
    return not bool(_SYMBOL_RE.match(value))


async def _sample_icon(ctx: Context, title: str) -> Optional[str]:
    """Ask the client's LLM to pick one catalog symbol for `title`.

    Constrained to `ALL_SYMBOLS`, so any accepted reply is a real SF Symbol.
    Returns None when sampling is unsupported, errors, or nothing fits.
    """
    prompt = (
        "Choose the single best SF Symbol icon for an Apple Reminders list titled "
        f"'{title}'. Reply with EXACTLY one symbol name copied verbatim from this "
        f"list, or the word NONE if nothing fits.\n\nOptions: {', '.join(ALL_SYMBOLS)}"
    )
    try:
        result = await ctx.session.create_message(
            messages=[
                mcp_types.SamplingMessage(
                    role="user",
                    content=mcp_types.TextContent(type="text", text=prompt),
                ),
            ],
            max_tokens=16,
            temperature=0.0,
        )
    except AttributeError:
        await ctx.debug("suggest icon: sampling unsupported on this session; using fallback.")
        return None
    except Exception as e:  # best-effort: any sampling failure degrades to fallback
        await ctx.debug(f"suggest icon: sampling failed ({e}); using fallback.")
        return None

    text = ""
    if isinstance(result.content, mcp_types.TextContent):
        text = result.content.text
    elif hasattr(result.content, "text"):
        text = str(result.content.text)
    parts = text.strip().split()
    pick = parts[0].strip(",'\"").lower() if parts else ""
    return pick if pick in _SYMBOL_SET else None


async def _elicit_icon(ctx: Context, title: str, suggestion: IconSuggestionResult) -> Optional[ResolvedIcon]:
    """Confirm/override the icon with the user. None ⇒ unsupported (fall through)."""
    rec = suggestion.recommended
    alts = ", ".join(c.symbol for c in suggestion.candidates) or rec
    try:
        res = await ctx.elicit(
            message=(
                f"Icon for the list '{title}'? Recommended: {rec}. Accept to use it, "
                f"or edit to pick another (suggestions: {alts}; or any SF Symbol / emoji)."
            ),
            schema=_IconChoice,
        )
    except AttributeError:
        await ctx.debug("Elicitation unsupported; using silent best-effort icon.")
        return None
    if res.action != "accept":
        return ResolvedIcon(source="none")  # user declined → no icon
    chosen = (getattr(res.data, "symbol", "") or rec).strip() or rec
    if _looks_like_emoji(chosen):
        return ResolvedIcon(emoji=chosen, source="asked")
    return ResolvedIcon(symbol=chosen, source="asked")


async def resolve_icon(
    ctx: Context,
    title: str,
    icon: Optional[str],
    *,
    explicit_symbol: Optional[str] = None,
    explicit_emoji: Optional[str] = None,
    allow_sampling: bool = True,
) -> ResolvedIcon:
    """Decide which badge to apply for a new list. See the module docstring."""
    # 1. A low-level explicit symbol/emoji (tools that expose them) always wins.
    if explicit_symbol:
        return ResolvedIcon(symbol=explicit_symbol, source="explicit")
    if explicit_emoji:
        return ResolvedIcon(emoji=explicit_emoji, source="explicit")

    raw = (icon or _AUTO).strip()
    low = raw.lower()
    # 2. An explicit icon string that isn't a sentinel → use it verbatim.
    if low not in _NONE and low not in (_AUTO, _ASK):
        if _looks_like_emoji(raw):
            return ResolvedIcon(emoji=raw, source="explicit")
        return ResolvedIcon(symbol=raw, source="explicit")
    # 3. Opt-out.
    if low in _NONE:
        return ResolvedIcon(source="none")

    # 4. auto / ask → rank the catalog.
    suggestion = suggest_icons(title)
    if low == _ASK:
        chosen = await _elicit_icon(ctx, title, suggestion)
        if chosen is not None:
            return chosen  # accepted/declined; None means "elicitation unsupported"

    # 5. Silent best-effort: a confident table match.
    if suggestion.confident:
        return ResolvedIcon(symbol=suggestion.recommended, source="matched")
    # 6. Table miss → sampling constrained to the catalog.
    if allow_sampling:
        sampled = await _sample_icon(ctx, title)
        if sampled:
            return ResolvedIcon(symbol=sampled, source="sampled")
    # 7. Final fallback → the agent / automated-list glyph.
    return ResolvedIcon(symbol=AGENT_FALLBACK_SYMBOL, source="fallback")


async def apply_list_icon(ctx: Context, list_id: str, resolved: ResolvedIcon) -> bool:
    """Apply a resolved badge to a just-created list via ReminderKit.

    Best-effort: if the ReminderKit helper is unavailable the list still exists,
    so warn and return False rather than failing the create.
    """
    if not resolved.symbol and not resolved.emoji:
        return False
    try:
        _helper_set_list_appearance(list_id, symbol=resolved.symbol, emoji=resolved.emoji)
    except ReminderKitHelperUnavailable as e:
        await ctx.warning(f"List created, but icon not applied — ReminderKit helper not built: {e}")
        return False
    except ReminderKitHelperError as e:
        await ctx.warning(f"List created, but icon not applied: {e.message}")
        return False
    await ctx.debug(f"Applied icon to list {list_id} (source={resolved.source}).")
    return True
