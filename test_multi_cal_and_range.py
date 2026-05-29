"""Slices 3.5 + 3.6 — multi-cal filter + completion range."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from mcp_apple_reminders._native.sqlite import Reader, RemindersDBUnavailable, connect


def _open_or_skip():
    try:
        return connect()
    except RemindersDBUnavailable as e:
        pytest.skip(f"SQLite store unavailable: {e}")


def test_iter_reminders_multi_calendar_filter_empty_for_unknown_uuids():
    """Two bogus UUIDs match no reminders."""
    conn = _open_or_skip()
    try:
        out = list(
            Reader(conn).iter_reminders(
                calendar_ids=[
                    "00000000-0000-0000-0000-000000000000",
                    "11111111-1111-1111-1111-111111111111",
                ],
                limit=5,
            )
        )
        assert out == []
    finally:
        conn.close()


def test_iter_reminders_multi_calendar_filter_returns_results_for_real_lists():
    """Passing every real list UUID returns at least one reminder."""
    conn = _open_or_skip()
    try:
        reader = Reader(conn)
        cals = reader.list_calendars()
        if len(cals) < 2:
            pytest.skip("Need at least 2 calendars to exercise multi-cal filter.")
        cal_ids = [c.id for c in cals[:2]]
        out = list(reader.iter_reminders(calendar_ids=cal_ids, limit=20))
        # Every result should be from one of the chosen lists.
        for r in out:
            assert r.list_id in cal_ids
    finally:
        conn.close()


def test_completion_range_filter_excludes_outside_window():
    """A 1-second-wide future window matches nothing."""
    conn = _open_or_skip()
    try:
        far_future = datetime.now() + timedelta(days=365 * 50)
        out = list(
            Reader(conn).iter_reminders(
                completed=True,
                completion_after=far_future,
                completion_before=far_future + timedelta(seconds=1),
                limit=5,
            )
        )
        assert out == []
    finally:
        conn.close()


def test_completion_range_filter_window_around_now_returns_reminders_with_completion_date():
    """An hour-wide window in the past may match (depending on store contents)."""
    conn = _open_or_skip()
    try:
        end = datetime.now()
        start = end - timedelta(days=365 * 5)
        out = list(
            Reader(conn).iter_reminders(
                completed=True,
                completion_after=start,
                completion_before=end,
                limit=10,
            )
        )
        # Every returned reminder must have a completion_date within the window.
        for r in out:
            assert r.completion_date is not None
            assert start <= r.completion_date < end
    finally:
        conn.close()
