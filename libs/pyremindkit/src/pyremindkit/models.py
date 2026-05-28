"""Data models for pyremindkit.

Lightweight value types used across the pyremindkit surface. Kept dependency-free
(no EventKit imports) so they can be safely shared between the public API
(`RemindKit`, `Calendar`, `CalendarManager`) and consumers without dragging in the
Objective-C bridge.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import NamedTuple, Optional


class Priority(Enum):
    """Named priority levels mapped to the integer ranges EventKit uses internally.

    EventKit stores reminder priority as an integer 0-9 where:
    - 0 = none
    - 1-4 = low (we canonicalize to 1)
    - 5 = medium
    - 6-9 = high (we canonicalize to 9)

    The enum values here are NOT the EventKit integers — they are stable ordinal
    tags. Conversion to the EventKit integer happens at the EventKit-bridge layer.
    """

    NONE = 0
    LOW = 1
    MEDIUM = 2
    HIGH = 3


class Reminder(NamedTuple):
    """Immutable snapshot of an EventKit reminder.

    All datetime fields are Python `datetime` (naive, local time as returned by
    `datetime.fromtimestamp`). Conversion to/from `NSDate` happens in `_internal`.

    The `priority` field is the raw EventKit integer (0-9), NOT a `Priority` enum
    value. Callers that want a named bucket should compare against the integer
    ranges documented on `Priority`.
    """

    id: str
    title: str
    due_date: Optional[datetime]
    notes: Optional[str]
    completed: bool
    url: Optional[str]
    priority: int
    list_id: str
    created_date: Optional[datetime]
    modified_date: Optional[datetime]
    flagged: bool
