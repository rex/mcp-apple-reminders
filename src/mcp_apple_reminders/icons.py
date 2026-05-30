"""List-icon resolution + application via Reminders' curated EMBLEM catalog.

Reminders list icons are a small, curated set of EMBLEMS (see `emblems.py`) —
NOT arbitrary SF Symbols (an SF Symbol name like ``star.fill`` is stored but
renders blank). The caller may:

- pass an **emblem id** (e.g. ``weather5``, ``food``) — see `reminders://appearance`;
- pass an **emoji** for an arbitrary glyph;
- pass ``'none'`` to skip the badge;
- omit it / pass ``'auto'`` → the server **auto-suggests** an emblem from the
  list title (the keyword heuristic in `emblems.py`), or leaves it icon-less if
  nothing fits.

`apply_list_icon` writes the badge via the ReminderKit helper, degrading
gracefully (warn, never fail the create) — and warns rather than silently
applying an unrecognised (blank-rendering) emblem.
"""

from __future__ import annotations

import re
from typing import Optional

from mcp.server.fastmcp import Context
from pydantic import BaseModel

from ._native.reminderkit import ReminderKitHelperError, ReminderKitHelperUnavailable
from ._native.reminderkit_lists import set_list_appearance as _helper_set_list_appearance
from .emblems import is_valid_emblem, suggest_emblem

# A bare ascii token (letters/digits/dots) is a candidate emblem id; anything
# else (non-ascii) is treated as an emoji.
_SYMBOL_RE = re.compile(r"^[a-z0-9.]+$")

# `icon` argument values that mean "no badge" (case-insensitive).
_NONE = {"none", "off", ""}


class ResolvedIcon(BaseModel):
    """The badge to apply to a list, and how it was chosen."""

    symbol: Optional[str] = None  # a valid Reminders emblem id
    emoji: Optional[str] = None
    source: str  # explicit | suggested | none | invalid
    requested: Optional[str] = None  # the raw value, when source == "invalid"


def _looks_like_emoji(value: str) -> bool:
    """True when `value` is not a bare ascii token (so: treat it as emoji)."""
    return not bool(_SYMBOL_RE.match(value))


def _suggest(title: Optional[str]) -> ResolvedIcon:
    emblem = suggest_emblem(title)
    return ResolvedIcon(symbol=emblem, source="suggested") if emblem else ResolvedIcon(source="none")


def _resolve_token(token: str) -> ResolvedIcon:
    if is_valid_emblem(token):
        return ResolvedIcon(symbol=token, source="explicit")
    return ResolvedIcon(source="invalid", requested=token)


def resolve_icon(
    icon: Optional[str],
    *,
    title: Optional[str] = None,
    explicit_symbol: Optional[str] = None,
    explicit_emoji: Optional[str] = None,
) -> ResolvedIcon:
    """Resolve the caller's icon choice to a renderable badge.

    Precedence:
    - a low-level explicit `emoji` wins; an explicit `symbol` is validated as an emblem;
    - 'none' / 'off' / '' → no badge;
    - omitted (None) or 'auto' → AUTO-SUGGEST an emblem from `title` (icon-less
      if nothing fits — a wrong icon is worse than none);
    - an emoji → used as-is;
    - any other token → a Reminders emblem id if valid, else flagged `invalid`
      (the caller warns + skips, since it would render blank).
    """
    if explicit_emoji:
        return ResolvedIcon(emoji=explicit_emoji, source="explicit")
    if explicit_symbol:
        return _resolve_token(explicit_symbol)
    if icon is None:
        return _suggest(title)
    raw = icon.strip()
    low = raw.lower()
    if low in _NONE:
        return ResolvedIcon(source="none")
    if low == "auto":
        return _suggest(title)
    if _looks_like_emoji(raw):
        return ResolvedIcon(emoji=raw, source="explicit")
    return _resolve_token(raw)


async def apply_list_icon(ctx: Context, list_id: str, resolved: ResolvedIcon) -> bool:
    """Apply a resolved badge to a just-created list via ReminderKit.

    Best-effort: never fails the create. Warns (and skips) when the caller asked
    for an emblem that isn't in the catalog, or when the helper is unavailable.
    """
    if resolved.source == "invalid":
        await ctx.warning(
            f"List created, but icon {resolved.requested!r} is not a valid Reminders emblem "
            f"(those are a curated set — see reminders://appearance, or pass an emoji). Icon skipped."
        )
        return False
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
