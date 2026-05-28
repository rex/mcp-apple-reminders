"""Reminder query MCP tools.

Five read-only operations:
- `get_reminders` — full filter surface (date range, completion, priority, calendar, limit)
- `search_reminders` — substring search across title and notes
- `get_next_reminder` — soonest upcoming incomplete reminder with a due date
- `get_overdue_reminders` — incomplete reminders whose due date is past
- `get_today_reminders` — reminders due in the current local day
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from mcp.types import TextContent, Tool

from mcp_apple_reminders._native import Priority

from ..formatting import format_reminder, parse_datetime


def _render_reminder_list(reminders, prefix: str) -> str:
    """Render a list of reminders with a count header and separator-delimited bodies."""
    parts = [f"{prefix} ({len(reminders)} reminder(s)):", ""]
    for i, reminder in enumerate(reminders, 1):
        parts.append(f"=== Reminder {i} ===")
        parts.append(format_reminder(reminder))
        parts.append("\n" + "=" * 40 + "\n")
    return "\n".join(parts)


def _build_filter_kwargs(arguments: Any) -> dict:
    """Translate MCP filter args into pyremindkit.get_reminders kwargs."""
    kwargs = {}
    if arguments.get("due_after"):
        kwargs["due_after"] = parse_datetime(arguments["due_after"])
    if arguments.get("due_before"):
        kwargs["due_before"] = parse_datetime(arguments["due_before"])
    if "is_completed" in arguments:
        kwargs["is_completed"] = arguments["is_completed"]
    if arguments.get("priority"):
        priority_str = arguments["priority"].lower()
        priority_map = {
            "none": Priority.NONE,
            "low": Priority.LOW,
            "medium": Priority.MEDIUM,
            "high": Priority.HIGH,
        }
        if priority_str in priority_map:
            kwargs["priority"] = priority_map[priority_str]
    if arguments.get("calendar_id"):
        kwargs["calendar_id"] = arguments["calendar_id"]
    return kwargs


def _handle_get_reminders(arguments: Any, remind) -> list[TextContent]:
    kwargs = _build_filter_kwargs(arguments)
    reminders = list(remind.get_reminders(**kwargs))

    limit = arguments.get("limit")
    if limit and limit > 0:
        reminders = reminders[:limit]

    if not reminders:
        return [TextContent(type="text", text="No reminders found matching the specified filters.")]
    return [TextContent(type="text", text=_render_reminder_list(reminders, "Found"))]


def _handle_search_reminders(arguments: Any, remind) -> list[TextContent]:
    query = arguments["query"]
    reminders = list(remind.search_reminders(query))

    limit = arguments.get("limit")
    if limit and limit > 0:
        reminders = reminders[:limit]

    if not reminders:
        return [TextContent(type="text", text=f"No reminders found matching '{query}'.")]
    return [TextContent(type="text", text=_render_reminder_list(reminders, f"Found matching '{query}'"))]


def _handle_get_next_reminder(arguments: Any, remind) -> list[TextContent]:
    reminder = remind.get_next_reminder()
    if not reminder:
        return [TextContent(type="text", text="No upcoming reminders found.")]
    return [TextContent(type="text", text="Next Upcoming Reminder:\n\n" + format_reminder(reminder))]


def _handle_get_overdue_reminders(arguments: Any, remind) -> list[TextContent]:
    now = datetime.now()
    reminders = list(remind.get_reminders(due_before=now, is_completed=False))

    limit = arguments.get("limit")
    if limit and limit > 0:
        reminders = reminders[:limit]

    if not reminders:
        return [TextContent(type="text", text="No overdue reminders found. Great job!")]
    return [TextContent(type="text", text=_render_reminder_list(reminders, "Found overdue"))]


def _handle_get_today_reminders(arguments: Any, remind) -> list[TextContent]:
    now = datetime.now()
    start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end_of_day = now.replace(hour=23, minute=59, second=59, microsecond=999999)

    include_completed = arguments.get("include_completed", False)

    if include_completed:
        reminders = list(remind.get_reminders(due_after=start_of_day, due_before=end_of_day))
    else:
        reminders = list(remind.get_reminders(due_after=start_of_day, due_before=end_of_day, is_completed=False))

    if not reminders:
        status = "any" if include_completed else "incomplete"
        return [TextContent(type="text", text=f"No {status} reminders due today.")]
    return [TextContent(type="text", text=_render_reminder_list(reminders, "Found due today"))]


TOOLS: list[Tool] = [
    Tool(
        name="get_reminders",
        description="Get reminders with optional filters. You can filter by: due date range, completion status, priority level, and specific calendar. Without filters, returns all reminders from all calendars.",
        inputSchema={
            "type": "object",
            "properties": {
                "due_after": {
                    "type": "string",
                    "description": "Only return reminders due after this date (ISO format). Optional.",
                },
                "due_before": {
                    "type": "string",
                    "description": "Only return reminders due before this date (ISO format). Optional.",
                },
                "is_completed": {
                    "type": "boolean",
                    "description": "Filter by completion status: true for completed, false for incomplete, omit for all. Optional.",
                },
                "priority": {
                    "type": "string",
                    "description": "Filter by priority: 'none', 'low', 'medium', or 'high'. Optional.",
                },
                "calendar_id": {
                    "type": "string",
                    "description": "Only return reminders from this specific calendar. Optional.",
                },
                "limit": {"type": "integer", "description": "Maximum number of reminders to return. Optional."},
            },
            "required": [],
        },
    ),
    Tool(
        name="search_reminders",
        description="Search for reminders by text query. Searches both the reminder title and notes fields. Case-insensitive partial matching.",
        inputSchema={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query string to match against titles and notes"},
                "limit": {"type": "integer", "description": "Maximum number of results to return. Optional."},
            },
            "required": ["query"],
        },
    ),
    Tool(
        name="get_next_reminder",
        description="Get the next upcoming incomplete reminder based on due date. Returns the soonest incomplete reminder that has a due date set. Returns nothing if no upcoming reminders exist.",
        inputSchema={"type": "object", "properties": {}, "required": []},
    ),
    Tool(
        name="get_overdue_reminders",
        description="Get all incomplete reminders that are overdue (due date is in the past). Useful for finding tasks that need immediate attention.",
        inputSchema={
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "description": "Maximum number of results to return. Optional."},
            },
            "required": [],
        },
    ),
    Tool(
        name="get_today_reminders",
        description="Get all reminders due today (both completed and incomplete). Useful for daily task management and review.",
        inputSchema={
            "type": "object",
            "properties": {
                "include_completed": {
                    "type": "boolean",
                    "description": "Whether to include completed reminders. Default is false (only incomplete). Optional.",
                },
            },
            "required": [],
        },
    ),
]

HANDLERS = {
    "get_reminders": _handle_get_reminders,
    "search_reminders": _handle_search_reminders,
    "get_next_reminder": _handle_get_next_reminder,
    "get_overdue_reminders": _handle_get_overdue_reminders,
    "get_today_reminders": _handle_get_today_reminders,
}
