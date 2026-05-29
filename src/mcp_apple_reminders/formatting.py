"""Parsing helpers shared across MCP tool handlers.

Two small utilities:
- `parse_datetime` — parse ISO-format datetime strings from MCP arguments.
- `parse_priority` — accept either named priorities ("none"/"low"/"medium"/"high")
  or integer strings (0-9) and return the canonical EventKit integer.
"""

from __future__ import annotations

from datetime import datetime


def parse_datetime(date_string: str) -> datetime:
    """Parse an ISO-format datetime string.

    Raises `ValueError` with a hint about the expected format on failure.
    """
    try:
        return datetime.fromisoformat(date_string)
    except ValueError as err:
        raise ValueError(
            f"Invalid datetime format: {date_string}. Expected ISO format (e.g., '2024-01-15T14:30:00')"
        ) from err


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

    raise ValueError(f"Invalid priority: {priority_str}. Expected 'none', 'low', 'medium', 'high', or integer 0-9")
