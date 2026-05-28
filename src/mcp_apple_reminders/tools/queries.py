"""Reminder query MCP tools — FastMCP edition.

Five read-only operations:
- `get_reminders` — full filter surface (date range, completion, priority, calendar, limit)
- `search_reminders` — substring search across title and notes
- `get_next_reminder` — soonest upcoming incomplete reminder with a due date
- `get_overdue_reminders` — incomplete reminders whose due date is past
- `get_today_reminders` — reminders due in the current local day
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from mcp.server.fastmcp import Context

from .._native import Priority
from ..formatting import parse_datetime
from ..models import Reminder, native_reminder_to_pydantic
from ..server import mcp


def _bridge_from_ctx(ctx: Context):
    return ctx.request_context.lifespan_context.bridge


def _to_pydantic_list(native_iter) -> list[Reminder]:
    return [native_reminder_to_pydantic(r) for r in native_iter]


def _resolve_priority(priority_str: Optional[str]) -> Optional[Priority]:
    if not priority_str:
        return None
    priority_map = {
        "none": Priority.NONE,
        "low": Priority.LOW,
        "medium": Priority.MEDIUM,
        "high": Priority.HIGH,
    }
    return priority_map.get(priority_str.lower())


@mcp.tool(
    name="get_reminders",
    description=(
        "Get reminders with optional filters. You can filter by: due date range, "
        "completion status, priority level, and specific calendar. Without "
        "filters, returns all reminders from all calendars."
    ),
)
async def get_reminders(
    ctx: Context,
    due_after: Optional[str] = None,
    due_before: Optional[str] = None,
    is_completed: Optional[bool] = None,
    priority: Optional[str] = None,
    calendar_id: Optional[str] = None,
    limit: Optional[int] = None,
) -> list[Reminder]:
    """Get reminders with optional filters.

    Args:
        due_after: Only return reminders due after this date (ISO format). Optional.
        due_before: Only return reminders due before this date (ISO format). Optional.
        is_completed: Filter by completion status: true for completed, false for incomplete, omit for all. Optional.
        priority: Filter by priority: 'none', 'low', 'medium', or 'high'. Optional.
        calendar_id: Only return reminders from this specific calendar. Optional.
        limit: Maximum number of reminders to return. Optional.
    """
    kwargs: dict = {}
    if due_after:
        kwargs["due_after"] = parse_datetime(due_after)
    if due_before:
        kwargs["due_before"] = parse_datetime(due_before)
    if is_completed is not None:
        kwargs["is_completed"] = is_completed
    resolved_priority = _resolve_priority(priority)
    if resolved_priority is not None:
        kwargs["priority"] = resolved_priority
    if calendar_id:
        kwargs["calendar_id"] = calendar_id

    bridge = _bridge_from_ctx(ctx)
    results = list(bridge.get_reminders(**kwargs))
    if limit and limit > 0:
        results = results[:limit]
    return _to_pydantic_list(results)


@mcp.tool(
    name="search_reminders",
    description=(
        "Search for reminders by text query. Searches both the reminder title "
        "and notes fields. Case-insensitive partial matching."
    ),
)
async def search_reminders(query: str, ctx: Context, limit: Optional[int] = None) -> list[Reminder]:
    """Search reminders by case-insensitive substring across title and notes.

    Args:
        query: Search query string to match against titles and notes.
        limit: Maximum number of results to return. Optional.
    """
    bridge = _bridge_from_ctx(ctx)
    results = list(bridge.search_reminders(query))
    if limit and limit > 0:
        results = results[:limit]
    return _to_pydantic_list(results)


@mcp.tool(
    name="get_next_reminder",
    description=(
        "Get the next upcoming incomplete reminder based on due date. Returns "
        "the soonest incomplete reminder that has a due date set. Returns "
        "nothing if no upcoming reminders exist."
    ),
)
async def get_next_reminder(ctx: Context) -> Optional[Reminder]:
    """Return the soonest upcoming incomplete reminder, or None if none."""
    bridge = _bridge_from_ctx(ctx)
    native = bridge.get_next_reminder()
    if not native:
        return None
    return native_reminder_to_pydantic(native)


@mcp.tool(
    name="get_overdue_reminders",
    description=(
        "Get all incomplete reminders that are overdue (due date is in the "
        "past). Useful for finding tasks that need immediate attention."
    ),
)
async def get_overdue_reminders(ctx: Context, limit: Optional[int] = None) -> list[Reminder]:
    """Get all incomplete reminders whose due date is in the past.

    Args:
        limit: Maximum number of results to return. Optional.
    """
    bridge = _bridge_from_ctx(ctx)
    results = list(bridge.get_reminders(due_before=datetime.now(), is_completed=False))
    if limit and limit > 0:
        results = results[:limit]
    return _to_pydantic_list(results)


@mcp.tool(
    name="get_today_reminders",
    description=(
        "Get all reminders due today (both completed and incomplete). Useful " "for daily task management and review."
    ),
)
async def get_today_reminders(ctx: Context, include_completed: bool = False) -> list[Reminder]:
    """Get all reminders due in the current local day.

    Args:
        include_completed: Whether to include completed reminders. Default is false (only incomplete). Optional.
    """
    now = datetime.now()
    start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end_of_day = now.replace(hour=23, minute=59, second=59, microsecond=999999)

    bridge = _bridge_from_ctx(ctx)
    if include_completed:
        results = list(bridge.get_reminders(due_after=start_of_day, due_before=end_of_day))
    else:
        results = list(bridge.get_reminders(due_after=start_of_day, due_before=end_of_day, is_completed=False))
    return _to_pydantic_list(results)
