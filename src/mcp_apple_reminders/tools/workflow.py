"""Workflow-list MCP tools.

Six operations covering the `Claude-*` workflow lists (Pierce's pre-existing
conversational task-management system, not the new `Agents-*` visibility plane):
- `get_workflow_lists` — enumerate calendars whose name starts with `Claude-`
- `move_reminder_to_list` — generic move to an explicit calendar_id
- Four sugar moves: `move_reminder_on_deck`, `move_reminder_active`,
  `move_reminder_done`, `move_reminder_blocked`. Each finds its target
  calendar by name search and delegates to the underlying `move_reminder`.

The sugar moves return an explicit error message if the target `Claude-*` list
isn't present; they don't auto-create lists (calendar creation is a P0 gap).
"""

from __future__ import annotations

from typing import Any

from mcp.types import TextContent, Tool

from ..formatting import format_reminder


def _move_to_named_list(remind, reminder_id: str, list_name: str, friendly_state: str) -> list[TextContent]:
    """Shared implementation for the four sugar move handlers."""
    calendars = list(remind.calendars.search(list_name))
    if not calendars:
        return [
            TextContent(
                type="text",
                text=f"Error: '{list_name}' calendar not found. Please create it in Apple Reminders first.",
            )
        ]
    target = calendars[0]
    reminder = remind.move_reminder(reminder_id, target.id)
    return [
        TextContent(
            type="text",
            text=f"Reminder moved to '{list_name}' ({friendly_state})!\n\n" + format_reminder(reminder),
        )
    ]


def _handle_get_workflow_lists(arguments: Any, remind) -> list[TextContent]:
    calendars = list(remind.calendars.search("Claude-"))
    if not calendars:
        return [TextContent(type="text", text="No workflow lists found (calendars starting with 'Claude-').")]

    parts = [f"Found {len(calendars)} workflow list(s):", ""]
    for cal in calendars:
        parts.append(f"Name: {cal.name}")
        parts.append(f"ID: {cal.id}")
        parts.append(f"Color: {cal.color}")
        parts.append(f"Default: {'Yes' if cal.is_default else 'No'}")
        parts.append("-" * 40)
    return [TextContent(type="text", text="\n".join(parts))]


def _handle_move_reminder_to_list(arguments: Any, remind) -> list[TextContent]:
    reminder = remind.move_reminder(arguments["reminder_id"], arguments["calendar_id"])
    calendar = remind.calendars.get_by_id(arguments["calendar_id"])
    return [
        TextContent(
            type="text",
            text=f"Reminder moved successfully to '{calendar.name}'!\n\n" + format_reminder(reminder),
        )
    ]


def _handle_move_reminder_on_deck(arguments: Any, remind) -> list[TextContent]:
    return _move_to_named_list(remind, arguments["reminder_id"], "Claude-On-Deck", "queued for work")


def _handle_move_reminder_active(arguments: Any, remind) -> list[TextContent]:
    return _move_to_named_list(remind, arguments["reminder_id"], "Claude-Active", "now in progress")


def _handle_move_reminder_done(arguments: Any, remind) -> list[TextContent]:
    return _move_to_named_list(remind, arguments["reminder_id"], "Claude-Done", "task completed")


def _handle_move_reminder_blocked(arguments: Any, remind) -> list[TextContent]:
    return _move_to_named_list(remind, arguments["reminder_id"], "Claude-Waiting", "task blocked/waiting")


TOOLS: list[Tool] = [
    Tool(
        name="get_workflow_lists",
        description="Get all workflow lists (calendars starting with 'Claude-'). These are special lists used for workflow management with Claude, such as Claude-Brain-Dump, Claude-On-Deck, Claude-Active, Claude-Done, and Claude-Waiting.",
        inputSchema={"type": "object", "properties": {}, "required": []},
    ),
    Tool(
        name="move_reminder_to_list",
        description="Move a reminder to a different calendar/list. This allows you to organize reminders by moving them between different lists.",
        inputSchema={
            "type": "object",
            "properties": {
                "reminder_id": {"type": "string", "description": "The unique identifier of the reminder to move"},
                "calendar_id": {"type": "string", "description": "The unique identifier of the target calendar/list"},
            },
            "required": ["reminder_id", "calendar_id"],
        },
    ),
    Tool(
        name="move_reminder_on_deck",
        description="Move a reminder to the 'Claude-On-Deck' workflow list. This indicates the task is queued and ready to be worked on next. Convenience function for workflow management.",
        inputSchema={
            "type": "object",
            "properties": {
                "reminder_id": {"type": "string", "description": "The unique identifier of the reminder to move"},
            },
            "required": ["reminder_id"],
        },
    ),
    Tool(
        name="move_reminder_active",
        description="Move a reminder to the 'Claude-Active' workflow list. This indicates the task is currently being worked on. Convenience function for workflow management.",
        inputSchema={
            "type": "object",
            "properties": {
                "reminder_id": {"type": "string", "description": "The unique identifier of the reminder to move"},
            },
            "required": ["reminder_id"],
        },
    ),
    Tool(
        name="move_reminder_done",
        description="Move a reminder to the 'Claude-Done' workflow list. This indicates the task has been completed. Convenience function for workflow management.",
        inputSchema={
            "type": "object",
            "properties": {
                "reminder_id": {"type": "string", "description": "The unique identifier of the reminder to move"},
            },
            "required": ["reminder_id"],
        },
    ),
    Tool(
        name="move_reminder_blocked",
        description="Move a reminder to the 'Claude-Waiting' workflow list. This indicates the task is blocked or waiting for external input. Convenience function for workflow management.",
        inputSchema={
            "type": "object",
            "properties": {
                "reminder_id": {"type": "string", "description": "The unique identifier of the reminder to move"},
            },
            "required": ["reminder_id"],
        },
    ),
]

HANDLERS = {
    "get_workflow_lists": _handle_get_workflow_lists,
    "move_reminder_to_list": _handle_move_reminder_to_list,
    "move_reminder_on_deck": _handle_move_reminder_on_deck,
    "move_reminder_active": _handle_move_reminder_active,
    "move_reminder_done": _handle_move_reminder_done,
    "move_reminder_blocked": _handle_move_reminder_blocked,
}
