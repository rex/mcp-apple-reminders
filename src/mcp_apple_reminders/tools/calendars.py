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

from typing import Optional

from mcp.server.fastmcp import Context

from .._native.eventkit import (
    EventKitHelperError,
    EventKitHelperUnavailable,
)
from .._native.eventkit import (
    create_calendar as helper_create_calendar,
)
from .._native.eventkit import (
    delete_calendar as helper_delete_calendar,
)
from .._native.eventkit import (
    rename_calendar as helper_rename_calendar,
)
from .._native.sqlite import Reader, RemindersDBUnavailable
from ..icons import apply_list_icon, resolve_icon
from ..lifespan import app_context as _app_context
from ..models import Calendar, native_calendar_to_pydantic
from ..server import mcp
from ._annotations import CREATE, DESTROY, MUTATE, READ


@mcp.tool(
    name="list_calendars",
    title="List Calendars",
    annotations=READ,
    description=(
        "List all available reminder calendars (lists). Returns all reminder "
        "lists accessible to the user, including their IDs, names, colors, "
        "and whether they are the default list."
    ),
)
async def list_calendars(ctx: Context, include_groups: bool = False) -> list[Calendar]:
    """List reminder calendars (lists, and optionally groups).

    Args:
        include_groups: When False (default, post-S5.1), filters out
            group rows. Set True to see groups alongside lists; or use
            the dedicated `list_groups` tool for groups only.
    """
    app = _app_context(ctx)
    try:
        with app.open_sqlite() as conn:
            return Reader(conn).list_calendars(include_groups=include_groups)
    except RemindersDBUnavailable as e:
        await ctx.warning(f"SQLite read path unavailable ({e}); falling back to EventKit.")
        return [native_calendar_to_pydantic(c) for c in app.bridge.calendars.list()]


@mcp.tool(
    name="get_calendar",
    title="Get List by Name",
    annotations=READ,
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
    title="Get List by ID",
    annotations=READ,
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
    title="Search Lists",
    annotations=READ,
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
    name="create_calendar",
    title="Create List",
    annotations=CREATE,
    description=(
        "Create a new reminder calendar (list) in Apple Reminders. The name "
        "must be unique among existing non-deleted lists. Optional `color` "
        "accepts a named palette token (e.g. 'red', 'blue', 'green'). `icon` "
        "sets the list badge: pass any SF Symbol name (e.g. 'cart.fill') or an "
        "emoji, 'none' to skip, or omit it to get the agent-made marker "
        "('sparkles'). The caller chooses the icon — the server does not guess; "
        "see the reminders://appearance resource for valid colors + example "
        "symbols. Returns the new calendar with its deeplink. Backed by the "
        "Swift EventKit helper (_native/bin/rem_eventkit), plus the ReminderKit "
        "helper for the icon."
    ),
)
async def create_calendar(
    name: str,
    ctx: Context,
    color: Optional[str] = None,
    icon: Optional[str] = None,
) -> Calendar:
    """Create a new reminder list via the Swift EventKit helper.

    Args:
        name: The list name (must be unique among existing non-deleted lists).
        color: Optional named-palette token. Optional.
        icon: List badge — an SF Symbol name or emoji to set explicitly, 'none'
            to skip, or omit to get the agent-default glyph ('sparkles'). The
            caller chooses; the server does not guess. Optional.
    """
    if not name or not name.strip():
        raise ValueError("name is required and must be non-empty")

    app = _app_context(ctx)

    # Duplicate-name guard: query the SQLite reader (fast) before invoking
    # the helper. Fall back to a calendar-list scan if SQLite is unavailable.
    try:
        with app.open_sqlite() as conn:
            existing = Reader(conn).get_calendar_by_name(name)
    except RemindersDBUnavailable:
        existing = next(
            (c for c in app.bridge.calendars.list() if c.name == name),
            None,
        )
    if existing is not None:
        raise ValueError(
            f"A calendar named {name!r} already exists. " f"Pick a unique name or update the existing one."
        )

    try:
        created = helper_create_calendar(name, color=color)
    except EventKitHelperUnavailable as e:
        await ctx.error(f"EventKit helper unavailable: {e}")
        raise ValueError(
            f"EventKit helper binary not built. Run `make build-native` from the project root. ({e})"
        ) from e
    except EventKitHelperError as e:
        await ctx.error(f"create_calendar failed: {e.message}")
        raise ValueError(e.message) from e

    await ctx.info(f"Created calendar {created.id} ({name!r})")

    # Best-effort badge. EventKit's create sets color; the SF Symbol / emoji
    # badge is a ReminderKit concept, applied here as a follow-up. The caller
    # picks it (or omits → agent default); a ReminderKit miss warns, never fails.
    resolved = resolve_icon(icon)
    if await apply_list_icon(ctx, created.id, resolved):
        badge = resolved.symbol or resolved.emoji
        await ctx.info(f"Set list icon {badge!r} (source={resolved.source}).")

    return created


