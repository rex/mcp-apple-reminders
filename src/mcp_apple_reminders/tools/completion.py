"""Completion shortcut tools.

`complete_reminder` / `uncomplete_reminder` are thin sugar over
`update_reminder(is_completed=…)`, split out of `tools/reminders.py` to keep
each module under the architecture line cap. They route through the same
EventKit write path so they stay in sync with the canonical update.
"""

from __future__ import annotations

from mcp.server.fastmcp import Context

from ..lifespan import bridge_from_ctx as _bridge_from_ctx
from ..models import Reminder, native_reminder_to_pydantic
from ..server import mcp
from ._annotations import MUTATE


@mcp.tool(
    name="complete_reminder",
    title="Complete Reminder",
    annotations=MUTATE,
    description=(
        "Mark a reminder as completed. This is a convenience tool that's "
        "equivalent to calling update_reminder with is_completed=true."
    ),
)
async def complete_reminder(reminder_id: str, ctx: Context) -> Reminder:
    """Mark a reminder as completed.

    Args:
        reminder_id: The unique identifier of the reminder to mark as complete.
    """
    bridge = _bridge_from_ctx(ctx)
    result = native_reminder_to_pydantic(bridge.update_reminder(reminder_id, is_completed=True))
    await ctx.info(f"Completed reminder {reminder_id}")
    return result


@mcp.tool(
    name="uncomplete_reminder",
    title="Uncomplete Reminder",
    annotations=MUTATE,
    description=(
        "Mark a reminder as incomplete/not done. This is useful for reopening "
        "a reminder that was previously completed."
    ),
)
async def uncomplete_reminder(reminder_id: str, ctx: Context) -> Reminder:
    """Mark a reminder as incomplete.

    Args:
        reminder_id: The unique identifier of the reminder to mark as incomplete.
    """
    bridge = _bridge_from_ctx(ctx)
    result = native_reminder_to_pydantic(bridge.update_reminder(reminder_id, is_completed=False))
    await ctx.info(f"Uncompleted reminder {reminder_id}")
    return result
