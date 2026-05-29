"""Reminder query MCP tools — SQLite-first (post-S1.0), EventKit-fallback.

Five read-only operations:
- `get_reminders` — full filter surface (date range, completion, calendar, limit)
- `search_reminders` — substring search across title and notes
- `get_next_reminder` — soonest upcoming incomplete reminder with a due date
- `get_overdue_reminders` — incomplete reminders whose due date is past
- `get_today_reminders` — reminders due in the current local day

The SQLite reader replaces EventKit iteration for all five. EventKit
remains as the fallback path; tools log a `ctx.warning(...)` when they
fall through. Latency dropped from O(seconds) on a 2200-reminder store
to single-digit ms.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from mcp.server.fastmcp import Context

from .._native import Priority
from .._native.sqlite import Reader, RemindersDBUnavailable
from ..formatting import parse_datetime
from ..lifespan import app_context as _app_context
from ..models import Reminder, native_reminder_to_pydantic
from ..server import mcp


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


def _matches_priority(reminder_priority: int, bucket: Priority) -> bool:
    """Client-side priority bucket filter (SQLite stores raw int 0-9)."""
    if bucket is Priority.NONE:
        return reminder_priority == 0
    if bucket is Priority.LOW:
        return 1 <= reminder_priority <= 4
    if bucket is Priority.MEDIUM:
        return reminder_priority == 5
    if bucket is Priority.HIGH:
        return 6 <= reminder_priority <= 9
    return True


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
    calendar_ids: Optional[list[str]] = None,
    tags: Optional[list[str]] = None,
    limit: Optional[int] = None,
) -> list[Reminder]:
    """Get reminders with optional filters (SQLite-first; EventKit fallback).

    Args:
        due_after: Only return reminders due after this date (ISO format). Optional.
        due_before: Only return reminders due before this date (ISO format). Optional.
        is_completed: Filter by completion status. Optional.
        priority: Filter by priority bucket: 'none', 'low', 'medium', or 'high'. Optional.
        calendar_id: Only return reminders from this specific calendar. Optional.
        limit: Maximum number of reminders to return. Optional.
    """
    app = _app_context(ctx)
    due_after_dt = parse_datetime(due_after) if due_after else None
    due_before_dt = parse_datetime(due_before) if due_before else None
    priority_bucket = _resolve_priority(priority)

    try:
        with app.open_sqlite() as conn:
            stream = Reader(conn).iter_reminders(
                calendar_id=calendar_id,
                calendar_ids=calendar_ids,
                completed=is_completed,
                due_after=due_after_dt,
                due_before=due_before_dt,
                tags=tags,
            )
            results: list[Reminder] = []
            for r in stream:
                if priority_bucket is not None and not _matches_priority(r.priority, priority_bucket):
                    continue
                results.append(r)
                if limit and len(results) >= limit:
                    break
            await ctx.debug(f"get_reminders (SQLite): {len(results)} match(es)")
            return results
    except RemindersDBUnavailable as e:
        await ctx.warning(f"SQLite read path unavailable ({e}); falling back to EventKit.")
        kwargs: dict = {}
        if due_after_dt is not None:
            kwargs["due_after"] = due_after_dt
        if due_before_dt is not None:
            kwargs["due_before"] = due_before_dt
        if is_completed is not None:
            kwargs["is_completed"] = is_completed
        if priority_bucket is not None:
            kwargs["priority"] = priority_bucket
        if calendar_id:
            kwargs["calendar_id"] = calendar_id
        results = [native_reminder_to_pydantic(r) for r in app.bridge.get_reminders(**kwargs)]
        if limit and limit > 0:
            results = results[:limit]
        return results


@mcp.tool(
    name="search_reminders",
    description=(
        "Search for reminders by text query. Searches both the reminder title "
        "and notes fields. Case-insensitive partial matching."
    ),
)
async def search_reminders(query: str, ctx: Context, limit: Optional[int] = None) -> list[Reminder]:
    """SQLite-first substring search across title and notes.

    Args:
        query: Search query string to match against titles and notes.
        limit: Maximum number of results to return. Optional.
    """
    app = _app_context(ctx)
    try:
        with app.open_sqlite() as conn:
            results = Reader(conn).search_reminders(query, limit=limit)
            if not results:
                await ctx.warning(f"search_reminders({query!r}): no matches")
            else:
                await ctx.debug(f"search_reminders({query!r}) (SQLite): {len(results)} match(es)")
            return results
    except RemindersDBUnavailable as e:
        await ctx.warning(f"SQLite read path unavailable ({e}); falling back to EventKit.")
        results = [native_reminder_to_pydantic(r) for r in app.bridge.search_reminders(query)]
        if limit and limit > 0:
            results = results[:limit]
        return results


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
    app = _app_context(ctx)
    now = datetime.now()
    try:
        with app.open_sqlite() as conn:
            for r in Reader(conn).iter_reminders(completed=False, due_after=now, limit=1):
                return r
            await ctx.info("get_next_reminder: no upcoming incomplete reminders.")
            return None
    except RemindersDBUnavailable as e:
        await ctx.warning(f"SQLite read path unavailable ({e}); falling back to EventKit.")
        native = app.bridge.get_next_reminder()
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
    app = _app_context(ctx)
    now = datetime.now()
    try:
        with app.open_sqlite() as conn:
            results = list(Reader(conn).iter_reminders(completed=False, due_before=now, limit=limit))
            await ctx.debug(f"get_overdue_reminders (SQLite): {len(results)} overdue")
            return results
    except RemindersDBUnavailable as e:
        await ctx.warning(f"SQLite read path unavailable ({e}); falling back to EventKit.")
        results = [native_reminder_to_pydantic(r) for r in app.bridge.get_reminders(due_before=now, is_completed=False)]
        if limit and limit > 0:
            results = results[:limit]
        return results


@mcp.tool(
    name="get_completed_in_range",
    description=(
        "Return reminders whose completion_date falls in [start, end). "
        "Completion ranges are closed on the start and open on the end so "
        "passing the same datetime for both yields an empty result (instead "
        "of one fenceposting boundary)."
    ),
)
async def get_completed_in_range(
    start: str,
    end: str,
    ctx: Context,
    calendar_id: Optional[str] = None,
    limit: Optional[int] = None,
) -> list[Reminder]:
    """Reminders completed within a half-open `[start, end)` window.

    Args:
        start: ISO datetime, inclusive.
        end: ISO datetime, exclusive.
        calendar_id: Optional list UUID to scope to one calendar.
        limit: Optional cap.
    """
    app = _app_context(ctx)
    start_dt = parse_datetime(start)
    end_dt = parse_datetime(end)
    if end_dt < start_dt:
        raise ValueError("end must be >= start")

    try:
        with app.open_sqlite() as conn:
            results = list(
                Reader(conn).iter_reminders(
                    completed=True,
                    completion_after=start_dt,
                    completion_before=end_dt,
                    calendar_id=calendar_id,
                    limit=limit,
                )
            )
            await ctx.debug(f"get_completed_in_range: {len(results)} completion(s) in window")
            return results
    except RemindersDBUnavailable as e:
        await ctx.warning(f"SQLite read path unavailable ({e}); EventKit fallback not implemented for this tool.")
        return []


@mcp.tool(
    name="get_today_reminders",
    description=(
        "Get all reminders due today (both completed and incomplete). Useful " "for daily task management and review."
    ),
)
async def get_today_reminders(ctx: Context, include_completed: bool = False) -> list[Reminder]:
    """Get all reminders due in the current local day.

    Args:
        include_completed: Whether to include completed reminders. Default false. Optional.
    """
    app = _app_context(ctx)
    now = datetime.now()
    start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end_of_day = now.replace(hour=23, minute=59, second=59, microsecond=999999)
    completed_filter: Optional[bool] = None if include_completed else False

    try:
        with app.open_sqlite() as conn:
            results = list(
                Reader(conn).iter_reminders(
                    completed=completed_filter,
                    due_after=start_of_day,
                    due_before=end_of_day,
                )
            )
            await ctx.debug(
                f"get_today_reminders(include_completed={include_completed}) (SQLite): " f"{len(results)} due today"
            )
            return results
    except RemindersDBUnavailable as e:
        await ctx.warning(f"SQLite read path unavailable ({e}); falling back to EventKit.")
        if include_completed:
            results = [
                native_reminder_to_pydantic(r)
                for r in app.bridge.get_reminders(due_after=start_of_day, due_before=end_of_day)
            ]
        else:
            results = [
                native_reminder_to_pydantic(r)
                for r in app.bridge.get_reminders(due_after=start_of_day, due_before=end_of_day, is_completed=False)
            ]
        return results
