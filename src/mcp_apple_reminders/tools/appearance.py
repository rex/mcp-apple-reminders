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
from ..server import mcp


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
    description=(
        "Rename and/or restyle a list OR group (sidebar folder) by its UUID. "
        "`color` accepts a named palette token (red/orange/yellow/green/blue/"
        "purple/brown/gray/etc.); `symbol` is an SF Symbol name (e.g. "
        "'star.fill', 'cart'); `emoji` sets an emoji icon. Pass `name` to "
        "rename. At least one change should be supplied. Works on both regular "
        "lists and groups. Private ReminderKit API."
    ),
)
async def set_list_appearance(
    list_id: str,
    ctx: Context,
    name: Optional[str] = None,
    color: Optional[str] = None,
    symbol: Optional[str] = None,
    emoji: Optional[str] = None,
) -> dict:
    """Rename/restyle a list or group. See description for color/symbol/emoji."""
    if not list_id or not list_id.strip():
        raise ValueError("list_id is required and must be non-empty")
    resp = _run(helper_set_list_appearance, list_id, name=name, color=color, symbol=symbol, emoji=emoji)
    await ctx.info(f"Updated appearance of list {list_id}")
    return {"list_id": list_id, "name": resp.get("name", name), "status": resp.get("status", "updated")}


@mcp.tool(
    name="set_list_pinned",
    description=(
        "Pin or unpin a list/group at the top of the Reminders sidebar. Pass "
        "the list (or group) UUID and `pinned` (true to pin, false to unpin). "
        "Private ReminderKit API."
    ),
)
async def set_list_pinned(list_id: str, pinned: bool, ctx: Context) -> dict:
    """Pin (true) or unpin (false) a list/group."""
    if not list_id or not list_id.strip():
        raise ValueError("list_id is required and must be non-empty")
    resp = _run(helper_set_list_pinned, list_id, pinned)
    await ctx.info(f"{'Pinned' if pinned else 'Unpinned'} list {list_id}")
    return {"list_id": list_id, "pinned": bool(pinned), "status": resp.get("status", "updated")}


@mcp.tool(
    name="set_smart_list_pinned",
    description=(
        "Pin or unpin a custom smart list at the top of the Reminders sidebar. "
        "Pass the smart-list UUID and `pinned`. Private ReminderKit API."
    ),
)
async def set_smart_list_pinned(smart_list_id: str, pinned: bool, ctx: Context) -> dict:
    """Pin (true) or unpin (false) a custom smart list."""
    if not smart_list_id or not smart_list_id.strip():
        raise ValueError("smart_list_id is required and must be non-empty")
    resp = _run(helper_set_smart_list_pinned, smart_list_id, pinned)
    await ctx.info(f"{'Pinned' if pinned else 'Unpinned'} smart list {smart_list_id}")
    return {"smart_list_id": smart_list_id, "pinned": bool(pinned), "status": resp.get("status", "updated")}
