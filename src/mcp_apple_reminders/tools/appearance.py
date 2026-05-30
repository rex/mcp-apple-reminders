"""List/group appearance + pinning MCP tools — CL-2.2.

`set_list_appearance` restyles or renames a regular list OR a group (sidebar
folder) — color, SF-symbol, emoji. `set_list_pinned` / `set_smart_list_pinned`
pin items at the top of the Reminders sidebar. All backed by the Obj-C
ReminderKit helper (private API).
"""

from __future__ import annotations

from typing import Optional

from mcp.server.fastmcp import Context

from .._native.reminderkit import ReminderKitHelperError, ReminderKitHelperUnavailable
from .._native.reminderkit_lists import (
    set_list_appearance as helper_set_list_appearance,
)
from .._native.reminderkit_lists import (
    set_list_pinned as helper_set_list_pinned,
)
from .._native.reminderkit_lists import (
    set_smart_list_pinned as helper_set_smart_list_pinned,
)
from .._native.sqlite import Reader, RemindersDBUnavailable
from ..emblems import is_valid_emblem
from ..lifespan import app_context as _app_context
from ..results import WriteResult
from ..server import mcp
from ._annotations import MUTATE


def _run(fn, *args, **kwargs) -> dict:
    """Run a helper wrapper, translating helper errors into ValueErrors."""
    try:
        return fn(*args, **kwargs)
    except ReminderKitHelperUnavailable as e:
        raise ValueError(f"ReminderKit helper not built. Run `make build-native`. ({e})") from e
    except ReminderKitHelperError as e:
        raise ValueError(e.message) from e


@mcp.tool(
    name="set_list_appearance",
    title="Set List Appearance",
    annotations=MUTATE,
    description=(
        "Rename and/or restyle a list by its UUID. `color` accepts a named "
        "palette token (red/orange/yellow/green/blue/purple/brown/gray/etc.); "
        "`symbol` is a Reminders EMBLEM id (e.g. 'food', 'weather5' — a curated "
        "catalog, NOT an SF Symbol; see reminders://appearance); `emoji` sets an "
        "emoji icon. Pass `name` to rename. NOTE: Reminders GROUPS have no "
        "color/icon — only `name` (rename) applies to a group; color/symbol/emoji "
        "on a group is rejected. At least one change should be supplied. Private "
        "ReminderKit API."
    ),
)
async def set_list_appearance(
    list_id: str,
    ctx: Context,
    name: Optional[str] = None,
    color: Optional[str] = None,
    symbol: Optional[str] = None,
    emoji: Optional[str] = None,
) -> WriteResult:
    """Rename/restyle a list or group. See description for color/symbol/emoji."""
    if not list_id or not list_id.strip():
        raise ValueError("list_id is required and must be non-empty")
    if symbol and not is_valid_emblem(symbol):
        raise ValueError(
            f"symbol {symbol!r} is not a valid Reminders emblem. List icons are a curated "
            f"catalog (e.g. 'food', 'weather5', 'work1') — see reminders://appearance — NOT SF "
            f"Symbols. Pass `emoji` for an arbitrary glyph."
        )
    # Reminders groups have no color/icon — reject a styling no-op (rename is fine).
    if color or symbol or emoji:
        app = _app_context(ctx)
        try:
            with app.open_sqlite() as conn:
                cal = Reader(conn).get_calendar_by_id(list_id)
            if cal is not None and cal.is_group:
                raise ValueError(
                    f"{list_id!r} is a group (sidebar folder); Reminders groups have no color/icon. "
                    f"Only `name` (rename) applies to a group."
                )
        except RemindersDBUnavailable:
            pass  # can't verify the kind — let the helper proceed
    resp = _run(helper_set_list_appearance, list_id, name=name, color=color, symbol=symbol, emoji=emoji)
    await ctx.info(f"Updated appearance of list {list_id}")
    return WriteResult.of(status=resp.get("status", "updated"), list_id=list_id, name=resp.get("name", name))


@mcp.tool(
    name="set_list_pinned",
    title="Pin or Unpin List",
    annotations=MUTATE,
    description=(
        "Pin or unpin a list/group at the top of the Reminders sidebar. Pass "
        "the list (or group) UUID and `pinned` (true to pin, false to unpin). "
        "Private ReminderKit API."
    ),
)
async def set_list_pinned(list_id: str, pinned: bool, ctx: Context) -> WriteResult:
    """Pin (true) or unpin (false) a list/group."""
    if not list_id or not list_id.strip():
        raise ValueError("list_id is required and must be non-empty")
    resp = _run(helper_set_list_pinned, list_id, pinned)
    await ctx.info(f"{'Pinned' if pinned else 'Unpinned'} list {list_id}")
    return WriteResult.of(status=resp.get("status", "updated"), list_id=list_id, pinned=bool(pinned))


@mcp.tool(
    name="set_smart_list_pinned",
    title="Pin or Unpin Smart List",
    annotations=MUTATE,
    description=(
        "Pin or unpin a custom smart list at the top of the Reminders sidebar. "
        "Pass the smart-list UUID and `pinned`. Private ReminderKit API."
    ),
)
async def set_smart_list_pinned(smart_list_id: str, pinned: bool, ctx: Context) -> WriteResult:
    """Pin (true) or unpin (false) a custom smart list."""
    if not smart_list_id or not smart_list_id.strip():
        raise ValueError("smart_list_id is required and must be non-empty")
    resp = _run(helper_set_smart_list_pinned, smart_list_id, pinned)
    await ctx.info(f"{'Pinned' if pinned else 'Unpinned'} smart list {smart_list_id}")
    return WriteResult.of(status=resp.get("status", "updated"), smart_list_id=smart_list_id, pinned=bool(pinned))
