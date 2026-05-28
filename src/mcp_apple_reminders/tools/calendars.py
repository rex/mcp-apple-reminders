"""Calendar (reminder-list) MCP tools — FastMCP edition.

Five read-only operations: list, get-by-name, get-by-id, search, get-default.

Read path: SQLite-first (post-S1.0), EventKit-fallback. The SQLite reader
opens the Reminders.app CoreData store in read-only mode and serves all
calendar lookups in sub-millisecond time. If the store can't be opened
(missing, permission denied, schema drift), the handler logs a warning
via `ctx.warning(...)` and falls back to the EventKit iteration path.

Calendar lifecycle (create/delete/update) is intentionally absent in this
version; tracked as a P0 capability gap (Slices 1.2, 1.3).
"""

from __future__ import annotations

from mcp.server.fastmcp import Context

from .._native.sqlite import Reader, RemindersDBUnavailable
from ..lifespan import AppContext
from ..models import Calendar, native_calendar_to_pydantic
from ..server import mcp


def _app_context(ctx: Context) -> AppContext:
    """Pull the lifespan-owned AppContext off the request context."""
    return ctx.request_context.lifespan_context


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
    app = _app_context(ctx)
    try:
        with app.open_sqlite() as conn:
            return Reader(conn).list_calendars()
    except RemindersDBUnavailable as e:
        await ctx.warning(f"SQLite read path unavailable ({e}); falling back to EventKit.")
        return [native_calendar_to_pydantic(c) for c in app.bridge.calendars.list()]


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
    app = _app_context(ctx)
    try:
        with app.open_sqlite() as conn:
            cal = Reader(conn).get_calendar_by_name(name)
            if cal is None:
                raise ValueError(f"Calendar with name '{name}' not found.")
            return cal
    except RemindersDBUnavailable as e:
        await ctx.warning(f"SQLite read path unavailable ({e}); falling back to EventKit.")
        return native_calendar_to_pydantic(app.bridge.calendars.get(name))


@mcp.tool(
    name="get_calendar_by_id",
    description=("Get a specific calendar (list) by its unique ID. More reliable than " "searching by name."),
)
async def get_calendar_by_id(calendar_id: str, ctx: Context) -> Calendar:
    """Look up a calendar by its unique identifier.

    Args:
        calendar_id: The unique identifier of the calendar.
    """
    app = _app_context(ctx)
    try:
        with app.open_sqlite() as conn:
            cal = Reader(conn).get_calendar_by_id(calendar_id)
            if cal is None:
                raise ValueError(f"Calendar with ID '{calendar_id}' not found.")
            return cal
    except RemindersDBUnavailable as e:
        await ctx.warning(f"SQLite read path unavailable ({e}); falling back to EventKit.")
        return native_calendar_to_pydantic(app.bridge.calendars.get_by_id(calendar_id))


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
    app = _app_context(ctx)
    try:
        with app.open_sqlite() as conn:
            return Reader(conn).search_calendars(query)
    except RemindersDBUnavailable as e:
        await ctx.warning(f"SQLite read path unavailable ({e}); falling back to EventKit.")
        return [native_calendar_to_pydantic(c) for c in app.bridge.calendars.search(query)]


@mcp.tool(
    name="get_default_calendar",
    description=(
        "Get the default calendar (list) for new reminders. This is the list "
        "that Apple Reminders uses by default when creating new items."
    ),
)
async def get_default_calendar(ctx: Context) -> Calendar:
    """Return the EventKit-declared default calendar for new reminders.

    Routed through `RemindKit` rather than the SQLite reader because EventKit
    is the source of truth for "which list is default" — SQLite stores the
    relationship indirectly, and we want exact agreement with what users see
    in Reminders.app's UI.
    """
    app = _app_context(ctx)
    return native_calendar_to_pydantic(app.bridge.calendars.get_default())
