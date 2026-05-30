"""Regression: Reminder datetimes must serialize as RFC 3339 (offset-bearing).

Naive-local datetimes used to serialize without an offset (e.g. '2026-06-19T04:00:00'),
which fails the JSON-Schema `date-time` (RFC 3339) format check FastMCP enforces on
structured output over the wire — so every Reminder-returning tool errored with -32602
even though the underlying EventKit write succeeded. The model now stamps the local UTC
offset on JSON serialization.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone

from mcp_apple_reminders.models import Reminder, reminder_deeplink

# RFC 3339 date-time REQUIRES a timezone offset (or 'Z'); that's the bit that was missing.
_RFC3339_OFFSET = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?([+-]\d{2}:\d{2}|Z)$")

_DT_FIELDS = ("due_date", "created_date", "modified_date", "completion_date", "start_date")


def _reminder(**kw) -> Reminder:
    base = {"id": "x", "title": "t", "list_id": "l", "deeplink": reminder_deeplink("x")}
    base.update(kw)
    return Reminder(**base)


def test_naive_due_date_serializes_with_offset():
    dumped = _reminder(due_date=datetime(2026, 6, 19, 4, 0, 0)).model_dump(mode="json")
    assert _RFC3339_OFFSET.match(dumped["due_date"]), dumped["due_date"]


def test_all_datetime_fields_offset_bearing():
    now = datetime(2026, 6, 19, 4, 0, 0)
    dumped = _reminder(**dict.fromkeys(_DT_FIELDS, now)).model_dump(mode="json")
    for f in _DT_FIELDS:
        assert _RFC3339_OFFSET.match(dumped[f]), f"{f}={dumped[f]!r}"


def test_aware_datetime_offset_preserved():
    dumped = _reminder(due_date=datetime(2026, 6, 19, 4, 0, 0, tzinfo=timezone.utc)).model_dump(mode="json")
    assert dumped["due_date"].endswith("+00:00")


def test_none_datetime_stays_none():
    assert _reminder().model_dump(mode="json")["due_date"] is None
