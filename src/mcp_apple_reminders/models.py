"""Public Pydantic models for the MCP Apple Reminders server.

Defines the canonical Calendar and Reminder schemas surfaced through every
MCP tool that returns structured output. Pydantic v2, immutable, with a
mandatory `deeplink` field on every Reminder + Calendar response.

### CONTRACT FREEZE (Slice 0.3, 2026-05-28)

The field order on `Calendar` and `Reminder` below is the canonical contract
for the rest of spec 002. Additions after this slice require an ADR. The
acceptance criterion in `specs/002-modernize-and-foundation/tasks.md::S0.3`
locks this in.

### Deeplinks

Both models surface a `deeplink` field of the form

  - `x-apple-reminderkit://REMCDReminder/{id}` for reminders
  - `x-apple-reminderkit://REMCDList/{id}` for calendars

These are intercepted by Reminders.app and open the matching entity in the
native UI. Verified runnable via `subprocess.run(["open", deeplink])`.

### EventKit vs SQLite identifier equivalence

The contract assumes `EKReminder.calendarItemIdentifier()` and the SQLite
`ZIDENTIFIER` column produce the same UUID string for the same reminder, so
deeplinks generated from either source resolve to the same entity. The
EventKit half is exercised by `eventkit_reminder_to_pydantic` below; the
SQLite half is verified at Slice 1.0 when the direct reader lands.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from pydantic import BaseModel, ConfigDict, Field, field_serializer

if TYPE_CHECKING:
    # Type-only imports — avoid pulling EventKit at import time so the models
    # module stays importable from non-EventKit consumers (tests, docs gen).
    from typing import Any

    EKReminder = Any
    EKCalendar = Any


# ---------------------------------------------------------------------------
# Deeplink helpers
# ---------------------------------------------------------------------------

REMINDER_DEEPLINK_SCHEME = "x-apple-reminderkit://REMCDReminder/"
CALENDAR_DEEPLINK_SCHEME = "x-apple-reminderkit://REMCDList/"


def reminder_deeplink(uuid: str) -> str:
    """Build the Reminders.app deeplink for an individual reminder."""
    return f"{REMINDER_DEEPLINK_SCHEME}{uuid}"


def calendar_deeplink(uuid: str) -> str:
    """Build the Reminders.app deeplink for a reminder list (calendar)."""
    return f"{CALENDAR_DEEPLINK_SCHEME}{uuid}"


# ---------------------------------------------------------------------------
# Calendar (6 fields, frozen post-S0.3)
# ---------------------------------------------------------------------------


class Calendar(BaseModel):
    """A Reminders.app list (an EKCalendar of entity type reminder).

    Field order is the contract freeze point of Slice 0.3. Do NOT reorder
    without an ADR.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str = Field(description="EKCalendar.calendarIdentifier() / SQLite ZIDENTIFIER.")
    name: str = Field(description="Display name (EKCalendar.title()).")
    color: str = Field(description="Hex color string (e.g. '#FF9500') or a named palette token.")
    is_default: bool = Field(
        description="True iff this calendar equals EKEventStore.defaultCalendarForNewReminders().",
    )
    owner: Optional[str] = Field(
        default=None,
        description="Account owner (e.g. iCloud account email). EventKit does not always expose this; may be None.",
    )
    deeplink: str = Field(description="x-apple-reminderkit://REMCDList/{id} — opens the list in Reminders.app.")
    # ----- post-S0.3 tail-append additions (ADR 0001, S5.1) -----
    is_group: bool = Field(
        default=False,
        description=(
            "True iff this Calendar row is a Reminders.app group (folder), "
            "not a regular list. Surfaces from SQLite `ZISGROUP=1`."
        ),
    )
    parent_group_id: Optional[str] = Field(
        default=None,
        description=(
            "If this list is a child of a group, the group's `ZCKIDENTIFIER`. "
            "None for top-level lists and for groups themselves."
        ),
    )


# ---------------------------------------------------------------------------
# Reminder (18 fields, frozen post-S0.3)
# ---------------------------------------------------------------------------


