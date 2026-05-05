"""FastMCP server for Apple Reminders.

Exposes Reminders as MCP tools, resources, and prompts to LLM clients.
Tool input schemas are generated from Pydantic models on the function
signatures; output payloads are returned as Pydantic instances which the
SDK serializes to JSON for structured agent consumption.

Resources and prompts are registered in :mod:`mcp_apple_reminders.resources`
and :mod:`mcp_apple_reminders.prompts`; this module wires everything
together and owns the singleton ``RemindKit`` connection.
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys
from datetime import datetime
from typing import Annotated, Any

from mcp.server.fastmcp import FastMCP
from pydantic import Field

from . import __version__
from ._helpers import parse_datetime, parse_priority, today_window
from ._models import (
    Calendar,
    CalendarList,
    OperationResult,
    Reminder,
    ReminderList,
    calendar_from_obj,
    reminder_from_obj,
)
from ._workflow import (
    WorkflowListMissingError,
    WorkflowRole,
    all_workflow_names,
    resolve_workflow_calendar,
    workflow_list_name,
)

logger = logging.getLogger("mcp_apple_reminders")


# --- Server-level instructions read by clients on initialize -----------------

INSTRUCTIONS = """\
This server is a conversational layer over Apple Reminders, designed for
ADHD-friendly task management. Prefer the prompts (`plan_my_day`,
`triage_inbox`, `weekly_review`, `quick_capture`) for compound workflows;
fall back to individual tools for surgical edits.

Workflow lists follow a simple kanban convention:
  Claude-On-Deck   — queued, ready to start
  Claude-Active    — currently in progress (≤3 items at a time is healthy)
  Claude-Done      — completed
  Claude-Blocked   — waiting on someone or something

Use `move_reminder_*` tools to transition items between states. The list
prefix can be customized via the MCP_APPLE_REMINDERS_LIST_PREFIX env var.

