"""Reminder CRUD MCP tools.

Six operations: create, update, complete (sugar over update), uncomplete (sugar),
get-by-id, delete. The complete/uncomplete handlers are thin wrappers that call
`update_reminder(is_completed=…)` so they stay in sync with the canonical update
path automatically.
"""

from __future__ import annotations

from typing import Any

from mcp.types import TextContent, Tool

from ..formatting import format_reminder, parse_datetime, parse_priority


def _handle_create_reminder(arguments: Any, remind) -> list[TextContent]:
    kwargs = {"title": arguments["title"]}

    if arguments.get("due_date"):
        kwargs["due_date"] = parse_datetime(arguments["due_date"])
    if arguments.get("notes"):
        kwargs["notes"] = arguments["notes"]
    if arguments.get("priority"):
        kwargs["priority"] = parse_priority(arguments["priority"])
    if arguments.get("url"):
        kwargs["url"] = arguments["url"]
    if arguments.get("calendar_id"):
        kwargs["calendar_id"] = arguments["calendar_id"]

    reminder = remind.create_reminder(**kwargs)
    return [TextContent(type="text", text="Reminder created successfully!\n\n" + format_reminder(reminder))]


def _handle_update_reminder(arguments: Any, remind) -> list[TextContent]:
    kwargs = {}

    if arguments.get("title"):
        kwargs["title"] = arguments["title"]
    if arguments.get("due_date"):
        kwargs["due_date"] = parse_datetime(arguments["due_date"])
    if arguments.get("notes") is not None:
        # Notes may be an empty string to explicitly clear them — preserve that.
        kwargs["notes"] = arguments["notes"]
    if arguments.get("priority"):
        kwargs["priority"] = parse_priority(arguments["priority"])
    if "url" in arguments:
        # Same as notes — empty string is a clear, not a no-op.
        kwargs["url"] = arguments["url"]
    if "is_completed" in arguments:
        kwargs["is_completed"] = arguments["is_completed"]

    reminder = remind.update_reminder(arguments["reminder_id"], **kwargs)
    return [TextContent(type="text", text="Reminder updated successfully!\n\n" + format_reminder(reminder))]


def _handle_complete_reminder(arguments: Any, remind) -> list[TextContent]:
    reminder = remind.update_reminder(arguments["reminder_id"], is_completed=True)
    return [TextContent(type="text", text="Reminder marked as complete!\n\n" + format_reminder(reminder))]


def _handle_uncomplete_reminder(arguments: Any, remind) -> list[TextContent]:
    reminder = remind.update_reminder(arguments["reminder_id"], is_completed=False)
    return [TextContent(type="text", text="Reminder marked as incomplete!\n\n" + format_reminder(reminder))]


def _handle_get_reminder(arguments: Any, remind) -> list[TextContent]:
    reminder = remind.get_reminder_by_id(arguments["reminder_id"])
    return [TextContent(type="text", text="Reminder Details:\n\n" + format_reminder(reminder))]


def _handle_delete_reminder(arguments: Any, remind) -> list[TextContent]:
    rid = arguments["reminder_id"]
    success = remind.delete_reminder(rid)
    if success:
        return [TextContent(type="text", text=f"Reminder {rid} deleted successfully.")]
    return [TextContent(type="text", text=f"Failed to delete reminder {rid}.")]


TOOLS: list[Tool] = [
    Tool(
        name="create_reminder",
        description="Create a new reminder in Apple Reminders. You can specify the title, due date, notes, priority, URL, and which calendar (list) to add it to. If no calendar is specified, it will be added to the default list.",
        inputSchema={
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "The title/name of the reminder"},
                "due_date": {
                    "type": "string",
                    "description": "ISO format datetime string (e.g., '2024-01-15T14:30:00'). Optional.",
                },
                "notes": {
                    "type": "string",
                    "description": "Additional notes or description for the reminder. Optional.",
                },
                "priority": {
                    "type": "string",
                    "description": "Priority level: 'none', 'low', 'medium', 'high', or integer 0-9. Default is 'none'. Optional.",
                },
                "url": {"type": "string", "description": "URL to associate with the reminder. Optional."},
                "calendar_id": {
                    "type": "string",
                    "description": "ID of the calendar (list) to add the reminder to. If not specified, uses the default calendar. Optional.",
                },
            },
            "required": ["title"],
        },
    ),
    Tool(
        name="update_reminder",
        description="Update an existing reminder. You can modify any combination of: title, due date, notes, priority, URL, and completion status. Only the fields you specify will be updated; others remain unchanged.",
        inputSchema={
            "type": "object",
            "properties": {
                "reminder_id": {"type": "string", "description": "The unique identifier of the reminder to update"},
                "title": {"type": "string", "description": "New title for the reminder. Optional."},
                "due_date": {
                    "type": "string",
                    "description": "New due date in ISO format (e.g., '2024-01-15T14:30:00'). Optional.",
                },
                "notes": {"type": "string", "description": "New notes/description. Optional."},
                "priority": {
                    "type": "string",
                    "description": "New priority: 'none', 'low', 'medium', 'high', or integer 0-9. Optional.",
                },
                "url": {"type": "string", "description": "New URL to associate with the reminder. Optional."},
                "is_completed": {
                    "type": "boolean",
                    "description": "Mark the reminder as completed (true) or incomplete (false). Optional.",
                },
            },
            "required": ["reminder_id"],
        },
    ),
    Tool(
        name="complete_reminder",
        description="Mark a reminder as completed. This is a convenience tool that's equivalent to calling update_reminder with is_completed=true.",
        inputSchema={
            "type": "object",
            "properties": {
                "reminder_id": {
                    "type": "string",
                    "description": "The unique identifier of the reminder to mark as complete",
                },
            },
            "required": ["reminder_id"],
        },
    ),
    Tool(
        name="uncomplete_reminder",
        description="Mark a reminder as incomplete/not done. This is useful for reopening a reminder that was previously completed.",
        inputSchema={
            "type": "object",
            "properties": {
                "reminder_id": {
                    "type": "string",
                    "description": "The unique identifier of the reminder to mark as incomplete",
                },
            },
            "required": ["reminder_id"],
        },
    ),
    Tool(
        name="get_reminder",
        description="Get a specific reminder by its unique ID. Returns all details about the reminder including title, due date, notes, priority, completion status, and more.",
        inputSchema={
            "type": "object",
            "properties": {
                "reminder_id": {"type": "string", "description": "The unique identifier of the reminder"},
            },
            "required": ["reminder_id"],
        },
    ),
    Tool(
        name="delete_reminder",
        description="Permanently delete a reminder. This action cannot be undone. The reminder will be removed from Apple Reminders entirely.",
        inputSchema={
            "type": "object",
            "properties": {
                "reminder_id": {"type": "string", "description": "The unique identifier of the reminder to delete"},
            },
            "required": ["reminder_id"],
        },
    ),
]

HANDLERS = {
    "create_reminder": _handle_create_reminder,
    "update_reminder": _handle_update_reminder,
    "complete_reminder": _handle_complete_reminder,
    "uncomplete_reminder": _handle_uncomplete_reminder,
    "get_reminder": _handle_get_reminder,
    "delete_reminder": _handle_delete_reminder,
}
