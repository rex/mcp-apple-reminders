"""Unit-test fixtures: stub pyremindkit, inject into the server module.

Run from any platform — no EventKit required.
"""

from __future__ import annotations

import sys
import types
from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import pytest


@dataclass
class FakeCalendar:
    id: str
    name: str
    color: str = "blue"
    is_default: bool = False
    owner: str = "test"


@dataclass
class FakeReminder:
    id: str
    title: str
    completed: bool = False
    due_date: datetime | None = None
    notes: str | None = None
    url: str | None = None
    priority: int = 0
    flagged: bool = False
    list_id: str | None = None
    created_date: datetime | None = None
    modified_date: datetime | None = None


class _FakeCalendarsAPI:
    def __init__(self, store: FakeRemindKit) -> None:
        self._store = store

    def list(self) -> Iterable[FakeCalendar]:
        return list(self._store._calendars.values())

    def get(self, name: str) -> FakeCalendar:
        for cal in self._store._calendars.values():
            if cal.name == name:
                return cal
        raise KeyError(name)

    def get_by_id(self, calendar_id: str) -> FakeCalendar:
        return self._store._calendars[calendar_id]

    def search(self, query: str) -> Iterator[FakeCalendar]:
        q = query.lower()
        for cal in self._store._calendars.values():
            if q in cal.name.lower():
                yield cal

    def get_default(self) -> FakeCalendar:
        for cal in self._store._calendars.values():
            if cal.is_default:
                return cal
        raise KeyError("no default")


@dataclass
class FakeRemindKit:
    """A minimal pyremindkit-shaped fake backed by in-memory dicts."""

    _calendars: dict[str, FakeCalendar] = field(default_factory=dict)
    _reminders: dict[str, FakeReminder] = field(default_factory=dict)
    _next_id: int = 1

    def __post_init__(self) -> None:
        self.calendars = _FakeCalendarsAPI(self)

    # Convenience views for tests
    @property
    def reminders_dict(self) -> dict[str, FakeReminder]:
        return self._reminders

    def _new_id(self) -> str:
        self._next_id += 1
        return f"R-{self._next_id}"

    def add_calendar(self, name: str, *, default: bool = False) -> FakeCalendar:
        cal_id = f"C-{len(self._calendars) + 1}"
        cal = FakeCalendar(id=cal_id, name=name, is_default=default)
        self._calendars[cal_id] = cal
        return cal

    def create_reminder(self, title: str, **kwargs: Any) -> FakeReminder:
        rid = self._new_id()
        # calendar_id is the pyremindkit kwarg; map to list_id on the model
        list_id = kwargs.pop("calendar_id", None)
        rem = FakeReminder(id=rid, title=title, list_id=list_id, **kwargs)
        if rem.list_id is None:
            rem.list_id = next((c.id for c in self._calendars.values() if c.is_default), None)
        self._reminders[rid] = rem
        return rem

    def update_reminder(self, reminder_id: str, **kwargs: Any) -> FakeReminder:
        if reminder_id not in self._reminders:
            raise KeyError(reminder_id)
        rem = self._reminders[reminder_id]
        for k, v in kwargs.items():
            if k == "is_completed":
                rem.completed = v
            elif hasattr(rem, k):
                setattr(rem, k, v)
        return rem

    def delete_reminder(self, reminder_id: str) -> bool:
        return self._reminders.pop(reminder_id, None) is not None

    def get_reminder_by_id(self, reminder_id: str) -> FakeReminder:
        return self._reminders[reminder_id]

    def get_reminders(
        self,
        *,
        due_after: datetime | None = None,
        due_before: datetime | None = None,
        is_completed: bool | None = None,
        priority: int | None = None,
        calendar_id: str | None = None,
        limit: int | None = None,
    ) -> list[FakeReminder]:
        results = list(self._reminders.values())
        if is_completed is not None:
            results = [r for r in results if r.completed == is_completed]
        if calendar_id is not None:
            results = [r for r in results if r.list_id == calendar_id]
        if priority is not None:
            results = [r for r in results if r.priority == priority]
        if due_after is not None:
            results = [r for r in results if r.due_date is not None and _aware(r.due_date) >= _aware(due_after)]
        if due_before is not None:
            results = [r for r in results if r.due_date is not None and _aware(r.due_date) < _aware(due_before)]
        if limit is not None:
            results = results[:limit]
        return results

    def search_reminders(self, query: str) -> list[FakeReminder]:
        q = query.lower()
        return [
            r
            for r in self._reminders.values()
            if q in r.title.lower() or (r.notes is not None and q in r.notes.lower())
        ]

    def get_next_reminder(self) -> FakeReminder | None:
        upcoming = [r for r in self._reminders.values() if not r.completed and r.due_date is not None]
        upcoming.sort(key=lambda r: _aware(r.due_date))  # type: ignore[arg-type]
        return upcoming[0] if upcoming else None

    def move_reminder(self, reminder_id: str, calendar_id: str) -> FakeReminder:
        rem = self._reminders[reminder_id]
        if calendar_id not in self._calendars:
            raise KeyError(f"calendar {calendar_id} not found")
        rem.list_id = calendar_id
        return rem


def _aware(dt: datetime) -> datetime:
    """Treat naive datetimes as UTC for comparison."""
    if dt.tzinfo is None:
        from datetime import timezone

        return dt.replace(tzinfo=timezone.utc)
    return dt


def _install_pyremindkit_stub() -> None:
    """Register a fake ``pyremindkit`` module in ``sys.modules`` once."""
    if "pyremindkit" in sys.modules:
        return
    fake_module = types.ModuleType("pyremindkit")

    # RemindKit() returns whatever's been injected by the active test.
    class _StubRemindKit:
        def __new__(cls, *args: Any, **kwargs: Any) -> FakeRemindKit:
            from mcp_apple_reminders import server as srv

            return srv._remind  # type: ignore[return-value]

    fake_module.RemindKit = _StubRemindKit  # type: ignore[attr-defined]
    fake_module.Reminder = FakeReminder  # type: ignore[attr-defined]
    fake_module.Priority = type("Priority", (), {"NONE": 0, "LOW": 1, "MEDIUM": 5, "HIGH": 9})  # type: ignore[attr-defined]
    sys.modules["pyremindkit"] = fake_module


# Install the stub at import time so that the FIRST `from mcp_apple_reminders
# import server` in the test session uses it. The server module itself imports
# pyremindkit lazily, so this is enough.
_install_pyremindkit_stub()


@pytest.fixture(autouse=True)
def stub_pyremindkit() -> Iterator[FakeRemindKit]:
    """Inject a fresh in-memory FakeRemindKit for each test."""
    from mcp_apple_reminders import server as srv

    fake_store = FakeRemindKit()
    srv._set_remindkit_for_testing(fake_store)
    return fake_store
