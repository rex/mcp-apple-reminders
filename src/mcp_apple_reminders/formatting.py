"""Formatting helpers shared across MCP tool handlers.

Three small utilities:
- `format_reminder` — render a `Reminder` as the canonical human-readable text block
  returned from `get_reminder`, `create_reminder`, etc.
- `parse_datetime` — parse ISO-format datetime strings from MCP arguments.
- `parse_priority` — accept either named priorities ("none"/"low"/"medium"/"high")
  or integer strings (0-9) and return the canonical EventKit integer.
"""

from __future__ import annotations

from datetime import datetime

from pyremindkit import Reminder


def format_reminder(reminder: Reminder) -> str:
    """Render a `Reminder` as a multi-line human-readable block.

    The output is consumed by the MCP client as plain text. Fields are emitted
    one-per-line in a stable order so downstream parsers (or humans) can rely on
    the layout.
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
    """Parse an ISO-format datetime string.

    Raises `ValueError` with a hint about the expected format on failure.
    """
    try:
        return datetime.fromisoformat(date_string)
    except ValueError:
        raise ValueError(
            f"Invalid datetime format: {date_string}. Expected ISO format (e.g., '2024-01-15T14:30:00')"
        )


def parse_priority(priority_str: str) -> int:
    """Parse a priority string into the EventKit integer (0-9).

    Accepts either:
    - Named priorities: "none"=0, "low"=1, "medium"=5, "high"=9
    - Integer strings: "0" through "9"

    Raises `ValueError` for anything else.
    """
    priority_lower = priority_str.lower().strip()

    try:
        val = int(priority_lower)
        if 0 <= val <= 9:
            return val
    except ValueError:
        pass

    priority_map = {"none": 0, "low": 1, "medium": 5, "high": 9}

    if priority_lower in priority_map:
        return priority_map[priority_lower]

    raise ValueError(
        f"Invalid priority: {priority_str}. Expected 'none', 'low', 'medium', 'high', or integer 0-9"
    )