Datetimes are parsed leniently: ISO 8601 with or without a `Z` suffix,
naive or zoned, all work. Priorities accept the words none/low/medium/high
or integers 0-9 (Apple's UI shows four levels; the int range is preserved
on round-trip).
"""


# --- pyremindkit connection (lazy, so import-time failures are recoverable) --


def _connect_remindkit() -> Any:
    """Open a connection to the local Reminders database via pyremindkit.

    Imported lazily so the module is importable on Linux/CI for unit tests.
    Raises ``RuntimeError`` with an actionable message if the connection
    fails — the caller (FastMCP) surfaces this to the client over MCP.
    """
    try:
        from pyremindkit import RemindKit
    except ImportError as exc:  # pragma: no cover - import guard
        raise RuntimeError(
            "pyremindkit is not installed. Install via `pip install mcp-apple-reminders` "
            "on macOS, or see the README for development setup."
        ) from exc
    try:
        return RemindKit()
    except PermissionError as exc:
        raise RuntimeError(
            "Apple Reminders permission denied. Grant access in "
            "System Settings → Privacy & Security → Reminders, then restart "
            "your MCP client. See: https://support.apple.com/guide/mac-help/mh40596"
        ) from exc


_remind: Any | None = None


def _remindkit() -> Any:
    """Memoized accessor for the RemindKit singleton."""
    global _remind
    if _remind is None:
        _remind = _connect_remindkit()
    return _remind


def _set_remindkit_for_testing(stub: Any) -> None:
    """Inject a fake RemindKit for unit tests. Not part of the public API."""
    global _remind
    _remind = stub


# --- Server instance ---------------------------------------------------------

mcp = FastMCP(
    name="apple-reminders",
    instructions=INSTRUCTIONS,
)


# --- Calendar (list) tools ---------------------------------------------------


@mcp.tool()
def list_calendars() -> CalendarList:
    """List every reminder list (Apple calls these calendars)."""
    cals = [calendar_from_obj(c) for c in _remindkit().calendars.list()]
    return CalendarList(calendars=cals, count=len(cals))


@mcp.tool()
def get_calendar(name: Annotated[str, Field(description="Exact (case-sensitive) list name.")]) -> Calendar:
    """Get a list by exact name."""
    return calendar_from_obj(_remindkit().calendars.get(name))


@mcp.tool()
def get_calendar_by_id(calendar_id: str) -> Calendar:
    """Get a list by its unique ID. More reliable than lookup by name."""
    return calendar_from_obj(_remindkit().calendars.get_by_id(calendar_id))


@mcp.tool()
def search_calendars(
    query: Annotated[str, Field(description="Substring to match against list names (case-insensitive).")],
) -> CalendarList:
    """Search lists by partial name."""
    cals = [calendar_from_obj(c) for c in _remindkit().calendars.search(query)]
    return CalendarList(calendars=cals, count=len(cals))


@mcp.tool()
def get_default_calendar() -> Calendar:
    """Get the default list new reminders are created in."""
    return calendar_from_obj(_remindkit().calendars.get_default())


# --- Reminder CRUD -----------------------------------------------------------


@mcp.tool()
def create_reminder(
    title: Annotated[str, Field(min_length=1, description="Reminder title.")],
    due_date: Annotated[str | None, Field(description="ISO 8601 datetime; trailing Z is OK.")] = None,
    notes: str | None = None,
    priority: Annotated[
        str | int | None,
        Field(description="'none'/'low'/'medium'/'high' or integer 0-9."),
    ] = None,
    url: str | None = None,
    flagged: bool = False,
    calendar_id: Annotated[
        str | None,
        Field(description="Target list ID. Defaults to the user's default list."),
    ] = None,
) -> Reminder:
    """Create a new reminder."""
    kwargs: dict[str, Any] = {"title": title}
    if due_date is not None:
        kwargs["due_date"] = parse_datetime(due_date)
    if notes is not None:
        kwargs["notes"] = notes
    if priority is not None:
        kwargs["priority"] = parse_priority(priority)
    if url is not None:
        kwargs["url"] = url
    if flagged:
        kwargs["flagged"] = True
    if calendar_id is not None:
        kwargs["calendar_id"] = calendar_id
    return reminder_from_obj(_remindkit().create_reminder(**kwargs))


@mcp.tool()
def update_reminder(
    reminder_id: str,
    title: str | None = None,
    due_date: str | None = None,
    notes: str | None = None,
    priority: str | int | None = None,
    url: str | None = None,
    flagged: bool | None = None,
    is_completed: bool | None = None,
) -> Reminder:
    """Update an existing reminder.

    Only fields you explicitly pass are touched. Pass an empty string to
    clear ``notes`` or ``url``; pass 0 to clear ``priority``. Use ``None``
    (the default) to leave a field unchanged.
    """
    kwargs: dict[str, Any] = {}
    if title is not None:
        kwargs["title"] = title
    if due_date is not None:
        kwargs["due_date"] = parse_datetime(due_date) if due_date else None
    if notes is not None:
        kwargs["notes"] = notes
    if priority is not None:
        kwargs["priority"] = parse_priority(priority)
    if url is not None:
        kwargs["url"] = url
    if flagged is not None:
        kwargs["flagged"] = flagged
    if is_completed is not None:
        kwargs["is_completed"] = is_completed
    return reminder_from_obj(_remindkit().update_reminder(reminder_id, **kwargs))


@mcp.tool()
def complete_reminder(reminder_id: str) -> Reminder:
    """Mark a reminder as done."""
    return reminder_from_obj(_remindkit().update_reminder(reminder_id, is_completed=True))


@mcp.tool()
def uncomplete_reminder(reminder_id: str) -> Reminder:
    """Re-open a completed reminder."""
    return reminder_from_obj(_remindkit().update_reminder(reminder_id, is_completed=False))


@mcp.tool()
def get_reminder(reminder_id: str) -> Reminder:
    """Fetch a reminder by ID."""
    return reminder_from_obj(_remindkit().get_reminder_by_id(reminder_id))


@mcp.tool()
def delete_reminder(reminder_id: str) -> OperationResult:
    """Permanently delete a reminder. This cannot be undone."""
    success = bool(_remindkit().delete_reminder(reminder_id))
    return OperationResult(
        success=success,
        message=f"Reminder {reminder_id} {'deleted' if success else 'not deleted (not found?)'}",
        data={"reminder_id": reminder_id},
    )


@mcp.tool()
def set_flagged(reminder_id: str, flagged: bool = True) -> Reminder:
    """Set or clear the ⚑ flag on a reminder."""
    return reminder_from_obj(_remindkit().update_reminder(reminder_id, flagged=flagged))


# --- Reminder queries --------------------------------------------------------


@mcp.tool()
def get_reminders(
    due_after: str | None = None,
    due_before: str | None = None,
    is_completed: bool | None = None,
    priority: str | int | None = None,
    calendar_id: str | None = None,
    limit: Annotated[int | None, Field(ge=1, le=1000, description="Max items to return.")] = None,
) -> ReminderList:
    """Filter reminders by date / completion / priority / list."""
    kwargs: dict[str, Any] = {}
    if due_after is not None:
        kwargs["due_after"] = parse_datetime(due_after)
    if due_before is not None:
        kwargs["due_before"] = parse_datetime(due_before)
    if is_completed is not None:
        kwargs["is_completed"] = is_completed
    if priority is not None:
        kwargs["priority"] = parse_priority(priority)
    if calendar_id is not None:
        kwargs["calendar_id"] = calendar_id
    if limit is not None:
        kwargs["limit"] = limit  # passed through; pyremindkit may or may not honor it

    items = list(_remindkit().get_reminders(**kwargs))
    if limit is not None:
        items = items[:limit]
    rems = [reminder_from_obj(r) for r in items]
    return ReminderList(reminders=rems, count=len(rems))


@mcp.tool()
def search_reminders(
    query: Annotated[str, Field(min_length=1, description="Text to match in titles and notes.")],
    limit: Annotated[int | None, Field(ge=1, le=1000)] = None,
) -> ReminderList:
    """Free-text search across reminder titles and notes."""
    items = list(_remindkit().search_reminders(query))
    if limit:
        items = items[:limit]
    rems = [reminder_from_obj(r) for r in items]
    return ReminderList(reminders=rems, count=len(rems))


@mcp.tool()
def get_next_reminder() -> Reminder | OperationResult:
    """Soonest incomplete reminder with a due date, or a 'none' result."""
    item = _remindkit().get_next_reminder()
    if item is None:
        return OperationResult(success=True, message="No upcoming reminders.")
    return reminder_from_obj(item)


@mcp.tool()
def get_overdue_reminders(
    limit: Annotated[int | None, Field(ge=1, le=1000)] = None,
) -> ReminderList:
    """Incomplete reminders with a due date in the past."""
    kwargs: dict[str, Any] = {"due_before": datetime.now(), "is_completed": False}
    if limit is not None:
        kwargs["limit"] = limit
    items = list(_remindkit().get_reminders(**kwargs))
    if limit is not None:
        items = items[:limit]
    rems = [reminder_from_obj(r) for r in items]
    return ReminderList(reminders=rems, count=len(rems))


@mcp.tool()
def get_today_reminders(include_completed: bool = False) -> ReminderList:
    """Reminders due today (00:00 to next-day 00:00, exclusive)."""
    start, end = today_window()
    kwargs: dict[str, Any] = {"due_after": start, "due_before": end}
    if not include_completed:
        kwargs["is_completed"] = False
    items = [reminder_from_obj(r) for r in _remindkit().get_reminders(**kwargs)]
    return ReminderList(reminders=items, count=len(items))


# --- Workflow (kanban) tools -------------------------------------------------


@mcp.tool()
def get_workflow_lists() -> CalendarList:
    """The four kanban-style workflow lists (On-Deck / Active / Done / Blocked)."""
    rk = _remindkit()
    found: list[Any] = []
    for name in all_workflow_names():
        for cal in rk.calendars.search(name):
            if cal.name == name:
                found.append(cal)
                break
    cals = [calendar_from_obj(c) for c in found]
    return CalendarList(calendars=cals, count=len(cals))


def _move_to_role(reminder_id: str, role: WorkflowRole) -> Reminder:
    rk = _remindkit()
    cal = resolve_workflow_calendar(rk, role)
    moved = rk.move_reminder(reminder_id, cal.id)
    return reminder_from_obj(moved)


@mcp.tool()
def move_reminder_to_list(reminder_id: str, calendar_id: str) -> Reminder:
    """Move a reminder to an arbitrary list by ID."""
    return reminder_from_obj(_remindkit().move_reminder(reminder_id, calendar_id))


@mcp.tool()
def move_reminder_on_deck(reminder_id: str) -> Reminder:
    """Move a reminder to the On-Deck list (queued for work)."""
    return _move_to_role(reminder_id, "on_deck")


@mcp.tool()
def move_reminder_active(reminder_id: str) -> Reminder:
    """Move a reminder to the Active list (in progress)."""
    return _move_to_role(reminder_id, "active")


@mcp.tool()
def move_reminder_done(reminder_id: str) -> Reminder:
    """Move a reminder to the Done list (completed)."""
    return _move_to_role(reminder_id, "done")


@mcp.tool()
def move_reminder_blocked(reminder_id: str) -> Reminder:
    """Move a reminder to the Blocked list (waiting on something)."""
    return _move_to_role(reminder_id, "blocked")


# --- Batch operations --------------------------------------------------------


@mcp.tool()
def batch_create_reminders(
    titles: Annotated[list[str], Field(min_length=1, max_length=200)],
    calendar_id: str | None = None,
) -> ReminderList:
    """Create many reminders at once (titles only). Ideal for inbox capture."""
    rk = _remindkit()
    kwargs_base: dict[str, Any] = {}
    if calendar_id is not None:
        kwargs_base["calendar_id"] = calendar_id
    created = [reminder_from_obj(rk.create_reminder(title=t, **kwargs_base)) for t in titles]
    return ReminderList(reminders=created, count=len(created))


@mcp.tool()
def batch_complete_reminders(reminder_ids: Annotated[list[str], Field(min_length=1, max_length=500)]) -> ReminderList:
    """Mark many reminders done in one call."""
    rk = _remindkit()
    updated = [reminder_from_obj(rk.update_reminder(rid, is_completed=True)) for rid in reminder_ids]
    return ReminderList(reminders=updated, count=len(updated))


@mcp.tool()
def batch_delete_reminders(reminder_ids: Annotated[list[str], Field(min_length=1, max_length=500)]) -> OperationResult:
    """Delete many reminders. Cannot be undone."""
    rk = _remindkit()
    deleted = [rid for rid in reminder_ids if rk.delete_reminder(rid)]
    return OperationResult(
        success=len(deleted) == len(reminder_ids),
        message=f"Deleted {len(deleted)} of {len(reminder_ids)} reminders.",
        data={"deleted_ids": deleted},
    )


# --- Workflow-aware composite query (used by the plan_my_day prompt) --------


@mcp.tool()
def workflow_status() -> dict[str, Any]:
    """One-shot snapshot of the kanban: counts per list + top-3 active items.

    Designed for the ``plan_my_day`` prompt; cheap enough to call directly.
    """
    rk = _remindkit()
    snapshot: dict[str, Any] = {"prefix": workflow_list_name("on_deck").rsplit("On-Deck", 1)[0]}
    for role in ("on_deck", "active", "done", "blocked"):
        try:
            cal = resolve_workflow_calendar(rk, role)  # type: ignore[arg-type]
            items = list(rk.get_reminders(calendar_id=cal.id, is_completed=False))
            snapshot[role] = {
                "list": cal.name,
                "open_count": len(items),
                "preview": [reminder_from_obj(r).model_dump(mode="json") for r in items[:3]],
            }
        except WorkflowListMissingError as exc:
            snapshot[role] = {"missing": True, "expected_name": exc.expected_name}
    return snapshot


# --- Resources & prompts (registered in companion modules) -------------------

# Imported for side-effect (registers @mcp.resource / @mcp.prompt handlers).
from . import prompts as _prompts  # noqa: E402, F401
from . import resources as _resources  # noqa: E402, F401

# --- Entry points ------------------------------------------------------------


def _configure_logging() -> None:
    """Configure stderr-only logging respecting the MCP stdio transport."""
    level_name = os.environ.get("MCP_APPLE_REMINDERS_LOG_LEVEL", "WARNING").upper()
    level = getattr(logging, level_name, logging.WARNING)
    handler = logging.StreamHandler(stream=sys.stderr)
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s", datefmt="%Y-%m-%dT%H:%M:%S%z"),
    )
    root = logging.getLogger("mcp_apple_reminders")
    root.setLevel(level)
    root.handlers.clear()
    root.addHandler(handler)
    root.propagate = False


async def main() -> None:
    """Run the MCP stdio server."""
    _configure_logging()
    logger.debug("starting mcp-apple-reminders %s", __version__)
    await mcp.run_stdio_async()


def cli_main() -> int:
    """Synchronous entry point for the ``mcp-apple-reminders`` console script."""
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        return 130
    return 0


if __name__ == "__main__":
    raise SystemExit(cli_main())
