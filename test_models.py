"""Smoke tests for src/mcp_apple_reminders/models.py.

Covers:
- Deeplink helpers return the expected `x-apple-reminderkit://...` URIs.
- Calendar and Reminder Pydantic models construct, validate, freeze.
- Optional integration: open() round-trip — only runs when REM_DEEPLINK_SMOKE=1
  is set in the environment (so CI / fresh agents do not pop the UI).

Run with:
    ./venv/bin/python -m pytest test_models.py -v
"""

from __future__ import annotations

import os
import subprocess

import pytest
from pydantic import ValidationError

from mcp_apple_reminders.models import (
    CALENDAR_DEEPLINK_SCHEME,
    REMINDER_DEEPLINK_SCHEME,
    Calendar,
    Reminder,
    calendar_deeplink,
    reminder_deeplink,
)

# ---------------------------------------------------------------------------
# Deeplink helpers
# ---------------------------------------------------------------------------


def test_reminder_deeplink_builds_expected_uri():
    """`reminder_deeplink(uuid)` returns the documented scheme + uuid."""
    uri = reminder_deeplink("ABCD-1234")
    assert uri == "x-apple-reminderkit://REMCDReminder/ABCD-1234"
    assert uri.startswith(REMINDER_DEEPLINK_SCHEME)


def test_calendar_deeplink_builds_expected_uri():
    """`calendar_deeplink(uuid)` returns the documented scheme + uuid."""
    uri = calendar_deeplink("EFGH-5678")
    assert uri == "x-apple-reminderkit://REMCDList/EFGH-5678"
    assert uri.startswith(CALENDAR_DEEPLINK_SCHEME)


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


def test_calendar_minimum_fields_construct():
    """A Calendar with the 6 contract fields validates."""
    cal = Calendar(
        id="UUID-1",
        name="Inbox",
        color="#FF9500",
        is_default=True,
        owner=None,
        deeplink=calendar_deeplink("UUID-1"),
    )
    assert cal.id == "UUID-1"
    assert cal.deeplink.endswith("UUID-1")


def test_calendar_is_frozen():
    """Calendar instances are immutable (Pydantic frozen=True)."""
    cal = Calendar(
        id="UUID-2",
        name="Work",
        color="red",
        is_default=False,
        deeplink=calendar_deeplink("UUID-2"),
    )
    with pytest.raises(ValidationError):
        cal.name = "Personal"  # type: ignore[misc]


def test_reminder_minimum_fields_construct():
    """A Reminder with only the required fields (id, title, list_id, deeplink) validates."""
    r = Reminder(
        id="R-1",
        title="Buy milk",
        list_id="L-1",
        deeplink=reminder_deeplink("R-1"),
    )
    assert r.completed is False
    assert r.priority == 0
    assert r.subtasks == []
    assert r.tags == []
    assert r.flagged is False
    assert r.deeplink == "x-apple-reminderkit://REMCDReminder/R-1"


def test_reminder_field_order_is_canonical():
    """Field order is the contract freeze of Slice 0.3 — guarded by this test.

    Failing this test means someone reordered fields in models.py::Reminder
    without an ADR. Either revert or write the ADR.
    """
    expected = [
        "id",
        "title",
        "due_date",
        "notes",
        "completed",
        "url",
        "priority",
        "list_id",
        "created_date",
        "modified_date",
        "flagged",
        "parent_reminder_id",
        "subtasks",
        "tags",
        "section_name",
        "completion_date",
        "start_date",
        "deeplink",
    ]
    actual = list(Reminder.model_fields.keys())
    assert actual == expected, (
        f"Reminder field order drifted from the S0.3 contract freeze.\n"
        f"  expected: {expected}\n"
        f"  actual:   {actual}\n"
        f"Reorder back or write an ADR documenting the new contract."
    )


def test_calendar_field_order_is_canonical():
    """Field order is the contract freeze of Slice 0.3 — guarded by this test.

    Post-S5.1 (ADR 0001), `is_group` + `parent_group_id` were appended at the
    tail. Tail-additions are explicitly allowed by the S0.3 contract freeze.
    """
    expected = [
        "id",
        "name",
        "color",
        "is_default",
        "owner",
        "deeplink",
        # Post-S0.3 tail-appended additions (ADR 0001, S5.1)
        "is_group",
        "parent_group_id",
    ]
    actual = list(Calendar.model_fields.keys())
    assert actual == expected, (
        f"Calendar field order drifted from the S0.3 contract freeze.\n"
        f"  expected: {expected}\n"
        f"  actual:   {actual}"
    )


