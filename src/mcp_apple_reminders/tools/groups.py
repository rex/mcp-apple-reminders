"""Group (list-folder) MCP tools — Slice 5.1 (ADR 0001).

Groups are the collapsible folders in Reminders.app's sidebar. They live in
the same `ZREMCDBASELIST` table as regular lists but with `ZISGROUP=1`;
child lists carry `ZPARENTLIST = group's Z_PK`.

Three tools:

- `create_group(name)` — make a new empty group.
- `list_groups()` — enumerate all groups (read via SQLite).
- `move_list_to_group(list_id, group_id?)` — reparent a list under a
  group, or detach by omitting `group_id`.
"""

from __future__ import annotations

from typing import Optional

from mcp.server.fastmcp import Context

from .._native.reminderkit import (
    ReminderKitHelperError,
    ReminderKitHelperUnavailable,
)
from .._native.reminderkit_actions import (
    create_group as helper_create_group,
)
from .._native.reminderkit_actions import (
    delete_group as helper_delete_group,
)
from .._native.reminderkit_actions import (
    move_list_to_group as helper_move_list_to_group,
)
from .._native.sqlite import Reader, RemindersDBUnavailable
from ..lifespan import app_context as _app_context
from ..models import Calendar, calendar_deeplink
from ..server import mcp
from ._annotations import CREATE, DESTROY, MUTATE, READ


@mcp.tool(
    name="create_group",
    title="Create Group",
    annotations=CREATE,
    description=(
        "Create a new Reminders.app group (sidebar folder). Groups are "
        "containers — they hold lists, not reminders. Use `move_list_to_group` "
        "afterwards to move existing lists into the new group. Backed by "
        "the Obj-C ReminderKit helper's `create_group` action (private API)."
    ),
)
async def create_group(name: str, ctx: Context) -> Calendar:
    """Create a new group.

    Args:
        name: The group's display name. Must be non-empty and not collide
            with an existing list or group of the same name.
    """
    if not name or not name.strip():
        raise ValueError("name is required and must be non-empty")

    app = _app_context(ctx)

    # Collision guard via SQLite — groups and lists share the same table.
    try:
        with app.open_sqlite() as conn:
            existing = Reader(conn).get_calendar_by_name(name)
    except RemindersDBUnavailable:
        existing = None  # let the helper enforce uniqueness if SQLite is unavailable
    if existing is not None:
        raise ValueError(f"A list or group named {name!r} already exists. Pick a unique name.")

    try:
        response = helper_create_group(name)
    except ReminderKitHelperUnavailable as e:
        await ctx.error(f"ReminderKit helper unavailable: {e}")
        raise ValueError(f"ReminderKit helper not built. Run `make build-native`. ({e})") from e
    except ReminderKitHelperError as e:
        await ctx.error(f"create_group failed: {e.message}")
        raise ValueError(e.message) from e

    group_id = str(response.get("id") or "")
    if not group_id:
        raise ValueError(f"Helper succeeded but returned no group id: {response!r}")

    await ctx.info(f"Created group {group_id} ({name!r})")
    return Calendar(
        id=group_id,
        name=name,
        color="",
        is_default=False,
        owner=None,
        deeplink=calendar_deeplink(group_id),
        is_group=True,
        parent_group_id=None,
    )


@mcp.tool(
    name="list_groups",
    title="List Groups",
    annotations=READ,
    description=(
        "List all Reminders.app groups (sidebar folders). Each returned "
        "Calendar has `is_group=True`. Use `iter_lists_in_group(group_id)` "
        "on the SQLite Reader to get a group's child lists — or just call "
        "`search_calendars` filtered by `parent_group_id`."
    ),
)
async def list_groups(ctx: Context) -> list[Calendar]:
    """Enumerate every group in the user's Reminders store."""
    app = _app_context(ctx)
    try:
        with app.open_sqlite() as conn:
            return Reader(conn).list_groups()
    except RemindersDBUnavailable as e:
        await ctx.error(f"SQLite read path unavailable ({e}); cannot list groups.")
        raise ValueError(f"SQLite read path unavailable ({e}); groups require the SQLite reader.") from e


@mcp.tool(
    name="delete_group",
    title="Delete Group",
    annotations=DESTROY,
    description=(
        "Permanently delete a Reminders.app group. The group must be empty — "
        "if it has children, detach or reparent them first with "
        "`move_list_to_group`. DESTRUCTIVE — this action cannot be undone."
    ),
)
async def delete_group(group_id: str, ctx: Context) -> dict:
    """Delete a group by UUID.

    Args:
        group_id: UUID of the group to delete.
    """
    if not group_id or not group_id.strip():
        raise ValueError("group_id is required and must be non-empty")

    app = _app_context(ctx)
    name: Optional[str] = None
    child_count: Optional[int] = None
    try:
        with app.open_sqlite() as conn:
            reader = Reader(conn)
            cal = reader.get_calendar_by_id(group_id)
            if cal is None or not cal.is_group:
                raise ValueError(f"No group with id {group_id!r} found " f"(must be a group, not a regular list).")
            name = cal.name
            child_count = sum(1 for _ in reader.iter_lists_in_group(group_id))
    except RemindersDBUnavailable as e:
        await ctx.warning(f"SQLite unavailable; skipping pre-check ({e}).")

    if child_count and child_count > 0:
        raise ValueError(
            f"Group {name!r} has {child_count} child list(s). "
            f"Detach or reparent them first with `move_list_to_group`."
        )

    await ctx.warning(f"Deleting group {name!r} ({group_id}, destructive)")
    try:
        helper_delete_group(group_id)
    except ReminderKitHelperUnavailable as e:
        await ctx.error(f"ReminderKit helper unavailable: {e}")
        raise ValueError(f"ReminderKit helper not built. Run `make build-native`. ({e})") from e
    except ReminderKitHelperError as e:
        await ctx.error(f"delete_group failed: {e.message}")
        raise ValueError(e.message) from e

    await ctx.info(f"Deleted group {name!r} ({group_id})")
    return {"id": group_id, "name": name, "status": "deleted_group"}


@mcp.tool(
    name="move_list_to_group",
    title="Move List to Group",
    annotations=MUTATE,
    description=(
        "Move an existing list under a group, or detach it back to the "
        "account root. Pass `group_id` to attach; omit it (or pass empty) "
        "to detach. The list and the group must both exist. Backed by the "
        "Obj-C helper's `move_list_to_group` action via the private "
        "`REMListChangeItem.setParentListID:` selector."
    ),
)
async def move_list_to_group(
    list_id: str,
    ctx: Context,
    group_id: Optional[str] = None,
) -> dict:
    """Reparent a list under a group, or detach it.

    Args:
        list_id: UUID of the child list to reparent.
        group_id: UUID of the target group, or None / omitted to detach
            the list (move it back to the account root).
    """
    if not list_id or not list_id.strip():
        raise ValueError("list_id is required and must be non-empty")

    try:
        response = helper_move_list_to_group(list_id, group_id)
    except ReminderKitHelperUnavailable as e:
        await ctx.error(f"ReminderKit helper unavailable: {e}")
        raise ValueError(f"ReminderKit helper not built. Run `make build-native`. ({e})") from e
    except ReminderKitHelperError as e:
        await ctx.error(f"move_list_to_group failed: {e.message}")
        raise ValueError(e.message) from e

    action = response.get("status", "moved")
    if group_id:
        await ctx.info(f"Moved list {list_id} into group {group_id} ({action})")
    else:
        await ctx.info(f"Detached list {list_id} from its group ({action})")
    return {
        "list_id": list_id,
        "group_id": group_id,
        "status": action,
    }
