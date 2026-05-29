"""RemindKit — top-level orchestrator over EventKit.

This module hosts ONLY the `RemindKit` class — the public entry point. Calendar
and Reminder primitives live in `calendars` and `models`; EventKit/Foundation
glue lives in `_internal`.

Side effects on instantiation:
- Requests Reminders access from the user via `_grant_permission`. May trigger
  a macOS permission dialog. Raises `PermissionError` if the user denies.
"""

from __future__ import annotations

from datetime import datetime
from typing import Callable, Generator, Optional, cast

from Foundation import (
    NSURL,
    NSCalendar,
    NSCalendarUnitDay,
    NSCalendarUnitHour,
    NSCalendarUnitMinute,
    NSCalendarUnitMonth,
    NSCalendarUnitSecond,
    NSCalendarUnitYear,
    NSDate,
)

from ._internal import (
    _convert_ek_reminder_to_reminder,
    _grant_permission,
    _save_ek_reminder,
)
from .calendars import CalendarManager
from .models import Priority, Reminder


class RemindKit:
    """High-level Reminders client.

    On construction, requests Reminders permission and opens an `EKEventStore`.
    All reminder/calendar operations route through this instance.

    Note: `on_reminder_created` and `on_reminder_completed` register callbacks
    into internal lists that are NEVER FIRED (dead code preserved from the
    original implementation, tracked as a known issue).
    """

    def __init__(self):
        self._event_store = _grant_permission()
        self.calendars = CalendarManager(self, self._event_store)
        self._is_authenticated = False
        self._on_reminder_created_callbacks = []
        self._on_reminder_completed_callbacks = []

    def create_reminder(self, **kwargs) -> Reminder:
        """Create a reminder. Defaults to the system default calendar.

        Accepts `calendar_id` or `list_id` to target a specific calendar.
        Forwards remaining kwargs to `Calendar.create_reminder`.
        """
        calendar_id = kwargs.pop("calendar_id", None) or kwargs.pop("list_id", None)
        calendar = self.calendars.get_by_id(calendar_id) if calendar_id else self.calendars.get_default()

        reminder = calendar.create_reminder(**kwargs)

        for callback in self._on_reminder_created_callbacks:
            callback(reminder)

        return reminder

    def update_reminder(self, reminder_id: str, **kwargs) -> Reminder:
        """Update fields on an existing reminder.

        Only the fields supplied as kwargs are mutated. Supported fields:
        title, due_date, notes, priority, is_completed, url.
        Pass url="" or url=None to clear the URL.
        """
        ek_reminder = self._event_store.calendarItemWithIdentifier_(reminder_id)
        if not ek_reminder:
            raise ValueError(f"Reminder with ID '{reminder_id}' not found.")

        if "title" in kwargs:
            ek_reminder.setTitle_(kwargs["title"])

        if "due_date" in kwargs and kwargs["due_date"]:
            components = NSCalendar.currentCalendar().components_fromDate_(
                NSCalendarUnitYear
                | NSCalendarUnitMonth
                | NSCalendarUnitDay
                | NSCalendarUnitHour
                | NSCalendarUnitMinute
                | NSCalendarUnitSecond,
                NSDate.dateWithTimeIntervalSince1970_(kwargs["due_date"].timestamp()),
            )
            ek_reminder.setDueDateComponents_(components)

        if "notes" in kwargs:
            ek_reminder.setNotes_(kwargs["notes"])

        if "priority" in kwargs:
            priority_val = kwargs["priority"]
            if isinstance(priority_val, int):
                ek_reminder.setPriority_(priority_val)
            else:
                if priority_val == Priority.NONE:
                    ek_reminder.setPriority_(0)
                elif priority_val == Priority.LOW:
                    ek_reminder.setPriority_(1)
                elif priority_val == Priority.MEDIUM:
                    ek_reminder.setPriority_(5)
                elif priority_val == Priority.HIGH:
                    ek_reminder.setPriority_(9)

        if "is_completed" in kwargs:
            ek_reminder.setCompleted_(kwargs["is_completed"])

        if "url" in kwargs:
            url_value = kwargs["url"]
            if url_value:
                if isinstance(url_value, str):
                    ns_url = NSURL.URLWithString_(url_value)
                    if ns_url:
                        ek_reminder.setURL_(ns_url)
                else:
                    ek_reminder.setURL_(url_value)
            else:
                ek_reminder.setURL_(None)

        _save_ek_reminder(self._event_store, ek_reminder)

        return _convert_ek_reminder_to_reminder(ek_reminder)

    def move_reminder(self, reminder_id: str, target_calendar_id: str) -> Reminder:
        """Move a reminder to a different calendar by changing its `calendar` field."""
        ek_reminder = self._event_store.calendarItemWithIdentifier_(reminder_id)
        if not ek_reminder:
            raise ValueError(f"Reminder with ID '{reminder_id}' not found.")

        target_calendar = self._event_store.calendarWithIdentifier_(target_calendar_id)
        if not target_calendar:
            raise ValueError(f"Calendar with ID '{target_calendar_id}' not found.")

        ek_reminder.setCalendar_(target_calendar)
        _save_ek_reminder(self._event_store, ek_reminder)

        return _convert_ek_reminder_to_reminder(ek_reminder)

    def get_reminder_by_id(self, id: str) -> Reminder:
        """Fetch a single reminder by identifier; raises if not found."""
        ek_reminder = self._event_store.calendarItemWithIdentifier_(id)
        if ek_reminder:
            return _convert_ek_reminder_to_reminder(ek_reminder)
        raise ValueError(f"Reminder with ID '{id}' not found.")

    def get_next_reminder(self) -> Optional[Reminder]:
        """Return the soonest incomplete reminder with a due date, or None."""
        current_time = datetime.now()
        all_reminders = list(self.get_reminders(is_completed=False, due_after=current_time))
        # `r.due_date is not None` lets mypy narrow the Optional in the sort key.
        upcoming_reminders = [r for r in all_reminders if r.due_date is not None]
        upcoming_reminders.sort(key=lambda x: cast(datetime, x.due_date))
        return upcoming_reminders[0] if upcoming_reminders else None

    def get_reminders(
        self,
        due_after: Optional[datetime] = None,
        due_before: Optional[datetime] = None,
        is_completed: Optional[bool] = None,
        priority: Optional[Priority] = None,
        calendar_id: Optional[str] = None,
    ) -> Generator[Reminder, None, None]:
        """Stream reminders matching the supplied filters.

        If `calendar_id` is provided, restricts to that calendar; otherwise
        iterates across every reminder calendar in turn.
        """
        if calendar_id:
            calendar = self.calendars.get_by_id(calendar_id)
            yield from calendar.get_reminders(due_after, due_before, is_completed, priority)
        else:
            for calendar in self.calendars.list():
                yield from calendar.get_reminders(due_after, due_before, is_completed, priority)

    def search_reminders(self, query: str) -> Generator[Reminder, None, None]:
        """Case-insensitive substring search across every reminder's title and notes.

        Performance note: this fetches every reminder from every calendar via
        the predicate API, then filters in Python. O(N) across all reminders.
        """
        for calendar in self.calendars.list():
            for reminder in calendar.get_reminders():
                if (
                    query.lower() in reminder.title.lower()
                    or reminder.notes
                    and query.lower() in reminder.notes.lower()
                ):
                    yield reminder

    def delete_reminder(self, reminder_id: str) -> bool:
        """Permanently delete a reminder. Raises on lookup miss or save failure."""
        ek_reminder = self._event_store.calendarItemWithIdentifier_(reminder_id)
        if not ek_reminder:
            raise ValueError(f"Reminder with ID '{reminder_id}' not found.")

        error = None
        success = self._event_store.removeReminder_commit_error_(ek_reminder, True, error)

        if not success:
            raise RuntimeError(f"Failed to delete reminder: {error}")

        return success

    def on_reminder_created(self, callback: Callable) -> None:
        """Register a callback that WOULD be invoked when a reminder is created.

        NOTE: this callback list is dead code — `create_reminder` iterates it, but
        no upstream EventKit observer is wired up to trigger it for external
        changes. Tracked as a known issue.
        """
        self._on_reminder_created_callbacks.append(callback)

    def on_reminder_completed(self, callback: Callable) -> None:
        """Register a callback for reminder-completion events.

        NOTE: never fired anywhere in the codebase. Dead code preserved for API
        compatibility; tracked as a known issue.
        """
        self._on_reminder_completed_callbacks.append(callback)
