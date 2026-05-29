"""Section + subtask-shape tools — slices 1.5 + 1.8.

Lives apart from `tools/reminders.py` so each file stays under the 400-line
architecture-gate limit. FastMCP picks up the decorators at import time
via `tools/__init__.py`.
"""

from __future__ import annotations

from typing import Optional

from mcp.server.fastmcp import Context

from .._native.reminderkit import (
    ReminderKitHelperError,
    ReminderKitHelperUnavailable,
)
from .._native.reminderkit_actions import (
    assign_section as helper_assign_section,
)
from .._native.sqlite import Reader, RemindersDBUnavailable
from ..lifespan import AppContext
from ..models import Reminder
from ..server import mcp


def _app_context(ctx: Context) -> AppContext:
    return ctx.request_context.lifespan_context


@mcp.tool(
    name="get_subtasks",
    description=(
        "Get the subtasks of a reminder. Returns Reminder objects whose "
        "parent_reminder_id is the supplied id. Reads from the SQLite cache "
        "(sub-millisecond). Empty list if the parent has no subtasks."
    ),
)
async def get_subtasks(reminder_id: str, ctx: Context) -> list[Reminder]:
    """List the subtasks of `reminder_id`."""
    app = _app_context(ctx)
    try:
        with app.open_sqlite() as conn:
            raw = list(Reader(conn).iter_subtasks(reminder_id))
            subtasks = [r.model_copy(update={"parent_reminder_id": reminder_id}) for r in raw]
            await ctx.debug(f"get_subtasks({reminder_id}): {len(subtasks)} found")
            return subtasks
    except RemindersDBUnavailable as e:
        await ctx.warning(f"SQLite read path unavailable ({e}); cannot list subtasks.")
        return []


@mcp.tool(
    name="set_parent",
    description=(
        "Reassign or detach a reminder's parent. DEFERRED — the borrowed "
        "Obj-C helper does not currently expose a parent-reassignment "
        "action. Tracked for a follow-up patch that extends the helper."
    ),
)
async def set_parent(
    reminder_id: str,
    ctx: Context,
    new_parent_id: Optional[str] = None,
) -> dict:
    """Reassign or detach the parent of a reminder. Deferred — see description."""
    await ctx.error(
        "set_parent: not yet implemented — the borrowed Obj-C ReminderKit "
        "helper does not expose a parent-reassignment action. Tracked for a "
        "follow-up patch that extends the helper."
    )
    raise ValueError(
        "set_parent is not yet implemented. Use `create_reminder(parent_reminder_id=...)` "
        "to create a new subtask under a parent; deletion of the original is a "
        "manual cleanup until the helper gains a set_parent action."
    )


@mcp.tool(
    name="assign_section",
    description=(
        "Move a reminder into a section within its parent list. Sections are "
        "the in-list dividers exposed by Reminders.app. Pass the reminder ID "
        "and the section name (case-sensitive); the tool resolves the name "
        "against existing sections in the parent list. If the section does "
        "not exist, the error message lists every section that does."
    ),
)
async def assign_section(reminder_id: str, section_name: str, ctx: Context) -> Reminder:
    """Assign a reminder to a section in its parent list."""
    if not reminder_id or not reminder_id.strip():
        raise ValueError("reminder_id is required and must be non-empty")
    if not section_name or not section_name.strip():
        raise ValueError("section_name is required and must be non-empty")

    app = _app_context(ctx)
    try:
        with app.open_sqlite() as conn:
            reader = Reader(conn)
            reminder = reader.get_reminder_by_id(reminder_id)
            if reminder is None:
                raise ValueError(f"Reminder {reminder_id!r} not found.")
            sections = reader.list_sections_in_calendar(reminder.list_id)
    except RemindersDBUnavailable as e:
        await ctx.error(f"SQLite unavailable; cannot resolve section: {e}")
        raise ValueError(f"SQLite read path unavailable ({e}); needed to resolve the section name.") from e

    match = next(((sid, sname) for sid, sname in sections if sname == section_name), None)
    if match is None:
        existing = ", ".join(sorted(s for _sid, s in sections)) or "(none)"
        raise ValueError(
            f"Section {section_name!r} not found in calendar {reminder.list_id!r}. " f"Existing sections: {existing}"
        )

    section_id, _ = match

    try:
        helper_assign_section(reminder_id, section_id)
    except ReminderKitHelperUnavailable as e:
        await ctx.error(f"assign_section via ReminderKit unavailable: {e}")
        raise ValueError(f"ReminderKit helper not built. Run `make build-native`. ({e})") from e
    except ReminderKitHelperError as e:
        await ctx.error(f"assign_section failed: {e.message}")
        raise ValueError(e.message) from e

    await ctx.info(f"Assigned reminder {reminder_id} to section {section_name!r}")
    return reminder.model_copy(update={"section_name": section_name})
