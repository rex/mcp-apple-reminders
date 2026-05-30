"""CL-2.9 read-back (ADR 0002): recurrence/alarm summaries + early-reminder decode.

The `*_summary` functions and the early-reminder blob decoder are pure, so they're
tested directly with primitives — no EventKit or live store needed. The EventKit
adapters (`summarize_recurrence`/`summarize_alarms`) are exercised live via
get_reminder during integration testing.
"""

from __future__ import annotations

import json

from mcp_apple_reminders._native._sqlite_helpers import _early_reminders_from_blob
from mcp_apple_reminders._native.eventkit_readback import alarm_summary, recurrence_summary


def test_recurrence_weekly():
    assert recurrence_summary(1, 1) == "Weekly"


def test_recurrence_every_two_weeks():
    assert recurrence_summary(1, 2) == "Every 2 weeks"


def test_recurrence_monthly_on_day():
    assert recurrence_summary(2, 1, days_of_month=[15]) == "Monthly on day 15"


def test_recurrence_weekly_on_friday():
    assert recurrence_summary(1, 1, days_of_week=[6]) == "Weekly on Fri"


def test_recurrence_monthly_until_date():
    assert recurrence_summary(2, 1, end_date="2026-08-30") == "Monthly until 2026-08-30"


def test_recurrence_with_occurrence_count():
    assert recurrence_summary(2, 1, end_count=3) == "Monthly for 3 occurrences"


def test_alarm_location_arriving():
    assert (
        alarm_summary(proximity=1, place="4051 Beltway Dr", radius=100.0) == "Arriving: 4051 Beltway Dr (within 100 m)"
    )


def test_alarm_location_leaving_no_place():
    assert alarm_summary(proximity=2) == "Leaving a location"


def test_alarm_absolute_date():
    assert alarm_summary(absolute_date="2026-06-10 09:00") == "At 2026-06-10 09:00"


def test_alarm_trivial_returns_none():
    assert alarm_summary() is None


def test_early_reminders_one_month():
    blob = json.dumps({"dueDateDeltaAlerts": [{"dueDateDeltaCount": -1, "dueDateDeltaUnit": 2}]}).encode()
    assert _early_reminders_from_blob(blob) == ["1 month before due"]


def test_early_reminders_plural_days():
    blob = json.dumps({"dueDateDeltaAlerts": [{"dueDateDeltaCount": -5, "dueDateDeltaUnit": 0}]}).encode()
    assert _early_reminders_from_blob(blob) == ["5 days before due"]


def test_early_reminders_none_blob():
    assert _early_reminders_from_blob(None) == []


def test_early_reminders_garbage_blob():
    assert _early_reminders_from_blob(b"not json at all") == []
