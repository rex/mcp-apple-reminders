"""Agent visibility-plane tools — Slice 4.1.

The whole point of this project. Each project gets an `Agents-<project>`
reminder list; agents bootstrap it on session start, then mirror their
in-flight todos into it so the human can glance at Reminders.app and
see what the agent is up to without joining the agent's session.

Slice 4.1 ships:

- `bootstrap_agent_list(project_name)` — creates `Agents-<project>` if
  missing; idempotent.
- `agents://current/{project_name}` resource — surfaces the list state.

Slice 4.2 (TodoWrite mirror) follows.
"""

from __future__ import annotations

from mcp.server.fastmcp import Context

from .._native.eventkit import (
    EventKitHelperError,
    EventKitHelperUnavailable,
)
from .._native.eventkit import (
    create_calendar as helper_create_calendar,
)
from .._native.sqlite import Reader, RemindersDBUnavailable
from ..lifespan import app_context as _app_context
from ..models import Calendar, native_calendar_to_pydantic
from ..server import mcp
from ._annotations import MUTATE

AGENT_LIST_PREFIX = "Agents-"
DEFAULT_AGENT_LIST_COLOR = "gray"


@mcp.tool(
    name="bootstrap_agent_list",
    title="Bootstrap Agent List",
    annotations=MUTATE,
    description=(
        "Idempotently ensure the `Agents-<project_name>` reminder list "
        "exists. Creates it via the Swift EventKit helper if missing. "
        "Returns the resolved Calendar (existing or newly-created). "
        "This is the entry point an agent should call at session start "
        "before mirroring its in-memory todos."
    ),
)
async def bootstrap_agent_list(project_name: str, ctx: Context) -> Calendar:
    """Ensure the project's Agents-* list exists; create if missing.

    Args:
        project_name: Project identifier. The resulting list is named
            `Agents-<project_name>` exactly. Names are case-sensitive.
    """
    if not project_name or not project_name.strip():
        raise ValueError("project_name is required and must be non-empty")
    list_name = f"{AGENT_LIST_PREFIX}{project_name}"

    app = _app_context(ctx)

    # Look for an existing list first via SQLite (fast, sub-ms).
    try:
        with app.open_sqlite() as conn:
            existing = Reader(conn).get_calendar_by_name(list_name)
    except RemindersDBUnavailable:
        existing = next(
            (c for c in app.bridge.calendars.list() if c.name == list_name),
            None,
        )
        if existing is not None:
            existing = native_calendar_to_pydantic(existing)

    if existing is not None:
        await ctx.info(f"bootstrap_agent_list: {list_name!r} already exists (id={existing.id}).")
        return existing

    # Not present — create it.
    try:
        created = helper_create_calendar(list_name, color=DEFAULT_AGENT_LIST_COLOR)
    except EventKitHelperUnavailable as e:
        await ctx.error(f"EventKit helper unavailable; can't create {list_name!r}: {e}")
        raise ValueError(f"EventKit helper not built. Run `make build-native`. ({e})") from e
    except EventKitHelperError as e:
        await ctx.error(f"bootstrap_agent_list failed: {e.message}")
        raise ValueError(e.message) from e

    await ctx.info(f"bootstrap_agent_list: created {list_name!r} (id={created.id}).")
    return created
