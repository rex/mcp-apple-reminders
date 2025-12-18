"""MCP Apple Reminders Server Implementation.

This module implements a Model Context Protocol (MCP) server that provides comprehensive
integration with Apple Reminders. It exposes tools for managing reminders, calendars,
and related operations through the pyremindkit library.

The server is designed to work seamlessly with Claude for macOS and other MCP-compatible clients.
"""

import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

# Add the pyremindkit library to the path
# Use relative path from this file's location
_current_file = Path(__file__).resolve()
_project_root = _current_file.parent.parent.parent
_pyremindkit_path = _project_root / "libs" / "pyremindkit" / "src"
sys.path.insert(0, str(_pyremindkit_path))

from pyremindkit import Priority, RemindKit, Reminder

from mcp.server import Server
from mcp.types import Tool, TextContent, ImageContent, EmbeddedResource
import mcp.server.stdio


# Initialize the RemindKit instance
# This will request permissions on first run if not already granted
try:
    remind = RemindKit()
except PermissionError as e:
    print(f"Error: Unable to access Apple Reminders. Please grant permissions in System Settings > Privacy & Security > Reminders.", file=sys.stderr)
    sys.exit(1)
except Exception as e:
    print(f"Error initializing RemindKit: {e}", file=sys.stderr)
    sys.exit(1)


# Create the MCP server instance
app = Server("mcp-apple-reminders")


def format_reminder(reminder: Reminder) -> str:
    """Format a reminder object as a human-readable string.

    Args:
        reminder: The Reminder object to format

    Returns:
        A formatted string representation of the reminder
    """
    parts = [
        f"ID: {reminder.id}",
        f"Title: {reminder.title}",
        f"Completed: {'Yes' if reminder.completed else 'No'}",
    ]

    if reminder.due_date:
        parts.append(f"Due Date: {reminder.due_date.strftime('%Y-%m-%d %H:%M:%S')}")

    if reminder.notes:
        parts.append(f"Notes: {reminder.notes}")

    if reminder.url:
        parts.append(f"URL: {reminder.url}")

    # Format priority
    priority_map = {0: "None", 1: "Low", 5: "Medium", 9: "High"}
    priority_str = priority_map.get(reminder.priority, f"Custom ({reminder.priority})")
    parts.append(f"Priority: {priority_str}")

    parts.append(f"List ID: {reminder.list_id}")

    if reminder.created_date:
        parts.append(f"Created: {reminder.created_date.strftime('%Y-%m-%d %H:%M:%S')}")

    if reminder.modified_date:
        parts.append(f"Modified: {reminder.modified_date.strftime('%Y-%m-%d %H:%M:%S')}")

    parts.append(f"Flagged: {'Yes' if reminder.flagged else 'No'}")

    return "\n".join(parts)


def parse_datetime(date_string: str) -> datetime:
    """Parse a datetime string in ISO format.

    Args:
        date_string: ISO format datetime string (e.g., "2024-01-15T14:30:00")

    Returns:
        datetime object

    Raises:
        ValueError: If the date string is invalid
    """
    try:
        return datetime.fromisoformat(date_string)
    except ValueError:
        raise ValueError(f"Invalid datetime format: {date_string}. Expected ISO format (e.g., '2024-01-15T14:30:00')")


def parse_priority(priority_str: str) -> int:
    """Parse a priority string to an integer value.

    Apple Reminders uses these priority values:
    - 0: None
    - 1-4: Low (we use 1)
    - 5: Medium
    - 6-9: High (we use 9)

    Args:
        priority_str: Priority as string ("none", "low", "medium", "high") or integer string

    Returns:
        Integer priority value (0, 1, 5, or 9)

    Raises:
        ValueError: If the priority string is invalid
    """
    priority_lower = priority_str.lower().strip()

    # Try direct integer parsing first
    try:
        val = int(priority_lower)
        if 0 <= val <= 9:
            return val
    except ValueError:
        pass

    # Parse named priorities
    priority_map = {
        "none": 0,
        "low": 1,
        "medium": 5,
        "high": 9,
    }

    if priority_lower in priority_map:
        return priority_map[priority_lower]

    raise ValueError(f"Invalid priority: {priority_str}. Expected 'none', 'low', 'medium', 'high', or integer 0-9")


