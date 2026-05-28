"""Reminder CRUD MCP tools — FastMCP edition.

Six operations: create, update, complete (sugar over update), uncomplete
(sugar), get-by-id, delete. The complete/uncomplete handlers are thin
wrappers that call `update_reminder(is_completed=…)` so they stay in sync
with the canonical update path automatically.
"""

from __future__ import annotations

from typing import Optional

from mcp.server.fastmcp import Context

from .._native.sqlite import Reader, RemindersDBUnavailable
from ..formatting import parse_datetime, parse_priority
from ..lifespan import AppContext
from ..models import Reminder, native_reminder_to_pydantic
from ..server import mcp


def _bridge_from_ctx(ctx: Context):
    return ctx.request_context.lifespan_context.bridge


def _app_context(ctx: Context) -> AppContext:
    return ctx.request_context.lifespan_context


@mcp.tool(
    name="create_reminder",
    description=(
        "Create a new reminder in Apple Reminders. You can specify the title, "
        "due date, notes, priority, URL, and which calendar (list) to add it "
        "to. If no calendar is specified, it will be added to the default list."
    ),
)
async def create_reminder(
    title: str,
    ctx: Context,
    due_date: Optional[str] = None,
    notes: Optional[str] = None,
    priority: Optional[str] = None,
    url: Optional[str] = None,
    calendar_id: Optional[str] = None,
) -> Reminder:
    """Create a new reminder.

    Args:
        title: The title/name of the reminder.
        due_date: ISO format datetime string (e.g., '2024-01-15T14:30:00'). Optional.
        notes: Additional notes or description for the reminder. Optional.
        priority: Priority level: 'none', 'low', 'medium', 'high', or integer 0-9. Default is 'none'. Optional.
        url: URL to associate with the reminder. Optional.
        calendar_id: ID of the calendar (list) to add the reminder to. If not specified, uses the default calendar. Optional.
    """
    kwargs: dict = {"title": title}
    if due_date:
        kwargs["due_date"] = parse_datetime(due_date)
    if notes:
        kwargs["notes"] = notes
    if priority:
        kwargs["priority"] = parse_priority(priority)
    if url:
        kwargs["url"] = url
    if calendar_id:
        kwargs["calendar_id"] = calendar_id

    bridge = _bridge_from_ctx(ctx)
    created = native_reminder_to_pydantic(bridge.create_reminder(**kwargs))
    await ctx.info(f"Created reminder {created.id} in list {created.list_id}: {created.title!r}")
    return created


@mcp.tool(
    name="update_reminder",
    description=(
        "Update an existing reminder. You can modify any combination of: "
        "title, due date, notes, priority, URL, and completion status. Only "
        "the fields you specify will be updated; others remain unchanged."
    ),
)
async def update_reminder(
    reminder_id: str,
    ctx: Context,
    title: Optional[str] = None,
    due_date: Optional[str] = None,
    notes: Optional[str] = None,
    priority: Optional[str] = None,
    url: Optional[str] = None,
    is_completed: Optional[bool] = None,
) -> Reminder:
    """Update an existing reminder.

    Args:
        reminder_id: The unique identifier of the reminder to update.
        title: New title for the reminder. Optional.
        due_date: New due date in ISO format (e.g., '2024-01-15T14:30:00'). Optional.
        notes: New notes/description. Optional.
        priority: New priority: 'none', 'low', 'medium', 'high', or integer 0-9. Optional.
        url: New URL to associate with the reminder. Optional.
        is_completed: Mark the reminder as completed (true) or incomplete (false). Optional.
    """
    kwargs: dict = {}
    if title:
        kwargs["title"] = title
    if due_date:
        kwargs["due_date"] = parse_datetime(due_date)
    if notes is not None:
        # Empty string is an explicit clear, not a no-op.
        kwargs["notes"] = notes
    if priority:
        kwargs["priority"] = parse_priority(priority)
    if url is not None:
        kwargs["url"] = url
    if is_completed is not None:
        kwargs["is_completed"] = is_completed

    bridge = _bridge_from_ctx(ctx)
    updated = native_reminder_to_pydantic(bridge.update_reminder(reminder_id, **kwargs))
    await ctx.info(f"Updated reminder {reminder_id}: fields={sorted(kwargs.keys())}")
    return updated


@mcp.tool(
    name="complete_reminder",
    description=(
        "Mark a reminder as completed. This is a convenience tool that's "
        "equivalent to calling update_reminder with is_completed=true."
    ),
)
async def complete_reminder(reminder_id: str, ctx: Context) -> Reminder:
    """Mark a reminder as completed.

    Args:
        reminder_id: The unique identifier of the reminder to mark as complete.
    """
    bridge = _bridge_from_ctx(ctx)
    result = native_reminder_to_pydantic(bridge.update_reminder(reminder_id, is_completed=True))
    await ctx.info(f"Completed reminder {reminder_id}")
    return result


@mcp.tool(
    name="uncomplete_reminder",
    description=(
        "Mark a reminder as incomplete/not done. This is useful for reopening "
        "a reminder that was previously completed."
    ),
)
async def uncomplete_reminder(reminder_id: str, ctx: Context) -> Reminder:
    """Mark a reminder as incomplete.

    Args:
        reminder_id: The unique identifier of the reminder to mark as incomplete.
    """
    bridge = _bridge_from_ctx(ctx)
    result = native_reminder_to_pydantic(bridge.update_reminder(reminder_id, is_completed=False))
    await ctx.info(f"Uncompleted reminder {reminder_id}")
    return result


@mcp.tool(
    name="get_reminder",
    description=(
        "Get a specific reminder by its unique ID. Returns all details about "
        "the reminder including title, due date, notes, priority, completion "
        "status, and more."
    ),
)
async def get_reminder(reminder_id: str, ctx: Context) -> Reminder:
    """Get a reminder by its unique ID. SQLite-first; EventKit fallback.

    Args:
        reminder_id: The unique identifier of the reminder.
    """
    app = _app_context(ctx)
    try:
        with app.open_sqlite() as conn:
            cached = Reader(conn).get_reminder_by_id(reminder_id)
            if cached is not None:
                return cached
            # SQLite open succeeded but no row matched — fall through to
            # EventKit so callers get a uniform error path.
    except RemindersDBUnavailable as e:
        await ctx.warning(f"SQLite read path unavailable ({e}); falling back to EventKit.")
    return native_reminder_to_pydantic(app.bridge.get_reminder_by_id(reminder_id))


@mcp.tool(
    name="delete_reminder",
    description=(
        "Permanently delete a reminder. This action cannot be undone. The "
        "reminder will be removed from Apple Reminders entirely."
    ),
)
async def delete_reminder(reminder_id: str, ctx: Context) -> dict:
    """Permanently delete a reminder.

    Args:
        reminder_id: The unique identifier of the reminder to delete.
    """
    bridge = _bridge_from_ctx(ctx)
    await ctx.warning(f"Deleting reminder {reminder_id} (destructive, no undo)")
    success = bridge.delete_reminder(reminder_id)
    if success:
        await ctx.info(f"Deleted reminder {reminder_id}")
    else:
        await ctx.error(f"Failed to delete reminder {reminder_id}")
    return {
        "reminder_id": reminder_id,
        "deleted": bool(success),
        "message": (
            f"Reminder {reminder_id} deleted successfully." if success else f"Failed to delete reminder {reminder_id}."
        ),
    }