class Reminder(BaseModel):
    """A single Reminders.app reminder.

    Field order is the contract freeze point of Slice 0.3. Do NOT reorder
    without an ADR. Additions go at the tail with a default value so existing
    callers still construct correctly.

    `subtasks` holds child reminder IDs (not full nested objects) — clients
    that want hydrated subtasks should issue a follow-up `get_subtasks(id)`
    call. This keeps the payload bounded.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str = Field(description="EKReminder.calendarItemIdentifier() / SQLite ZIDENTIFIER.")
    title: str = Field(description="Reminder title.")
    due_date: Optional[datetime] = Field(default=None, description="Due date (naive local time).")
    notes: Optional[str] = Field(default=None, description="Free-form notes body.")
    completed: bool = Field(default=False, description="True if marked complete.")
    url: Optional[str] = Field(default=None, description="Attached URL (EKReminder.URL).")
    priority: int = Field(
        default=0,
        ge=0,
        le=9,
        description="EventKit raw priority 0–9: 0=none, 1–4=low, 5=medium, 6–9=high.",
    )
    list_id: str = Field(description="Parent calendar's EKCalendar.calendarIdentifier().")
    created_date: Optional[datetime] = Field(default=None, description="EKReminder.creationDate().")
    modified_date: Optional[datetime] = Field(default=None, description="EKReminder.lastModifiedDate().")
    flagged: bool = Field(default=False, description="EKReminder.flagged (ReminderKit-required to set).")
    parent_reminder_id: Optional[str] = Field(
        default=None,
        description="Parent reminder ID for subtasks (ReminderKit-only; None for top-level).",
    )
    subtasks: list[str] = Field(
        default_factory=list,
        description="Child reminder IDs. Hydrate with get_subtasks(id).",
    )
    tags: list[str] = Field(
        default_factory=list,
        description="Reminder tags (ReminderKit-only; empty list if none).",
    )
    section_name: Optional[str] = Field(
        default=None,
        description="Section the reminder belongs to within its list (ReminderKit/SQLite-only).",
    )
    completion_date: Optional[datetime] = Field(
        default=None,
        description="EKReminder.completionDate() — when the reminder was marked done.",
    )
    start_date: Optional[datetime] = Field(
        default=None,
        description="Optional start date (EKReminder.startDateComponents).",
    )
    deeplink: str = Field(
        description="x-apple-reminderkit://REMCDReminder/{id} — opens the reminder in Reminders.app.",
    )

    @field_serializer(
        "due_date",
        "created_date",
        "modified_date",
        "completion_date",
        "start_date",
        when_used="json",
    )
    def _serialize_local_datetime(self, value: Optional[datetime]) -> Optional[str]:
        """Emit RFC 3339 (offset-bearing) datetimes for MCP structured-output validation.

        The model stores naive *local* datetimes, which serialize to an offset-less
        ISO string (e.g. ``2026-06-19T04:00:00``) that fails the JSON-Schema
        ``date-time`` (RFC 3339) format check FastMCP enforces on structured output
        over the wire — every Reminder-returning tool would otherwise error. Stamp
        the local UTC offset on the way out; the stored value stays naive-local and
        the field order is unchanged (S0.3 freeze safe).
        """
        if value is None:
            return None
        if value.tzinfo is None:
            value = value.astimezone()
        return value.isoformat()


# ---------------------------------------------------------------------------
# Converters (EventKit → Pydantic)
# ---------------------------------------------------------------------------


def eventkit_reminder_to_pydantic(ek_reminder: "EKReminder") -> Reminder:
    """Convert an `EKReminder` (PyObjC handle) into the public `Reminder` model.

    Populates the EventKit-derivable subset of fields. Fields only available
    via ReminderKit (`parent_reminder_id`, `subtasks`, `tags`, `section_name`)
    are returned as their defaults; callers wanting those should round-trip
    through the SQLite read path (Slice 1.0) or the ReminderKit helper (S1.4+).

    The `deeplink` is derived from `calendarItemIdentifier()`, which the
    contract assumes is identical to the SQLite `ZIDENTIFIER` for the same
    reminder. The same UUID feeds both deeplink paths.
    """
    reminder_id = str(ek_reminder.calendarItemIdentifier())

    def _ts_to_dt(ns_date) -> Optional[datetime]:
        if ns_date is None:
            return None
        return datetime.fromtimestamp(ns_date.timeIntervalSince1970())

    due_date: Optional[datetime] = None
    if ek_reminder.dueDateComponents():
        due_date = _ts_to_dt(ek_reminder.dueDateComponents().date())

    start_date: Optional[datetime] = None
    if hasattr(ek_reminder, "startDateComponents") and ek_reminder.startDateComponents():
        start_date = _ts_to_dt(ek_reminder.startDateComponents().date())

    raw_priority = ek_reminder.priority() if hasattr(ek_reminder, "priority") else 0
    raw_url = str(ek_reminder.URL()) if ek_reminder.URL() else None

    return Reminder(
        id=reminder_id,
        title=ek_reminder.title() or "",
        due_date=due_date,
        notes=ek_reminder.notes(),
        completed=ek_reminder.isCompleted(),
        url=raw_url,
        priority=raw_priority,
        list_id=str(ek_reminder.calendar().calendarIdentifier()),
        created_date=_ts_to_dt(ek_reminder.creationDate()) if ek_reminder.creationDate() else None,
        modified_date=_ts_to_dt(ek_reminder.lastModifiedDate()) if ek_reminder.lastModifiedDate() else None,
        flagged=ek_reminder.flagged() if hasattr(ek_reminder, "flagged") else False,
        completion_date=_ts_to_dt(ek_reminder.completionDate()) if ek_reminder.completionDate() else None,
        start_date=start_date,
        deeplink=reminder_deeplink(reminder_id),
    )


def eventkit_calendar_to_pydantic(
    ek_calendar: "EKCalendar",
    *,
    is_default: bool,
    owner: Optional[str] = None,
) -> Calendar:
    """Convert an `EKCalendar` (PyObjC handle) into the public `Calendar` model.

    `is_default` is passed in by the caller because EventKit identifies the
    default via the *store*, not via a property on the calendar object.
    """
    calendar_id = str(ek_calendar.calendarIdentifier())
    return Calendar(
        id=calendar_id,
        name=ek_calendar.title() or "",
        color=str(ek_calendar.color()) if ek_calendar.color() else "",
        is_default=is_default,
        owner=owner,
        deeplink=calendar_deeplink(calendar_id),
    )


# ---------------------------------------------------------------------------
# Native (NamedTuple/dataclass) → Pydantic converters
# ---------------------------------------------------------------------------
# `_native.Calendar` is a dataclass and `_native.Reminder` is a NamedTuple.
# These transitional converters let FastMCP tools wrap the existing
# data-access surface without changing the underlying _native types. They go
# away in S1.0+ once SQLite reads return Pydantic models directly.


def native_calendar_to_pydantic(native_cal) -> Calendar:
    """Convert a `_native.Calendar` (dataclass) into the public `Calendar` model."""
    cal_id = str(native_cal.id)
    owner = native_cal.owner if native_cal.owner not in (None, "Unknown") else None
    return Calendar(
        id=cal_id,
        name=native_cal.name,
        color=native_cal.color,
        is_default=native_cal.is_default,
        owner=owner,
        deeplink=calendar_deeplink(cal_id),
    )


def native_reminder_to_pydantic(native_r) -> Reminder:
    """Convert a `_native.Reminder` (NamedTuple) into the public `Reminder` model.

    ReminderKit-only fields (parent_reminder_id, subtasks, tags, section_name)
    default to None / [] because `_native` only surfaces the EventKit subset.
    Slice 1.0 hydrates them from the SQLite read path.
    """
    reminder_id = str(native_r.id)
    return Reminder(
        id=reminder_id,
        title=native_r.title,
        due_date=native_r.due_date,
        notes=native_r.notes,
        completed=native_r.completed,
        url=native_r.url,
        priority=native_r.priority,
        list_id=native_r.list_id,
        created_date=native_r.created_date,
        modified_date=native_r.modified_date,
        flagged=native_r.flagged,
        deeplink=reminder_deeplink(reminder_id),
    )


__all__ = [
    "CALENDAR_DEEPLINK_SCHEME",
    "Calendar",
    "REMINDER_DEEPLINK_SCHEME",
    "Reminder",
    "calendar_deeplink",
    "eventkit_calendar_to_pydantic",
    "eventkit_reminder_to_pydantic",
    "native_calendar_to_pydantic",
    "native_reminder_to_pydantic",
    "reminder_deeplink",
]