@app.list_tools()
async def list_tools() -> list[Tool]:
    """List all available tools provided by this MCP server.

    This function is called by the MCP client to discover available operations.
    Each tool represents a specific operation that can be performed on Apple Reminders.

    Returns:
        List of Tool objects describing available operations
    """
    return [
        # Calendar Management Tools
        Tool(
            name="list_calendars",
            description="List all available reminder calendars (lists). Returns all reminder lists accessible to the user, including their IDs, names, colors, and whether they are the default list.",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": [],
            },
        ),
        Tool(
            name="get_calendar",
            description="Get a specific calendar (list) by name. Searches for a reminder list with the exact name provided.",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "The exact name of the calendar to retrieve",
                    },
                },
                "required": ["name"],
            },
        ),
        Tool(
            name="get_calendar_by_id",
            description="Get a specific calendar (list) by its unique ID. More reliable than searching by name.",
            inputSchema={
                "type": "object",
                "properties": {
                    "calendar_id": {
                        "type": "string",
                        "description": "The unique identifier of the calendar",
                    },
                },
                "required": ["calendar_id"],
            },
        ),
        Tool(
            name="search_calendars",
            description="Search for calendars (lists) by partial name match. Case-insensitive search that returns all calendars containing the query string.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query string (partial name match)",
                    },
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="get_default_calendar",
            description="Get the default calendar (list) for new reminders. This is the list that Apple Reminders uses by default when creating new items.",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": [],
            },
        ),

        # Reminder CRUD Operations
        Tool(
            name="create_reminder",
            description="Create a new reminder in Apple Reminders. You can specify the title, due date, notes, priority, URL, and which calendar (list) to add it to. If no calendar is specified, it will be added to the default list.",
            inputSchema={
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "The title/name of the reminder",
                    },
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
                    "url": {
                        "type": "string",
                        "description": "URL to associate with the reminder. Optional.",
                    },
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
                    "reminder_id": {
                        "type": "string",
                        "description": "The unique identifier of the reminder to update",
                    },
                    "title": {
                        "type": "string",
                        "description": "New title for the reminder. Optional.",
                    },
                    "due_date": {
                        "type": "string",
                        "description": "New due date in ISO format (e.g., '2024-01-15T14:30:00'). Optional.",
                    },
                    "notes": {
                        "type": "string",
                        "description": "New notes/description. Optional.",
                    },
                    "priority": {
                        "type": "string",
                        "description": "New priority: 'none', 'low', 'medium', 'high', or integer 0-9. Optional.",
                    },
                    "url": {
                        "type": "string",
                        "description": "New URL to associate with the reminder. Optional.",
                    },
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
                    "reminder_id": {
                        "type": "string",
                        "description": "The unique identifier of the reminder",
                    },
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
                    "reminder_id": {
                        "type": "string",
                        "description": "The unique identifier of the reminder to delete",
                    },
                },
                "required": ["reminder_id"],
            },
        ),

        # Reminder Query Operations
        Tool(
            name="get_reminders",
            description="Get reminders with optional filters. You can filter by: due date range, completion status, priority level, and specific calendar. Without filters, returns all reminders from all calendars.",
            inputSchema={
                "type": "object",
                "properties": {
                    "due_after": {
                        "type": "string",
                        "description": "Only return reminders due after this date (ISO format). Optional.",
                    },
                    "due_before": {
                        "type": "string",
                        "description": "Only return reminders due before this date (ISO format). Optional.",
                    },
                    "is_completed": {
                        "type": "boolean",
                        "description": "Filter by completion status: true for completed, false for incomplete, omit for all. Optional.",
                    },
                    "priority": {
                        "type": "string",
                        "description": "Filter by priority: 'none', 'low', 'medium', or 'high'. Optional.",
                    },
                    "calendar_id": {
                        "type": "string",
                        "description": "Only return reminders from this specific calendar. Optional.",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of reminders to return. Optional.",
                    },
                },
                "required": [],
            },
        ),
        Tool(
            name="search_reminders",
            description="Search for reminders by text query. Searches both the reminder title and notes fields. Case-insensitive partial matching.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query string to match against titles and notes",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results to return. Optional.",
                    },
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="get_next_reminder",
            description="Get the next upcoming incomplete reminder based on due date. Returns the soonest incomplete reminder that has a due date set. Returns nothing if no upcoming reminders exist.",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": [],
            },
        ),
        Tool(
            name="get_overdue_reminders",
            description="Get all incomplete reminders that are overdue (due date is in the past). Useful for finding tasks that need immediate attention.",
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results to return. Optional.",
                    },
                },
                "required": [],
            },
        ),
        Tool(
            name="get_today_reminders",
            description="Get all reminders due today (both completed and incomplete). Useful for daily task management and review.",
            inputSchema={
                "type": "object",
                "properties": {
                    "include_completed": {
                        "type": "boolean",
                        "description": "Whether to include completed reminders. Default is false (only incomplete). Optional.",
                    },
                },
                "required": [],
            },
        ),

        # Workflow Management Tools
        Tool(
            name="get_workflow_lists",
            description="Get all workflow lists (calendars starting with 'Claude-'). These are special lists used for workflow management with Claude, such as Claude-Brain-Dump, Claude-On-Deck, Claude-Active, Claude-Done, and Claude-Waiting.",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": [],
            },
        ),
        Tool(
            name="move_reminder_to_list",
            description="Move a reminder to a different calendar/list. This allows you to organize reminders by moving them between different lists.",
            inputSchema={
                "type": "object",
                "properties": {
                    "reminder_id": {
                        "type": "string",
                        "description": "The unique identifier of the reminder to move",
                    },
                    "calendar_id": {
                        "type": "string",
                        "description": "The unique identifier of the target calendar/list",
                    },
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
                    "reminder_id": {
                        "type": "string",
                        "description": "The unique identifier of the reminder to move",
                    },
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
                    "reminder_id": {
                        "type": "string",
                        "description": "The unique identifier of the reminder to move",
                    },
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
                    "reminder_id": {
                        "type": "string",
                        "description": "The unique identifier of the reminder to move",
                    },
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
                    "reminder_id": {
                        "type": "string",
                        "description": "The unique identifier of the reminder to move",
                    },
                },
                "required": ["reminder_id"],
            },
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: Any) -> list[TextContent]:
    """Handle tool execution requests from the MCP client.

    This function is called when the client wants to execute a specific tool.
    It routes the request to the appropriate handler based on the tool name.

    Args:
        name: The name of the tool to execute
        arguments: Dictionary of arguments for the tool

    Returns:
        List containing a TextContent with the tool's response

    Raises:
        ValueError: If the tool name is not recognized or arguments are invalid
        RuntimeError: If the tool execution fails
    """
    try:
        # Calendar Management Tools
        if name == "list_calendars":
            calendars = list(remind.calendars.list())
            if not calendars:
                return [TextContent(type="text", text="No calendars found.")]

            result = f"Found {len(calendars)} calendar(s):\n\n"
            for cal in calendars:
                result += f"Name: {cal.name}\n"
                result += f"ID: {cal.id}\n"
                result += f"Color: {cal.color}\n"
                result += f"Default: {'Yes' if cal.is_default else 'No'}\n"
                result += f"Owner: {cal.owner}\n"
                result += "-" * 40 + "\n"

            return [TextContent(type="text", text=result)]

        elif name == "get_calendar":
            calendar = remind.calendars.get(arguments["name"])
            result = f"Calendar Found:\n"
            result += f"Name: {calendar.name}\n"
            result += f"ID: {calendar.id}\n"
            result += f"Color: {calendar.color}\n"
            result += f"Default: {'Yes' if calendar.is_default else 'No'}\n"
            result += f"Owner: {calendar.owner}\n"
            return [TextContent(type="text", text=result)]

        elif name == "get_calendar_by_id":
            calendar = remind.calendars.get_by_id(arguments["calendar_id"])
            result = f"Calendar Found:\n"
            result += f"Name: {calendar.name}\n"
            result += f"ID: {calendar.id}\n"
            result += f"Color: {calendar.color}\n"
            result += f"Default: {'Yes' if calendar.is_default else 'No'}\n"
            result += f"Owner: {calendar.owner}\n"
            return [TextContent(type="text", text=result)]

        elif name == "search_calendars":
            calendars = list(remind.calendars.search(arguments["query"]))
            if not calendars:
                return [TextContent(type="text", text=f"No calendars found matching '{arguments['query']}'.")]

            result = f"Found {len(calendars)} calendar(s) matching '{arguments['query']}':\n\n"
            for cal in calendars:
                result += f"Name: {cal.name}\n"
                result += f"ID: {cal.id}\n"
                result += f"Color: {cal.color}\n"
                result += f"Default: {'Yes' if cal.is_default else 'No'}\n"
                result += "-" * 40 + "\n"

            return [TextContent(type="text", text=result)]

        elif name == "get_default_calendar":
            calendar = remind.calendars.get_default()
            result = f"Default Calendar:\n"
            result += f"Name: {calendar.name}\n"
            result += f"ID: {calendar.id}\n"
            result += f"Color: {calendar.color}\n"
            result += f"Owner: {calendar.owner}\n"
            return [TextContent(type="text", text=result)]

        # Reminder CRUD Operations
        elif name == "create_reminder":
            # Prepare kwargs for reminder creation
            kwargs = {"title": arguments["title"]}

            if "due_date" in arguments and arguments["due_date"]:
                kwargs["due_date"] = parse_datetime(arguments["due_date"])

            if "notes" in arguments and arguments["notes"]:
                kwargs["notes"] = arguments["notes"]

            if "priority" in arguments and arguments["priority"]:
                kwargs["priority"] = parse_priority(arguments["priority"])

            if "url" in arguments and arguments["url"]:
                kwargs["url"] = arguments["url"]

            if "calendar_id" in arguments and arguments["calendar_id"]:
                kwargs["calendar_id"] = arguments["calendar_id"]

            reminder = remind.create_reminder(**kwargs)

            result = "Reminder created successfully!\n\n"
            result += format_reminder(reminder)
            return [TextContent(type="text", text=result)]

        elif name == "update_reminder":
            # Prepare kwargs for reminder update
            kwargs = {}

            if "title" in arguments and arguments["title"]:
                kwargs["title"] = arguments["title"]

            if "due_date" in arguments and arguments["due_date"]:
                kwargs["due_date"] = parse_datetime(arguments["due_date"])

            if "notes" in arguments and arguments["notes"]:
                kwargs["notes"] = arguments["notes"]

            if "priority" in arguments and arguments["priority"]:
                kwargs["priority"] = parse_priority(arguments["priority"])

            if "url" in arguments and arguments["url"]:
                kwargs["url"] = arguments["url"]

            if "is_completed" in arguments:
                kwargs["is_completed"] = arguments["is_completed"]

            reminder = remind.update_reminder(arguments["reminder_id"], **kwargs)

            result = "Reminder updated successfully!\n\n"
            result += format_reminder(reminder)
            return [TextContent(type="text", text=result)]

        elif name == "complete_reminder":
            reminder = remind.update_reminder(
                arguments["reminder_id"],
                is_completed=True
            )
            result = "Reminder marked as complete!\n\n"
            result += format_reminder(reminder)
            return [TextContent(type="text", text=result)]

        elif name == "uncomplete_reminder":
            reminder = remind.update_reminder(
                arguments["reminder_id"],
                is_completed=False
            )
            result = "Reminder marked as incomplete!\n\n"
            result += format_reminder(reminder)
            return [TextContent(type="text", text=result)]

        elif name == "get_reminder":
            reminder = remind.get_reminder_by_id(arguments["reminder_id"])
            result = "Reminder Details:\n\n"
            result += format_reminder(reminder)
            return [TextContent(type="text", text=result)]

        elif name == "delete_reminder":
            success = remind.delete_reminder(arguments["reminder_id"])
            if success:
                return [TextContent(type="text", text=f"Reminder {arguments['reminder_id']} deleted successfully.")]
            else:
                return [TextContent(type="text", text=f"Failed to delete reminder {arguments['reminder_id']}.")]

        # Reminder Query Operations
        elif name == "get_reminders":
            # Parse filter arguments
            kwargs = {}

            if "due_after" in arguments and arguments["due_after"]:
                kwargs["due_after"] = parse_datetime(arguments["due_after"])

            if "due_before" in arguments and arguments["due_before"]:
                kwargs["due_before"] = parse_datetime(arguments["due_before"])

            if "is_completed" in arguments:
                kwargs["is_completed"] = arguments["is_completed"]

            if "priority" in arguments and arguments["priority"]:
                priority_str = arguments["priority"].lower()
                priority_map = {
                    "none": Priority.NONE,
                    "low": Priority.LOW,
                    "medium": Priority.MEDIUM,
                    "high": Priority.HIGH,
                }
                if priority_str in priority_map:
                    kwargs["priority"] = priority_map[priority_str]

            if "calendar_id" in arguments and arguments["calendar_id"]:
                kwargs["calendar_id"] = arguments["calendar_id"]

            # Get reminders
            reminders = list(remind.get_reminders(**kwargs))

            # Apply limit if specified
            limit = arguments.get("limit")
            if limit and limit > 0:
                reminders = reminders[:limit]

            if not reminders:
                return [TextContent(type="text", text="No reminders found matching the specified filters.")]

            result = f"Found {len(reminders)} reminder(s):\n\n"
            for i, reminder in enumerate(reminders, 1):
                result += f"=== Reminder {i} ===\n"
                result += format_reminder(reminder)
                result += "\n" + "=" * 40 + "\n\n"

            return [TextContent(type="text", text=result)]

        elif name == "search_reminders":
            reminders = list(remind.search_reminders(arguments["query"]))

            # Apply limit if specified
            limit = arguments.get("limit")
            if limit and limit > 0:
                reminders = reminders[:limit]

            if not reminders:
                return [TextContent(type="text", text=f"No reminders found matching '{arguments['query']}'.")]

            result = f"Found {len(reminders)} reminder(s) matching '{arguments['query']}':\n\n"
            for i, reminder in enumerate(reminders, 1):
                result += f"=== Reminder {i} ===\n"
                result += format_reminder(reminder)
                result += "\n" + "=" * 40 + "\n\n"

            return [TextContent(type="text", text=result)]

        elif name == "get_next_reminder":
            reminder = remind.get_next_reminder()
            if not reminder:
                return [TextContent(type="text", text="No upcoming reminders found.")]

            result = "Next Upcoming Reminder:\n\n"
            result += format_reminder(reminder)
            return [TextContent(type="text", text=result)]

        elif name == "get_overdue_reminders":
            now = datetime.now()
            reminders = list(remind.get_reminders(
                due_before=now,
                is_completed=False
            ))

            # Apply limit if specified
            limit = arguments.get("limit")
            if limit and limit > 0:
                reminders = reminders[:limit]

            if not reminders:
                return [TextContent(type="text", text="No overdue reminders found. Great job!")]

            result = f"Found {len(reminders)} overdue reminder(s):\n\n"
            for i, reminder in enumerate(reminders, 1):
                result += f"=== Reminder {i} ===\n"
                result += format_reminder(reminder)
                result += "\n" + "=" * 40 + "\n\n"

            return [TextContent(type="text", text=result)]

        elif name == "get_today_reminders":
            now = datetime.now()
            start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end_of_day = now.replace(hour=23, minute=59, second=59, microsecond=999999)

            include_completed = arguments.get("include_completed", False)

            if include_completed:
                reminders = list(remind.get_reminders(
                    due_after=start_of_day,
                    due_before=end_of_day
                ))
            else:
                reminders = list(remind.get_reminders(
                    due_after=start_of_day,
                    due_before=end_of_day,
                    is_completed=False
                ))

            if not reminders:
                status = "any" if include_completed else "incomplete"
                return [TextContent(type="text", text=f"No {status} reminders due today.")]

            result = f"Found {len(reminders)} reminder(s) due today:\n\n"
            for i, reminder in enumerate(reminders, 1):
                result += f"=== Reminder {i} ===\n"
                result += format_reminder(reminder)
                result += "\n" + "=" * 40 + "\n\n"

            return [TextContent(type="text", text=result)]

        # Workflow Management Tools
        elif name == "get_workflow_lists":
            calendars = list(remind.calendars.search("Claude-"))
            if not calendars:
                return [TextContent(type="text", text="No workflow lists found (calendars starting with 'Claude-').")]

            result = f"Found {len(calendars)} workflow list(s):\n\n"
            for cal in calendars:
                result += f"Name: {cal.name}\n"
                result += f"ID: {cal.id}\n"
                result += f"Color: {cal.color}\n"
                result += f"Default: {'Yes' if cal.is_default else 'No'}\n"
                result += "-" * 40 + "\n"

            return [TextContent(type="text", text=result)]

        elif name == "move_reminder_to_list":
            reminder = remind.move_reminder(
                arguments["reminder_id"],
                arguments["calendar_id"]
            )

            # Get calendar name for confirmation
            calendar = remind.calendars.get_by_id(arguments["calendar_id"])

            result = f"Reminder moved successfully to '{calendar.name}'!\n\n"
            result += format_reminder(reminder)
            return [TextContent(type="text", text=result)]

        elif name == "move_reminder_on_deck":
            # Find the Claude-On-Deck calendar
            calendars = list(remind.calendars.search("Claude-On-Deck"))
            if not calendars:
                return [TextContent(
                    type="text",
                    text="Error: 'Claude-On-Deck' calendar not found. Please create it in Apple Reminders first."
                )]

            on_deck_calendar = calendars[0]
            reminder = remind.move_reminder(
                arguments["reminder_id"],
                on_deck_calendar.id
            )

            result = f"Reminder moved to 'Claude-On-Deck' (queued for work)!\n\n"
            result += format_reminder(reminder)
            return [TextContent(type="text", text=result)]

        elif name == "move_reminder_active":
            # Find the Claude-Active calendar
            calendars = list(remind.calendars.search("Claude-Active"))
            if not calendars:
                return [TextContent(
                    type="text",
                    text="Error: 'Claude-Active' calendar not found. Please create it in Apple Reminders first."
                )]

            active_calendar = calendars[0]
            reminder = remind.move_reminder(
                arguments["reminder_id"],
                active_calendar.id
            )

            result = f"Reminder moved to 'Claude-Active' (now in progress)!\n\n"
            result += format_reminder(reminder)
            return [TextContent(type="text", text=result)]

        elif name == "move_reminder_done":
            # Find the Claude-Done calendar
            calendars = list(remind.calendars.search("Claude-Done"))
            if not calendars:
                return [TextContent(
                    type="text",
                    text="Error: 'Claude-Done' calendar not found. Please create it in Apple Reminders first."
                )]

            done_calendar = calendars[0]
            reminder = remind.move_reminder(
                arguments["reminder_id"],
                done_calendar.id
            )

            result = f"Reminder moved to 'Claude-Done' (task completed)!\n\n"
            result += format_reminder(reminder)
            return [TextContent(type="text", text=result)]

        elif name == "move_reminder_blocked":
            # Find the Claude-Waiting calendar
            calendars = list(remind.calendars.search("Claude-Waiting"))
            if not calendars:
                return [TextContent(
                    type="text",
                    text="Error: 'Claude-Waiting' calendar not found. Please create it in Apple Reminders first."
                )]

            waiting_calendar = calendars[0]
            reminder = remind.move_reminder(
                arguments["reminder_id"],
                waiting_calendar.id
            )

            result = f"Reminder moved to 'Claude-Waiting' (task blocked/waiting)!\n\n"
            result += format_reminder(reminder)
            return [TextContent(type="text", text=result)]

        else:
            raise ValueError(f"Unknown tool: {name}")

    except ValueError as e:
        return [TextContent(type="text", text=f"Error: {str(e)}")]
    except Exception as e:
        return [TextContent(type="text", text=f"Error executing {name}: {str(e)}")]


async def main():
    """Main entry point for the MCP server.

    Starts the server and begins listening for requests via stdio.
    This function is called when the server is launched by an MCP client.
    """
    # Run the server using stdin/stdout streams
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )


if __name__ == "__main__":
    """Entry point when the module is run directly."""
    import asyncio
    asyncio.run(main())
