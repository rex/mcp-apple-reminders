"""Workflow-list MCP tools — FastMCP edition.

Six operations covering the `Claude-*` workflow lists (Pierce's pre-existing
conversational task-management system, not the new `Agents-*` visibility
plane):
- `get_workflow_lists` — enumerate calendars whose name starts with `Claude-`
- `move_reminder_to_list` — generic move to an explicit calendar_id
- Four sugar moves: `move_reminder_on_deck`, `move_reminder_active`,
  `move_reminder_done`, `move_reminder_blocked`. Each finds its target
  calendar by name search and delegates to the underlying `move_reminder`.

The sugar moves return an explicit error message if the target `Claude-*`
list isn't present; they don't auto-create lists (calendar creation is
delivered in Slice 1.2).
"""

from __future__ import annotations

from mcp.server.fastmcp import Context

from ..lifespan import bridge_from_ctx as _bridge_from_ctx
from ..models import Calendar, Reminder, native_calendar_to_pydantic, native_reminder_to_pydantic
from ..server import mcp


async def _move_to_named_list(bridge, reminder_id: str, list_name: str, ctx: Context) -> Reminder:
    """Shared implementation for the four sugar move handlers."""
    calendars = list(bridge.calendars.search(list_name))
    if not calendars:
        await ctx.error(f"Move target {list_name!r} not found; create the list in Apple Reminders first.")
        raise ValueError(f"'{list_name}' calendar not found. Please create it in Apple Reminders first.")
    target = calendars[0]
    moved = native_reminder_to_pydantic(bridge.move_reminder(reminder_id, target.id))
    await ctx.info(f"Moved reminder {reminder_id} to {list_name!r}")
    return moved


@mcp.tool(
    name="get_workflow_lists",
    description=(
        "Get all workflow lists (calendars starting with 'Claude-'). These "
        "are special lists used for workflow management with Claude, such as "
        "Claude-Brain-Dump, Claude-On-Deck, Claude-Active, Claude-Done, and "
        "Claude-Waiting."
    ),
)
async def get_workflow_lists(ctx: Context) -> list[Calendar]:
    """Enumerate every calendar whose name starts with 'Claude-'."""
    bridge = _bridge_from_ctx(ctx)
    results = [native_calendar_to_pydantic(c) for c in bridge.calendars.search("Claude-")]
    if not results:
        await ctx.warning("No 'Claude-*' workflow lists found. Create them in Apple Reminders first.")
    return results


@mcp.tool(
    name="move_reminder_to_list",
    description=(
        "Move a reminder to a different calendar/list. This allows you to "
        "organize reminders by moving them between different lists."
    ),
)
async def move_reminder_to_list(reminder_id: str, calendar_id: str, ctx: Context) -> Reminder:
    """Move a reminder to a different calendar.

    Args:
        reminder_id: The unique identifier of the reminder to move.
        calendar_id: The unique identifier of the target calendar/list.
    """
    bridge = _bridge_from_ctx(ctx)
    moved = native_reminder_to_pydantic(bridge.move_reminder(reminder_id, calendar_id))
    await ctx.info(f"Moved reminder {reminder_id} to calendar {calendar_id}")
    return moved


@mcp.tool(
    name="move_reminder_on_deck",
    description=(
        "Move a reminder to the 'Claude-On-Deck' workflow list. This indicates "
        "the task is queued and ready to be worked on next. Convenience "
        "function for workflow management."
    ),
)
async def move_reminder_on_deck(reminder_id: str, ctx: Context) -> Reminder:
    """Move a reminder to the Claude-On-Deck workflow list.

    Args:
        reminder_id: The unique identifier of the reminder to move.
    """
    return await _move_to_named_list(_bridge_from_ctx(ctx), reminder_id, "Claude-On-Deck", ctx)


@mcp.tool(
    name="move_reminder_active",
    description=(
        "Move a reminder to the 'Claude-Active' workflow list. This indicates "
        "the task is currently being worked on. Convenience function for "
        "workflow management."
    ),
)
async def move_reminder_active(reminder_id: str, ctx: Context) -> Reminder:
    """Move a reminder to the Claude-Active workflow list.

    Args:
        reminder_id: The unique identifier of the reminder to move.
    """
    return await _move_to_named_list(_bridge_from_ctx(ctx), reminder_id, "Claude-Active", ctx)


@mcp.tool(
    name="move_reminder_done",
    description=(
        "Move a reminder to the 'Claude-Done' workflow list. This indicates "
        "the task has been completed. Convenience function for workflow "
        "management."
    ),
)
async def move_reminder_done(reminder_id: str, ctx: Context) -> Reminder:
    """Move a reminder to the Claude-Done workflow list.

    Args:
        reminder_id: The unique identifier of the reminder to move.
    """
    return await _move_to_named_list(_bridge_from_ctx(ctx), reminder_id, "Claude-Done", ctx)


@mcp.tool(
    name="move_reminder_blocked",
    description=(
        "Move a reminder to the 'Claude-Waiting' workflow list. This indicates "
        "the task is blocked or waiting for external input. Convenience "
        "function for workflow management."
    ),
)
async def move_reminder_blocked(reminder_id: str, ctx: Context) -> Reminder:
    """Move a reminder to the Claude-Waiting workflow list.

    Args:
        reminder_id: The unique identifier of the reminder to move.
    """
    return await _move_to_named_list(_bridge_from_ctx(ctx), reminder_id, "Claude-Waiting", ctx)