def test_reminder_priority_validation():
    """Pydantic enforces priority in [0, 9]."""
    with pytest.raises(ValidationError):
        Reminder(
            id="R-bad",
            title="x",
            list_id="L-1",
            priority=10,
            deeplink=reminder_deeplink("R-bad"),
        )


# ---------------------------------------------------------------------------
# EventKit → Pydantic converter integration (requires Reminders permission)
# ---------------------------------------------------------------------------


def test_eventkit_calendar_to_pydantic_against_default_calendar():
    """Convert the default EKCalendar into the Pydantic Calendar; deeplink derives.

    Requires Reminders permission. Will skip cleanly if permission is denied
    rather than failing the suite.
    """
    try:
        from mcp_apple_reminders._native import RemindKit
        from mcp_apple_reminders.models import eventkit_calendar_to_pydantic

        rk = RemindKit()
    except PermissionError:
        pytest.skip("Reminders permission not granted on this interpreter.")

    default_cal_view = rk.calendars.get_default()  # the dataclass-flavored view
    # Pull the actual EKCalendar handle from the event store.
    ek_cal = rk._event_store.calendarWithIdentifier_(default_cal_view.id)
    assert ek_cal is not None, "EventKit failed to resolve the default calendar."

    pydantic_cal = eventkit_calendar_to_pydantic(ek_cal, is_default=True)

    assert pydantic_cal.id == default_cal_view.id
    assert pydantic_cal.is_default is True
    assert pydantic_cal.deeplink == f"x-apple-reminderkit://REMCDList/{default_cal_view.id}"


def test_eventkit_reminder_to_pydantic_against_first_reminder():
    """Convert one real EKReminder into the Pydantic Reminder; deeplink derives.

    Picks the first reminder available in the default calendar. Skips if no
    reminders exist (fresh installs / empty default).
    """
    try:
        from mcp_apple_reminders._native import RemindKit
        from mcp_apple_reminders.models import eventkit_reminder_to_pydantic

        rk = RemindKit()
    except PermissionError:
        pytest.skip("Reminders permission not granted on this interpreter.")

    default_cal = rk.calendars.get_default()
    # Use the lower-level event-store API directly so we get the raw EKReminder,
    # not the pure-Python NamedTuple view.
    from threading import Event

    ek_calendar = rk._event_store.calendarWithIdentifier_(default_cal.id)
    predicate = rk._event_store.predicateForRemindersInCalendars_([ek_calendar])
    done = Event()
    captured: list = []

    def cb(reminders, _error=None):
        if reminders:
            captured.extend(reminders)
        done.set()

    rk._event_store.fetchRemindersMatchingPredicate_completion_(predicate, cb)
    done.wait(timeout=30)

    if not captured:
        pytest.skip("Default calendar has no reminders; cannot exercise converter.")

    ek_reminder = captured[0]
    pydantic_r = eventkit_reminder_to_pydantic(ek_reminder)

    expected_id = str(ek_reminder.calendarItemIdentifier())
    assert pydantic_r.id == expected_id, "Converter dropped calendarItemIdentifier."
    assert pydantic_r.deeplink == f"x-apple-reminderkit://REMCDReminder/{expected_id}"
    # ReminderKit-only fields should be their defaults via the EventKit path.
    assert pydantic_r.parent_reminder_id is None
    assert pydantic_r.subtasks == []
    assert pydantic_r.tags == []
    assert pydantic_r.section_name is None


# ---------------------------------------------------------------------------
# Optional deeplink round-trip (manual / local-only)
# ---------------------------------------------------------------------------


@pytest.mark.skipif(
    os.environ.get("REM_DEEPLINK_SMOKE") != "1",
    reason="Set REM_DEEPLINK_SMOKE=1 to run the open() round-trip locally.",
)
def test_calendar_deeplink_opens_reminders_app():
    """`open` should not error on a syntactically valid Reminders deeplink.

    NOTE: this will surface the Reminders.app UI. Skipped by default.
    """
    # Use the deeplink for the default list — Reminders.app will fall through
    # to the inbox if the UUID is unknown, but `open` itself should exit 0.
    deeplink = calendar_deeplink("00000000-0000-0000-0000-000000000000")
    result = subprocess.run(
        ["open", deeplink],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    assert result.returncode == 0, f"open(deeplink) failed: {result.stderr}"
