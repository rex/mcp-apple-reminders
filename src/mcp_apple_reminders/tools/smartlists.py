"""Smart-list MCP tools — CL-2.1.

Custom smart lists are the saved-filter lists in Reminders.app's sidebar. Backed
by the Obj-C ReminderKit helper (private API). The filter predicate
(`filter_data_b64`) is an opaque base64 blob — most callers create/name a smart
list here and refine its filter in Reminders.app, or pass a captured blob.
"""

from __future__ import annotations

from typing import Optional

from mcp.server.fastmcp import Context

from .._native.reminderkit import ReminderKitHelperError, ReminderKitHelperUnavailable
from .._native.reminderkit_lists import (
    create_smart_list as helper_create_smart_list,
)
from .._native.reminderkit_lists import (
    delete_smart_list as helper_delete_smart_list,
)
from .._native.reminderkit_lists import (
    update_smart_list as helper_update_smart_list,
)
from ..icons import resolve_icon
from ..results import DeleteResult, WriteResult
from ..server import mcp
from ._annotations import CREATE, DESTROY, MUTATE


def _helper_call(fn, ctx_error, *args, **kwargs) -> dict:
    """Run a helper wrapper, translating helper errors into ValueErrors."""
    try:
        return fn(*args, **kwargs)
    except ReminderKitHelperUnavailable as e:
        raise ValueError(f"ReminderKit helper not built. Run `make build-native`. ({e})") from e
    except ReminderKitHelperError as e:
        raise ValueError(e.message) from e


@mcp.tool(
    name="create_smart_list",
    title="Create Smart List",
    annotations=CREATE,
    description=(
        "Create a custom smart list (a saved-filter list) in Reminders.app. "
        "Pass a `name` and optional appearance (`color`, `symbol` = a Reminders "
        "emblem id like 'food'/'weather5' — NOT an SF Symbol; see "
        "reminders://appearance — or `emoji`). `icon` is a convenience badge knob: "
        "'none' (default) leaves it iconless; 'auto' auto-suggests an emblem from "
        "the name; or pass an emblem id / emoji directly. An explicit `symbol` or "
        "`emoji` overrides `icon`. The filter "
        "itself is an opaque base64 blob: omit `filter_data_b64` to create a "
        "named smart list whose filter you refine in Reminders.app, or pass a "
        "previously-captured blob. Requires an iCloud account that supports "
        "custom smart lists. Private ReminderKit API."
    ),
)
async def create_smart_list(
    name: str,
    ctx: Context,
    color: Optional[str] = None,
    symbol: Optional[str] = None,
    emoji: Optional[str] = None,
    icon: Optional[str] = "none",
    filter_data_b64: Optional[str] = None,
) -> WriteResult:
    """Create a custom smart list. See the tool description for `icon` / `filter_data_b64`."""
    if not name or not name.strip():
        raise ValueError("name is required and must be non-empty")
    resolved = resolve_icon(icon, title=name, explicit_symbol=symbol, explicit_emoji=emoji)
    if resolved.source == "invalid":
        await ctx.warning(
            f"Smart-list icon {resolved.requested!r} is not a valid Reminders emblem "
            f"(curated set — see reminders://appearance, or pass an emoji). Icon skipped."
        )
    resp = _helper_call(
        helper_create_smart_list,
        ctx,
        name,
        color=color,
        symbol=resolved.symbol,
        emoji=resolved.emoji,
        filter_data_b64=filter_data_b64,
    )
    sid = str(resp.get("id") or "")
    await ctx.info(f"Created smart list {sid} ({name!r})")
    return WriteResult.of(status=resp.get("status", "created"), id=sid, name=name, url=resp.get("url", ""))


@mcp.tool(
    name="update_smart_list",
    title="Update Smart List",
    annotations=MUTATE,
    description=(
        "Update a custom smart list by its UUID: rename it, change its "
        "appearance (`color`, `symbol`, `emoji`), and/or replace its filter "
        "(`filter_data_b64`, opaque base64). At least one change must be "
        "supplied. Private ReminderKit API."
    ),
)
async def update_smart_list(
    smart_list_id: str,
    ctx: Context,
    name: Optional[str] = None,
    color: Optional[str] = None,
    symbol: Optional[str] = None,
    emoji: Optional[str] = None,
    filter_data_b64: Optional[str] = None,
) -> WriteResult:
    """Update a custom smart list. At least one of name/appearance/filter is required."""
    if not smart_list_id or not smart_list_id.strip():
        raise ValueError("smart_list_id is required and must be non-empty")
    resp = _helper_call(
        helper_update_smart_list,
        ctx,
        smart_list_id,
        name=name,
        color=color,
        symbol=symbol,
        emoji=emoji,
        filter_data_b64=filter_data_b64,
    )
    await ctx.info(f"Updated smart list {smart_list_id}")
    return WriteResult.of(status=resp.get("status", "updated"), id=smart_list_id)


@mcp.tool(
    name="delete_smart_list",
    title="Delete Smart List",
    annotations=DESTROY,
    description=(
        "Permanently delete a custom smart list by its UUID. Does NOT delete the "
        "reminders the smart list surfaced (it is only a saved filter). "
        "DESTRUCTIVE — cannot be undone. Private ReminderKit API."
    ),
)
async def delete_smart_list(smart_list_id: str, ctx: Context) -> DeleteResult:
    """Delete a custom smart list by UUID."""
    if not smart_list_id or not smart_list_id.strip():
        raise ValueError("smart_list_id is required and must be non-empty")
    await ctx.warning(f"Deleting smart list {smart_list_id} (destructive)")
    resp = _helper_call(helper_delete_smart_list, ctx, smart_list_id)
    await ctx.info(f"Deleted smart list {smart_list_id}")
    return DeleteResult.of(deleted=True, id=smart_list_id, status=resp.get("status", "deleted"))
