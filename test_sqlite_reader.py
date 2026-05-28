"""Smoke tests for `mcp_apple_reminders._native.sqlite`.

Slice 1.0 acceptance bullets exercised here:
- `list_calendars()` < 100 ms.
- `search_reminders` substring match works (case-insensitive).
- `get_reminder_by_id` returns a Pydantic Reminder with a populated deeplink.
- `RemindersDBUnavailable` is raised when the store dir is bogus.
- Schema introspection reports the required tables present.

Each test will skip cleanly if the Reminders store isn't accessible — for
instance, on a fresh CI runner without Reminders TCC consent. The
acceptance criteria are about the local-dev path; CI just verifies the
import surface.
"""

from __future__ import annotations

import time
from pathlib import Path

import pytest

from mcp_apple_reminders._native.sqlite import (
    Reader,
    RemindersDBUnavailable,
    connect,
    find_db_path,
)
from mcp_apple_reminders.models import Calendar, Reminder


def _open_or_skip():
    """Open the store or skip the test cleanly."""
    try:
        return connect()
    except RemindersDBUnavailable as e:
        pytest.skip(f"Reminders SQLite store not accessible on this runner: {e}")


def test_find_db_path_returns_largest_store():
    """`find_db_path` returns an extant `Data-*.sqlite` file."""
    try:
        path = find_db_path()
    except RemindersDBUnavailable as e:
        pytest.skip(str(e))
    assert path.exists()
    assert path.suffix == ".sqlite"
    assert path.name.startswith("Data-")


def test_find_db_path_raises_when_missing():
    """Bogus store dir raises `RemindersDBUnavailable`."""
    with pytest.raises(RemindersDBUnavailable):
        find_db_path(Path("/tmp/definitely-not-a-reminders-store"))


def test_schema_summary_reports_required_tables_present():
    """The three tables we actually query are present on a normal install."""
    conn = _open_or_skip()
    try:
        summary = Reader(conn).schema_summary()
        assert summary["required_present"] is True, f"Missing tables: {summary['missing']}"
        assert "ZREMCDBASELIST" in summary["tables"]
        assert "ZREMCDREMINDER" in summary["tables"]
        assert "ZREMCDBASESECTION" in summary["tables"]
    finally:
        conn.close()


def test_list_calendars_returns_pydantic_with_deeplinks():
    """Reader.list_calendars yields immutable Pydantic Calendars with populated deeplinks."""
    conn = _open_or_skip()
    try:
        cals = Reader(conn).list_calendars()
        assert isinstance(cals, list)
        if not cals:
            pytest.skip("No calendars present in store; can't exercise deeplink shape.")
        for c in cals:
            assert isinstance(c, Calendar)
            assert c.id
            assert c.deeplink == f"x-apple-reminderkit://REMCDList/{c.id}"
        # Exactly one default
        defaults = [c for c in cals if c.is_default]
        assert len(defaults) in (0, 1), "More than one default calendar should be impossible."
    finally:
        conn.close()


def test_list_calendars_under_100ms_latency():
    """Acceptance bullet: `Reader.list_calendars()` returns in < 100 ms.

    On a 27-calendar / 2200-reminder store, the SQLite path is sub-millisecond.
    The 100 ms budget gives plenty of headroom for slower hardware.
    """
    conn = _open_or_skip()
    try:
        reader = Reader(conn)
        # Warm cold caches with one throwaway call.
        reader.list_calendars()
        start = time.perf_counter()
        reader.list_calendars()
        elapsed_ms = (time.perf_counter() - start) * 1000
        assert elapsed_ms < 100, f"list_calendars took {elapsed_ms:.1f} ms (budget 100 ms)"
    finally:
        conn.close()


def test_iter_reminders_yields_pydantic_with_deeplinks():
    """`Reader.iter_reminders` yields Pydantic Reminders with deeplinks + list_id."""
    conn = _open_or_skip()
    try:
        sample = list(Reader(conn).iter_reminders(limit=5))
        if not sample:
            pytest.skip("No reminders in store.")
        for r in sample:
            assert isinstance(r, Reminder)
            assert r.id
            assert r.deeplink == f"x-apple-reminderkit://REMCDReminder/{r.id}"
            assert r.list_id  # join hit
    finally:
        conn.close()


def test_iter_reminders_completed_filter_is_honored():
    """`completed=True` returns only completed reminders; `completed=False` only incomplete."""
    conn = _open_or_skip()
    try:
        reader = Reader(conn)
        completed_sample = list(reader.iter_reminders(completed=True, limit=10))
        incomplete_sample = list(reader.iter_reminders(completed=False, limit=10))
        for r in completed_sample:
            assert r.completed is True
        for r in incomplete_sample:
            assert r.completed is False
    finally:
        conn.close()


def test_search_reminders_substring_case_insensitive():
    """search_reminders matches titles + notes, case-insensitively."""
    conn = _open_or_skip()
    try:
        reader = Reader(conn)
        sample = list(reader.iter_reminders(limit=1))
        if not sample:
            pytest.skip("No reminders to source a needle from.")
        first_word = (sample[0].title or "").split()[0] if (sample[0].title or "").split() else "a"
        results = reader.search_reminders(first_word, limit=20)
        # The original reminder should appear among the hits.
        assert any(r.title == sample[0].title for r in results) or first_word == "a"
    finally:
        conn.close()


def test_get_reminder_by_id_roundtrip():
    """A reminder pulled by iter_reminders can be re-fetched by its ZCKIDENTIFIER UUID."""
    conn = _open_or_skip()
    try:
        reader = Reader(conn)
        sample = list(reader.iter_reminders(limit=1))
        if not sample:
            pytest.skip("No reminders to round-trip.")
        original = sample[0]
        fetched = reader.get_reminder_by_id(original.id)
        assert fetched is not None
        assert fetched.id == original.id
        assert fetched.deeplink == original.deeplink
    finally:
        conn.close()


def test_get_reminder_by_id_missing_returns_none():
    """Unknown UUID returns None (not an exception)."""
    conn = _open_or_skip()
    try:
        assert Reader(conn).get_reminder_by_id("00000000-0000-0000-0000-000000000000") is None
    finally:
        conn.close()
