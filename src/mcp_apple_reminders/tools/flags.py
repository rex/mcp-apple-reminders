"""Reminder-attribute MCP tools — CL-2.5.

`set_urgent` toggles a reminder's urgency; `set_early_reminder` adds/clears a
lead-time alert before the due date; `add_section_and_assign` creates a new
section in the reminder's list and moves the reminder into it (vs `assign_section`,
which needs an existing section). Backed by the Obj-C ReminderKit helper.
"""

from __future__ import annotations

from typing import Optional

from mcp.server.fastmcp import Context

from .._native.reminderkit import ReminderKitHelperError, ReminderKitHelperUnavailable
from .._native.reminderkit_flags import (
    add_section_and_assign as helper_add_section_and_assign,
)
from .._native.reminderkit_flags import (
    set_early_reminder as helper_set_early_reminder,
)
from .._native.reminderkit_flags import (
    set_urgent as helper_set_urgent,
)
from ..results import WriteResult
from ..server import mcp
from ._annotations import CREATE, MUTATE


def _run(fn, *args, **kwargs) -> dict:
    """Run a helper wrapper, translating helper errors into ValueErrors."""
    try:
        return fn(*args, **kwargs)
    except ReminderKitHelperUnavailable as e:
        raise ValueError(f"ReminderKit helper not built. Run `make build-native`. ({e})") from e
    except ReminderKitHelperError as e:
        raise ValueError(e.message) from e


@mcp.tool(
    name="set_urgent",
    title="Set Urgent",
    annotations=MUTATE,
    description=(
        "Toggle the 'urgent' state on a reminder by its UUID (the urgency flag "
        "Reminders.app surfaces with an exclamation badge). Pass `urgent=true` "
        "to mark urgent, false to clear. Private ReminderKit API."
    ),
)
async def set_urgent(reminder_id: str, urgent: bool, ctx: Context) -> WriteResult:
    """Mark a reminder urgent (true) or not (false)."""
    if not reminder_id or not reminder_id.strip():
        raise ValueError("reminder_id is required and must be non-empty")
    resp = _run(helper_set_urgent, reminder_id, urgent)
    await ctx.info(f"Set urgent={urgent} on reminder {reminder_id}")
    return WriteResult.of(status=resp.get("status", "updated"), id=reminder_id, urgent=bool(urgent))


@mcp.tool(
    name="set_early_reminder",
    title="Set Early Reminder",
    annotations=MUTATE,
    description=(
        "Set or clear an Early Reminder (a lead-time alert that fires before the "
        "reminder's due date). `unit`: 0=minutes, 1=hours, 2=days, 3=weeks, "
        "4=months; `count`: how many units before due (non-zero). Pass "
        "`clear=true` to remove early reminders instead. The reminder must have a "
        "due date. Private ReminderKit API."
    ),
)
async def set_early_reminder(
    reminder_id: str,
    ctx: Context,
    unit: Optional[int] = None,
    count: Optional[int] = None,
    clear: bool = False,
) -> WriteResult:
    """Set (unit+count) or clear an Early Reminder lead-time alert."""
    if not reminder_id or not reminder_id.strip():
        raise ValueError("reminder_id is required and must be non-empty")
    resp = _run(helper_set_early_reminder, reminder_id, unit=unit, count=count, clear=clear)
    await ctx.info(f"Updated early reminder on {reminder_id} (clear={clear})")
    return WriteResult.of(status=resp.get("status", "updated"), id=reminder_id, cleared=bool(clear))


@mcp.tool(
    name="add_section_and_assign",
    title="Add Section and Assign",
    annotations=CREATE,
    description=(
        "Create a new section (named divider) in the reminder's parent list and "
        "move the reminder into it. Use this when the target section does not yet "
        "exist; use `assign_section` to move into an existing section. Private "
        "ReminderKit API."
    ),
)
async def add_section_and_assign(reminder_id: str, section_name: str, ctx: Context) -> WriteResult:
    """Create section `section_name` in the reminder's list and assign the reminder to it."""
    if not reminder_id or not reminder_id.strip():
        raise ValueError("reminder_id is required and must be non-empty")
    if not section_name or not section_name.strip():
        raise ValueError("section_name is required and must be non-empty")
    resp = _run(helper_add_section_and_assign, reminder_id, section_name)
    await ctx.info(f"Created section {section_name!r} and assigned reminder {reminder_id}")
    return WriteResult.of(status=resp.get("status", "updated"), id=reminder_id, section_name=section_name)
