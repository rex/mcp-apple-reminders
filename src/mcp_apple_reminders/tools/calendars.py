"""Calendar (reminder-list) MCP tools — FastMCP edition.

Five read-only operations: list, get-by-name, get-by-id, search, get-default.
Calendar lifecycle (create/delete/update) is intentionally absent in this
version; tracked as a P0 capability gap (Slices 1.2, 1.3).
"""

from __future__ import annotations

from mcp.server.fastmcp import Context

from ..models import Calendar, native_calendar_to_pydantic
from ..server import mcp


def _bridge_from_ctx(ctx: Context):
    """Pull the RemindKit bridge off the lifespan-owned AppContext."""
    return ctx.request_context.lifespan_context.bridge


@mcp.tool(
    name="list_calendars",
    description=(
        "List all available reminder calendars (lists). Returns all reminder "
        "lists accessible to the user, including their IDs, names, colors, "
        "and whether they are the default list."
    ),
)
async def list_calendars(ctx: Context) -> list[Calendar]:
    """List all reminder calendars accessible to the user."""
    bridge = _bridge_from_ctx(ctx)
    return [native_calendar_to_pydantic(c) for c in bridge.calendars.list()]


@mcp.tool(
    name="get_calendar",
    description=(
        "Get a specific calendar (list) by name. Searches for a reminder " "list with the exact name provided."
    ),
)
async def get_calendar(name: str, ctx: Context) -> Calendar:
    """Look up a calendar by exact name match.

    Args:
        name: The exact name of the calendar to retrieve.
    """
    bridge = _bridge_from_ctx(ctx)
    return native_calendar_to_pydantic(bridge.calendars.get(name))


@mcp.tool(
    name="get_calendar_by_id",
    description=("Get a specific calendar (list) by its unique ID. More reliable than " "searching by name."),
)
async def get_calendar_by_id(calendar_id: str, ctx: Context) -> Calendar:
    """Look up a calendar by its unique identifier.

    Args:
        calendar_id: The unique identifier of the calendar.
    """
    bridge = _bridge_from_ctx(ctx)
    return native_calendar_to_pydantic(bridge.calendars.get_by_id(calendar_id))


@mcp.tool(
    name="search_calendars",
    description=(
        "Search for calendars (lists) by partial name match. Case-insensitive "
        "search that returns all calendars containing the query string."
    ),
)
async def search_calendars(query: str, ctx: Context) -> list[Calendar]:
    """Search calendars by case-insensitive substring match.

    Args:
        query: Search query string (partial name match).
    """
    bridge = _bridge_from_ctx(ctx)
    return [native_calendar_to_pydantic(c) for c in bridge.calendars.search(query)]


@mcp.tool(
    name="get_default_calendar",
    description=(
        "Get the default calendar (list) for new reminders. This is the list "
        "that Apple Reminders uses by default when creating new items."
    ),
)
async def get_default_calendar(ctx: Context) -> Calendar:
    """Return the EventKit-declared default calendar for new reminders."""
    bridge = _bridge_from_ctx(ctx)
    return native_calendar_to_pydantic(bridge.calendars.get_default())
