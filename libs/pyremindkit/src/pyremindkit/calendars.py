"""Calendar (reminder-list) primitives.

Defines:
- `Calendar` — the public dataclass that mirrors an `EKCalendar`. Holds an
  internal `_event_store` reference so methods on the instance (`get_reminders`,
  `create_reminder`) can talk to EventKit directly.
- `CalendarManager` — accessor surface bolted onto `RemindKit` as `.calendars`.
  Exposes `list`, `get` (by name), `get_by_id`, `search`, `get_default`.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from threading import Event
from typing import Generator, Optional

from EventKit import EKEntityTypeReminder, EKEventStore, EKReminder
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

from ._internal import _convert_ek_reminder_to_reminder, _save_ek_reminder
from .models import Priority, Reminder


@dataclass
class Calendar:
    """Pure-Python view of an `EKCalendar`.

    Carries a reference to the owning `EKEventStore` so reminder operations
    against the calendar can be performed without re-resolving identifiers.
    """

    id: str
    name: str
    owner: str  # Placeholder — EventKit does not expose calendar owner directly.
    color: str
    is_default: bool = False
    _event_store: EKEventStore = None

    def get_reminders(
        self,
        due_after: Optional[datetime] = None,
        due_before: Optional[datetime] = None,
        is_completed: Optional[bool] = None,
        priority: Optional[Priority] = None,
    ) -> Generator[Reminder, None, None]:
        """Stream reminders from this calendar that match the supplied filters.

        Date semantics use EventKit predicates:
        - `is_completed=None` → all reminders in the calendar.
        - `is_completed=True` → completed reminders whose `completionDate` falls
          in the range. Uses `predicateForCompletedRemindersWithCompletionDateStarting:ending:calendars:`.
        - `is_completed=False` → incomplete reminders whose `dueDate` falls in
          the range. Uses `predicateForIncompleteRemindersWithDueDateStarting:ending:calendars:`.

        Priority filtering is applied client-side after fetch, because EventKit
        predicates do not natively filter on priority bucket.
        """
        due_start_date = NSDate.dateWithTimeIntervalSince1970_(due_after.timestamp()) if due_after else None
        due_end_date = NSDate.dateWithTimeIntervalSince1970_(due_before.timestamp()) if due_before else None

        ek_calendar = self._event_store.calendarWithIdentifier_(self.id)

        if is_completed is None:
            predicate = self._event_store.predicateForRemindersInCalendars_([ek_calendar])
        elif is_completed:
            predicate = self._event_store.predicateForCompletedRemindersWithCompletionDateStarting_ending_calendars_(
                due_start_date,
                due_end_date,
                [ek_calendar],
            )
        else:
            predicate = self._event_store.predicateForIncompleteRemindersWithDueDateStarting_ending_calendars_(
                due_start_date,
                due_end_date,
                [ek_calendar],
            )

        fetch_done = Event()
        found_reminders = []

        def completion_handler(reminders, error=None):
            nonlocal found_reminders
            if reminders:
                found_reminders = reminders
            fetch_done.set()

        self._event_store.fetchRemindersMatchingPredicate_completion_(predicate, completion_handler)
        fetch_done.wait(timeout=60)

        for ek_reminder in found_reminders:
            # EventKit priority buckets: 0=none, 1-4=low, 5=medium, 6-9=high.
            if priority == Priority.LOW and not (1 <= ek_reminder.priority() <= 4):
                continue
            if priority == Priority.MEDIUM and ek_reminder.priority() != 5:
                continue
            if priority == Priority.HIGH and not (6 <= ek_reminder.priority() <= 9):
                continue

            yield _convert_ek_reminder_to_reminder(ek_reminder)

    def create_reminder(self, **kwargs) -> Reminder:
        """Create a new reminder in this calendar (or in a different one via list_id)."""
        if "list_id" in kwargs:
            target_calendar_id = kwargs.pop("list_id")
            ek_calendar = self._event_store.calendarWithIdentifier_(target_calendar_id)
            if not ek_calendar:
                ek_calendar = self._event_store.calendarWithIdentifier_(self.id)
        else:
            ek_calendar = self._event_store.calendarWithIdentifier_(self.id)

        new_reminder = EKReminder.reminderWithEventStore_(self._event_store)
        new_reminder.setCalendar_(ek_calendar)
        new_reminder.setTitle_(kwargs.get("title", ""))

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
            new_reminder.setDueDateComponents_(components)

        if "notes" in kwargs:
            new_reminder.setNotes_(kwargs["notes"])

        if "priority" in kwargs:
            priority_val = kwargs["priority"]
            if isinstance(priority_val, int):
                new_reminder.setPriority_(priority_val)
            else:
                if priority_val == Priority.NONE:
                    new_reminder.setPriority_(0)
                elif priority_val == Priority.LOW:
                    new_reminder.setPriority_(1)
                elif priority_val == Priority.MEDIUM:
                    new_reminder.setPriority_(5)
                elif priority_val == Priority.HIGH:
                    new_reminder.setPriority_(9)

        if "is_completed" in kwargs:
            new_reminder.setCompleted_(kwargs["is_completed"])

        if "url" in kwargs and kwargs["url"]:
            url_string = kwargs["url"]
            if isinstance(url_string, str):
                ns_url = NSURL.URLWithString_(url_string)
                if ns_url:
                    new_reminder.setURL_(ns_url)
            else:
                new_reminder.setURL_(url_string)

        _save_ek_reminder(self._event_store, new_reminder)

        return _convert_ek_reminder_to_reminder(new_reminder)


class CalendarManager:
    """Accessor surface for the set of reminder calendars exposed by EventKit."""

    def __init__(self, client, event_store: EKEventStore):
        self._client = client
        self._event_store = event_store

    def list(self) -> Generator[Calendar, None, None]:
        """Yield every reminder-type calendar accessible to the user.

        `is_default` is `True` for exactly the calendar returned by
        `EKEventStore.defaultCalendarForNewReminders()` — determined by
        comparing `calendarIdentifier()` values.
        """
        default_cal = self._event_store.defaultCalendarForNewReminders()
        default_id = default_cal.calendarIdentifier() if default_cal else None
        calendars = self._event_store.calendarsForEntityType_(EKEntityTypeReminder)
        for calendar in calendars:
            yield Calendar(
                id=calendar.calendarIdentifier(),
                name=calendar.title(),
                owner="Unknown",
                color=str(calendar.color()),
                is_default=(calendar.calendarIdentifier() == default_id),
                _event_store=self._event_store,
            )

    def get(self, name: str) -> Calendar:
        """Look up a calendar by exact name match."""
        for calendar in self.list():
            if calendar.name == name:
                return calendar
        raise ValueError(f"Calendar with name '{name}' not found.")

    def get_by_id(self, id: str) -> Calendar:
        """Look up a calendar by its unique identifier."""
        for calendar in self.list():
            if calendar.id == id:
                return calendar
        raise ValueError(f"Calendar with ID '{id}' not found.")

    def search(self, query: str) -> Generator[Calendar, None, None]:
        """Yield calendars whose name contains `query` (case-insensitive)."""
        for calendar in self.list():
            if query.lower() in calendar.name.lower():
                yield calendar

    def get_default(self) -> Calendar:
        """Return the EventKit-declared default calendar for new reminders."""
        default_calendar = self._event_store.defaultCalendarForNewReminders()
        if default_calendar:
            return Calendar(
                id=default_calendar.calendarIdentifier(),
                name=default_calendar.title(),
                owner="Unknown",
                color=str(default_calendar.color()),
                is_default=True,
                _event_store=self._event_store,
            )
        raise ValueError("No default calendar found.")