@mcp.tool(
    name="delete_calendar",
    title="Delete List",
    annotations=DESTROY,
    description=(
        "Delete a reminder calendar (list). By default, refuses to delete a "
        "list that contains any reminders — set force=true to cascade-delete "
        "the list and every reminder inside it atomically. The default list "
        "(the one new reminders go into) cannot be deleted; rename the default "
        "in Apple Reminders first if you need to remove it. DESTRUCTIVE — "
        "this action cannot be undone."
    ),
)
async def delete_calendar(name: str, ctx: Context, force: bool = False) -> dict:
    """Delete a reminder list.

    Args:
        name: The name of the list to delete.
        force: When false (default), refuse to delete a non-empty list.
            When true, cascade-delete the list and every reminder it
            contains atomically. Optional.
    """
    if not name or not name.strip():
        raise ValueError("name is required and must be non-empty")

    app = _app_context(ctx)

    # 1. Resolve the calendar (and reject the default).
    cal: Optional[Calendar] = None
    reminder_count: Optional[int] = None
    try:
        with app.open_sqlite() as conn:
            reader = Reader(conn)
            cal = reader.get_calendar_by_name(name)
            if cal is not None:
                reminder_count = sum(1 for _ in reader.iter_reminders(calendar_id=cal.id))
    except RemindersDBUnavailable:
        # Fallback path: scan EventKit
        cal_native = next((c for c in app.bridge.calendars.list() if c.name == name), None)
        if cal_native is not None:
            cal = native_calendar_to_pydantic(cal_native)
            reminder_count = sum(1 for _ in app.bridge.get_reminders(calendar_id=cal_native.id))

    if cal is None:
        raise ValueError(f"Calendar named {name!r} not found.")

    default_cal = native_calendar_to_pydantic(app.bridge.calendars.get_default())
    if cal.id == default_cal.id:
        raise ValueError(
            f"Refusing to delete the default calendar {name!r}. "
            f"Change the default in Apple Reminders → Settings → Default List first."
        )

    if reminder_count and reminder_count > 0 and not force:
        raise ValueError(
            f"Calendar {name!r} has {reminder_count} reminder(s). "
            f"Pass force=true to delete the list and all its reminders."
        )

    # force=true is itself the confirmation for the destructive cascade: a
    # non-empty list already requires it (above), so we proceed directly.
    # (Interactive elicitation was removed here - it errored on clients that
    # lack elicitation capability, and was redundant with the force flag.)

    await ctx.warning(f"Deleting calendar {name!r} (force={force}, {reminder_count or 0} reminders)")

    try:
        helper_delete_calendar(name)
    except EventKitHelperUnavailable as e:
        await ctx.error(f"EventKit helper unavailable: {e}")
        raise ValueError(
            f"EventKit helper binary not built. Run `make build-native` from the project root. ({e})"
        ) from e
    except EventKitHelperError as e:
        await ctx.error(f"delete_calendar failed: {e.message}")
        raise ValueError(e.message) from e

    await ctx.info(f"Deleted calendar {name!r} (cascade={force})")
    return {
        "id": cal.id,
        "name": name,
        "deleted_reminders": reminder_count or 0,
        "force": force,
    }


@mcp.tool(
    name="update_calendar",
    title="Rename List",
    annotations=MUTATE,
    description=(
        "Rename an existing reminder calendar (list). Pass the current name "
        "and the new name. The new name must not collide with another existing "
        "list. Color updates are not yet supported via this tool — they will "
        "land alongside the ReminderKit helper integration in Slice 1.7."
    ),
)
async def update_calendar(name: str, new_name: str, ctx: Context) -> Calendar:
    """Rename an existing reminder list.

    Args:
        name: The current name of the list.
        new_name: The new name.
    """
    if not name or not name.strip():
        raise ValueError("name is required and must be non-empty")
    if not new_name or not new_name.strip():
        raise ValueError("new_name is required and must be non-empty")
    if name == new_name:
        raise ValueError("new_name must be different from name")

    app = _app_context(ctx)

    # Existence + collision checks via the SQLite reader (fast).
    try:
        with app.open_sqlite() as conn:
            reader = Reader(conn)
            current = reader.get_calendar_by_name(name)
            collision = reader.get_calendar_by_name(new_name)
    except RemindersDBUnavailable:
        current_native = next((c for c in app.bridge.calendars.list() if c.name == name), None)
        collision_native = next((c for c in app.bridge.calendars.list() if c.name == new_name), None)
        current = native_calendar_to_pydantic(current_native) if current_native else None
        collision = native_calendar_to_pydantic(collision_native) if collision_native else None

    if current is None:
        raise ValueError(f"Calendar named {name!r} not found.")
    if collision is not None:
        raise ValueError(f"A calendar named {new_name!r} already exists. Pick a unique name.")

    try:
        renamed = helper_rename_calendar(name, new_name)
    except EventKitHelperUnavailable as e:
        await ctx.error(f"EventKit helper unavailable: {e}")
        raise ValueError(
            f"EventKit helper binary not built. Run `make build-native` from the project root. ({e})"
        ) from e
    except EventKitHelperError as e:
        await ctx.error(f"update_calendar failed: {e.message}")
        raise ValueError(e.message) from e

    await ctx.info(f"Renamed calendar {name!r} → {new_name!r}")
    return renamed


@mcp.tool(
    name="get_default_calendar",
    title="Get Default List",
    annotations=READ,
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
