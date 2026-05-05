"""Pure helpers shared across the MCP server: datetime / priority parsing.

These functions are intentionally side-effect-free and have no pyremindkit
dependency, so they're trivially unit-testable on any platform.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from dateutil import parser as _dateutil_parser

# Apple Reminders priorities are integers 0-9 (RFC 5545 / iCalendar). Apple's
# UI exposes only four levels; we map names to the canonical integer for each.
_NAMED_PRIORITIES: dict[str, int] = {
    "none": 0,
    "low": 1,
    "medium": 5,
    "high": 9,
}


def parse_datetime(value: str | datetime) -> datetime:
    """Parse an RFC 3339 / ISO 8601 datetime string.

    Accepts the trailing-``Z`` UTC form (``2024-01-15T14:30:00Z``), naive
    datetimes, and offsets. Returns a timezone-aware ``datetime`` whenever
    the input carries timezone info.

    Raises ``ValueError`` on unparseable input.
    """
    if isinstance(value, datetime):
        return value
    try:
        # python-dateutil handles every reasonable ISO/RFC variant including
        # ``Z`` and ``+0000`` (which datetime.fromisoformat rejects on Py<3.11).
        return _dateutil_parser.isoparse(value)
    except (ValueError, TypeError) as exc:
        raise ValueError(f"Invalid datetime: {value!r}. Expected ISO 8601 (e.g. '2024-01-15T14:30:00Z').") from exc


def parse_priority(value: str | int) -> int:
    """Parse a priority name or integer into the canonical 0/1/5/9 form.

    Accepts:
    - integers 0-9
    - integer-as-string ("0", "1", …, "9")
    - names "none", "low", "medium", "high" (case-insensitive)

    Returns 0 (none), 1 (low), 5 (medium), or 9 (high) — matching Apple's
    four-level UI. Other integers in 0-9 are passed through unchanged
    (Apple Reminders accepts the full range, even if it doesn't show it).
    """
    if isinstance(value, int):
        return _normalize_priority_int(value)
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in _NAMED_PRIORITIES:
            return _NAMED_PRIORITIES[normalized]
        try:
            return _normalize_priority_int(int(normalized))
        except ValueError:
            pass
    raise ValueError(f"Invalid priority: {value!r}. Expected 'none', 'low', 'medium', 'high', or integer 0-9.")


def _normalize_priority_int(value: int) -> int:
    if 0 <= value <= 9:
        return value
    raise ValueError(f"Priority integer must be 0-9, got {value}.")


def priority_label(value: int) -> str:
    """Human-readable label for a priority integer."""
    if value == 0:
        return "None"
    if 1 <= value <= 4:
        return "Low"
    if value == 5:
        return "Medium"
    if 6 <= value <= 9:
        return "High"
    return f"Custom({value})"


def today_window(now: datetime | None = None) -> tuple[datetime, datetime]:
    """Return the (inclusive_start, exclusive_end) datetime pair for "today".

    The end is the next day at 00:00:00, so callers can pass it as an
    exclusive upper bound without microsecond hackery.
    """
    now = now or datetime.now()
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=1)
    return start, end


def to_utc(value: datetime) -> datetime:
    """Coerce a datetime to UTC, treating naive values as already-UTC."""
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)
