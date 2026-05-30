"""List-icon resolution + application — the caller supplies the icon.

The client invoking a create tool decides the icon: pass an explicit SF Symbol
name or emoji to the `icon` argument (or the low-level `symbol`/`emoji` on smart
lists). There is intentionally NO server-side keyword/ML guesser — the agent
calling the tool already knows SF Symbols and can choose directly, and the
`reminders://appearance` resource lists the valid colors + example symbols to
browse.

When a list is created with no icon it gets ``AGENT_DEFAULT_SYMBOL`` — the glyph
marking an agent-created / automated list. Pass ``icon='none'`` to skip even
that. `apply_list_icon` writes the badge via the ReminderKit helper, degrading
gracefully (warn, never fail the create) when the helper is absent.
"""

from __future__ import annotations

import re
from typing import Optional

from mcp.server.fastmcp import Context
from pydantic import BaseModel

from ._native.reminderkit import ReminderKitHelperError, ReminderKitHelperUnavailable
from ._native.reminderkit_lists import set_list_appearance as _helper_set_list_appearance

# Badge for an agent-created list when the caller supplies no icon. `sparkles` is
# Apple's "generated automatically" glyph, so it reads as "an assistant made
# this". Tunable here in one place.
AGENT_DEFAULT_SYMBOL = "sparkles"

# SF Symbol names are lowercase letters, digits and dots; anything else
# (non-ascii) is treated as an emoji.
_SYMBOL_RE = re.compile(r"^[a-z0-9.]+$")

# `icon` argument values that mean "no badge" (case-insensitive).
_NONE = {"none", "off", ""}


class ResolvedIcon(BaseModel):
    """The badge to apply to a list, and how it was chosen."""

    symbol: Optional[str] = None
    emoji: Optional[str] = None
    source: str  # explicit | default | none


def _looks_like_emoji(value: str) -> bool:
    """True when `value` is not a bare SF Symbol name (so: treat it as emoji)."""
    return not bool(_SYMBOL_RE.match(value))


def resolve_icon(
    icon: Optional[str],
    *,
    explicit_symbol: Optional[str] = None,
    explicit_emoji: Optional[str] = None,
) -> ResolvedIcon:
    """Map the caller's `icon` argument to a badge — no guessing.

    Precedence:
    - a low-level explicit `symbol`/`emoji` (smart-list args) wins;
    - 'none' / 'off' / '' → no badge;
    - 'auto' or an omitted value (None) → the agent-default glyph;
    - any other string → that SF Symbol name (ascii) or emoji, verbatim.
    """
    if explicit_symbol:
        return ResolvedIcon(symbol=explicit_symbol, source="explicit")
    if explicit_emoji:
        return ResolvedIcon(emoji=explicit_emoji, source="explicit")
    if icon is None:
        return ResolvedIcon(symbol=AGENT_DEFAULT_SYMBOL, source="default")
    raw = icon.strip()
    low = raw.lower()
    if low in _NONE:
        return ResolvedIcon(source="none")
    if low == "auto":
        return ResolvedIcon(symbol=AGENT_DEFAULT_SYMBOL, source="default")
    if _looks_like_emoji(raw):
        return ResolvedIcon(emoji=raw, source="explicit")
    return ResolvedIcon(symbol=raw, source="explicit")


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
