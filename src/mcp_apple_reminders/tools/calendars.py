"""Calendar (reminder-list) MCP tools.

Five read-only operations: list, get-by-name, get-by-id, search, get-default.
Calendar lifecycle (create/delete/update) is intentionally absent in this version;
tracked as a P0 capability gap.
"""

from __future__ import annotations

from typing import Any

from mcp.types import TextContent, Tool


def _format_calendar(cal, include_default: bool = True) -> str:
    """Render a calendar as a human-readable block. Reused across handlers."""
    lines = [
        f"Name: {cal.name}",
        f"ID: {cal.id}",
        f"Color: {cal.color}",
    ]
    if include_default:
        lines.append(f"Default: {'Yes' if cal.is_default else 'No'}")
    lines.append(f"Owner: {cal.owner}")
    return "\n".join(lines)


def _handle_list_calendars(arguments: Any, remind) -> list[TextContent]:
    calendars = list(remind.calendars.list())
    if not calendars:
        return [TextContent(type="text", text="No calendars found.")]

    parts = [f"Found {len(calendars)} calendar(s):", ""]
    for cal in calendars:
        parts.append(_format_calendar(cal))
        parts.append("-" * 40)
    return [TextContent(type="text", text="\n".join(parts))]


def _handle_get_calendar(arguments: Any, remind) -> list[TextContent]:
    cal = remind.calendars.get(arguments["name"])
    return [TextContent(type="text", text="Calendar Found:\n" + _format_calendar(cal))]


def _handle_get_calendar_by_id(arguments: Any, remind) -> list[TextContent]:
    cal = remind.calendars.get_by_id(arguments["calendar_id"])
    return [TextContent(type="text", text="Calendar Found:\n" + _format_calendar(cal))]


def _handle_search_calendars(arguments: Any, remind) -> list[TextContent]:
    query = arguments["query"]
    calendars = list(remind.calendars.search(query))
    if not calendars:
        return [TextContent(type="text", text=f"No calendars found matching '{query}'.")]

    parts = [f"Found {len(calendars)} calendar(s) matching '{query}':", ""]
    for cal in calendars:
        parts.append(_format_calendar(cal))
        parts.append("-" * 40)
    return [TextContent(type="text", text="\n".join(parts))]


def _handle_get_default_calendar(arguments: Any, remind) -> list[TextContent]:
    cal = remind.calendars.get_default()
    return [TextContent(type="text", text="Default Calendar:\n" + _format_calendar(cal, include_default=False))]


TOOLS: list[Tool] = [
    Tool(
        name="list_calendars",
        description="List all available reminder calendars (lists). Returns all reminder lists accessible to the user, including their IDs, names, colors, and whether they are the default list.",
        inputSchema={"type": "object", "properties": {}, "required": []},
    ),
    Tool(
        name="get_calendar",
        description="Get a specific calendar (list) by name. Searches for a reminder list with the exact name provided.",
        inputSchema={
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "The exact name of the calendar to retrieve"},
            },
            "required": ["name"],
        },
    ),
    Tool(
        name="get_calendar_by_id",
        description="Get a specific calendar (list) by its unique ID. More reliable than searching by name.",
        inputSchema={
            "type": "object",
            "properties": {
                "calendar_id": {"type": "string", "description": "The unique identifier of the calendar"},
            },
            "required": ["calendar_id"],
        },
    ),
    Tool(
        name="search_calendars",
        description="Search for calendars (lists) by partial name match. Case-insensitive search that returns all calendars containing the query string.",
        inputSchema={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query string (partial name match)"},
            },
            "required": ["query"],
        },
    ),
    Tool(
        name="get_default_calendar",
        description="Get the default calendar (list) for new reminders. This is the list that Apple Reminders uses by default when creating new items.",
        inputSchema={"type": "object", "properties": {}, "required": []},
    ),
]

HANDLERS = {
    "list_calendars": _handle_list_calendars,
    "get_calendar": _handle_get_calendar,
    "get_calendar_by_id": _handle_get_calendar_by_id,
    "search_calendars": _handle_search_calendars,
    "get_default_calendar": _handle_get_default_calendar,
}
