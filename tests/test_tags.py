"""Slice 1.7 — set_tags + tag filter on get_reminders.

Coverage:
- `_native/reminderkit.py::add_tags` blank-input guards.
- `Reader.iter_reminders(tags=[...])` builds the SQL WHERE clause that
  filters by tag, and the returned Reminders have `tags` populated.
- Live: create a reminder with two tags via the helper; assert the
  SQLite reader sees them and that filtering by one of them returns it.
"""

from __future__ import annotations

import os
import time

import pytest

from mcp_apple_reminders._native.eventkit import DEFAULT_HELPER_PATH as EVENTKIT_HELPER
from mcp_apple_reminders._native.reminderkit import (
    DEFAULT_HELPER_PATH as REMINDERKIT_HELPER,
)
from mcp_apple_reminders._native.reminderkit import (
    add_tags,
)
from mcp_apple_reminders._native.sqlite import Reader, RemindersDBUnavailable, connect


def _open_or_skip():
    try:
        return connect()
    except RemindersDBUnavailable as e:
        pytest.skip(f"SQLite store unavailable: {e}")


# ---------------------------------------------------------------------------
# Unit
# ---------------------------------------------------------------------------


def test_add_tags_requires_id():
    with pytest.raises(ValueError, match="reminder_id"):
        add_tags("", ["x"])


def test_add_tags_rejects_empty_tag_list():
    with pytest.raises(ValueError, match="tags"):
        add_tags("UUID", [])
    with pytest.raises(ValueError, match="tags"):
        add_tags("UUID", ["", "   "])


def test_iter_reminders_with_unknown_tag_filter_returns_empty():
    """A tag nobody has yields zero results."""
    conn = _open_or_skip()
    try:
        out = list(Reader(conn).iter_reminders(tags=["this-tag-does-not-exist-zxq"], limit=5))
        assert out == []
    finally:
        conn.close()


def test_iter_reminders_with_no_tag_filter_populates_tags_field():
    """Reminders that have tags should have them surfaced in `tags`."""
    conn = _open_or_skip()
    try:
        # Pull 50 reminders; at least one should have tags on a real store.
        sample = list(Reader(conn).iter_reminders(limit=50))
        if not any(r.tags for r in sample):
            pytest.skip("No tagged reminders in the sample; can't exercise hydration.")
        for r in sample:
            assert isinstance(r.tags, list)
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Live integration
# ---------------------------------------------------------------------------


@pytest.mark.skipif(
    os.environ.get("REM_LIVE_HELPER") != "1" or not EVENTKIT_HELPER.exists() or not REMINDERKIT_HELPER.exists(),
    reason="Set REM_LIVE_HELPER=1 with both helpers built to run the live round-trip.",
)
def test_live_tags_and_filter_round_trip():
    """Create a reminder + 2 tags; assert SQLite surfaces them and filters."""
    from mcp_apple_reminders._native import RemindKit
    from mcp_apple_reminders._native.eventkit import create_calendar, delete_calendar

    rk = RemindKit()
    list_name = "REM-TEST-TAGS-S17"
    cal = create_calendar(list_name)
    try:
        native = rk.create_reminder(title="Tag target S17", calendar_id=cal.id)
        rid = native.id

        # The helper rejects empty tag arrays; we add two at once.
        add_tags(rid, ["work-s17", "urgent-s17"])

        # Poll until the SQLite cache reflects the new tags.
        deadline = time.time() + 5
        fetched = None
        while time.time() < deadline:
            time.sleep(0.25)
            conn = connect()
            try:
                fetched = Reader(conn).get_reminder_by_id(rid)
            finally:
                conn.close()
            if fetched and set(fetched.tags) >= {"work-s17", "urgent-s17"}:
                break

        assert fetched is not None, "Reminder vanished from SQLite"
        assert set(fetched.tags) >= {
            "work-s17",
            "urgent-s17",
        }, f"Expected tags to include work-s17 + urgent-s17; got {fetched.tags!r}"

        # Filter by tag — should return our reminder.
        conn = connect()
        try:
            hits = list(Reader(conn).iter_reminders(tags=["urgent-s17"]))
        finally:
            conn.close()
        assert any(h.id == rid for h in hits), (
            f"iter_reminders(tags=['urgent-s17']) missed our reminder; got " f"{[h.id for h in hits]}"
        )
    finally:
        delete_calendar(list_name)
