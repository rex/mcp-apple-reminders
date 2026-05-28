"""Internal EventKit glue for pyremindkit.

These helpers bridge between EventKit's Objective-C surface (via PyObjC) and the
pure-Python `Reminder` value type. They are not part of the public API; consumers
should go through `RemindKit`, `Calendar`, or `CalendarManager`.

Side effects:
- `_grant_permission` triggers a macOS Reminders permission request and may
  surface a system permission dialog. It blocks up to 60s waiting for the user's
  response.
- `_save_ek_reminder` commits a transaction against the system EventKit store
  and may raise `RuntimeError` on save failure.
"""

from __future__ import annotations

from datetime import datetime
from threading import Event

import objc
from EventKit import EKEventStore
from Foundation import NSURL

from .models import Reminder


def _grant_permission() -> EKEventStore:
    """Request full Reminders access and return an authenticated `EKEventStore`.

    Uses the `requestFullAccessToRemindersWithCompletion_` API (macOS Sequoia+).
    Blocks up to 60s for the user's response to the system permission dialog.

    Raises:
        PermissionError: If the user denies access or the request times out.
    """
    event_store = EKEventStore.alloc().init()
    done = Event()
    result = {}

    def completion_handler(granted: bool, error: objc.objc_object) -> None:
        result["granted"] = granted
        result["error"] = error
        done.set()

    event_store.requestFullAccessToRemindersWithCompletion_(completion_handler)
    done.wait(timeout=60)
    if not result.get("granted"):
        raise PermissionError("No access to reminders")

    return event_store


def _convert_ek_reminder_to_reminder(ek_reminder) -> Reminder:
    """Convert a raw `EKReminder` into the pure-Python `Reminder` value type.

    Extracts every field the `Reminder` NamedTuple exposes: id, title, due date,
    notes, completed flag, URL, priority, list ID, creation/modification dates,
    flagged flag. Missing optional fields come back as None / defaults.

    The `due_date` is reconstructed from `dueDateComponents` via the NSDateComponents
    `.date()` method — EventKit stores due dates as components, not absolute dates.
    """
    due_date = None
    if ek_reminder.dueDateComponents():
        ns_date = ek_reminder.dueDateComponents().date()
        if ns_date:
            due_date = datetime.fromtimestamp(ns_date.timeIntervalSince1970())

    created_date = None
    if ek_reminder.creationDate():
        created_date = datetime.fromtimestamp(ek_reminder.creationDate().timeIntervalSince1970())

    modified_date = None
    if ek_reminder.lastModifiedDate():
        modified_date = datetime.fromtimestamp(ek_reminder.lastModifiedDate().timeIntervalSince1970())

    raw_priority = ek_reminder.priority() if hasattr(ek_reminder, "priority") else 0

    return Reminder(
        id=ek_reminder.calendarItemIdentifier(),
        title=ek_reminder.title(),
        due_date=due_date,
        notes=ek_reminder.notes(),
        completed=ek_reminder.isCompleted(),
        url=str(ek_reminder.URL()) if ek_reminder.URL() else None,
        priority=raw_priority,
        list_id=ek_reminder.calendar().calendarIdentifier(),
        created_date=created_date,
        modified_date=modified_date,
        flagged=ek_reminder.flagged() if hasattr(ek_reminder, "flagged") else False,
    )


def _save_ek_reminder(event_store: EKEventStore, ek_reminder) -> bool:
    """Commit a modified `EKReminder` back to the system store.

    Args:
        event_store: The active `EKEventStore` (from `_grant_permission`).
        ek_reminder: The `EKReminder` to save (new or modified).

    Returns:
        True on success.

    Raises:
        RuntimeError: If EventKit refuses the save. NOTE: EventKit reports the
            actual error through an out-parameter that PyObjC does not currently
            populate from None; the captured `error` is consistently None, so
            the raised message ends with `: None`. Fixing this requires
            allocating an actual `objc.nil` reference. Tracked as a known issue.
    """
    error = None
    success = event_store.saveReminder_commit_error_(ek_reminder, True, error)

    if not success:
        raise RuntimeError(f"Failed to update reminder: {error}")

    return success


__all__ = [
    "_grant_permission",
    "_convert_ek_reminder_to_reminder",
    "_save_ek_reminder",
    "NSURL",  # re-exported for callers that need to build NSURL instances
]
