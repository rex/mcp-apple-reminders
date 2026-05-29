"""Slice 1.8 — assign_section live integration + unit tests."""

from __future__ import annotations

import os
import time

import pytest

from mcp_apple_reminders._native.eventkit import DEFAULT_HELPER_PATH as EVENTKIT_HELPER
from mcp_apple_reminders._native.reminderkit import (
    DEFAULT_HELPER_PATH as REMINDERKIT_HELPER,
)
from mcp_apple_reminders._native.reminderkit import (
    _invoke_action,
)
from mcp_apple_reminders._native.reminderkit_actions import (
    assign_section,
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


def test_assign_section_requires_id():
    with pytest.raises(ValueError, match="reminder_id"):
        assign_section("", "S")


def test_assign_section_requires_section_id():
    with pytest.raises(ValueError, match="section_id"):
        assign_section("R", "")


def test_list_sections_in_unknown_calendar_returns_empty():
    conn = _open_or_skip()
    try:
        out = Reader(conn).list_sections_in_calendar("00000000-0000-0000-0000-000000000000")
        assert out == []
    finally:
        conn.close()


def test_get_section_name_unknown_returns_none():
    conn = _open_or_skip()
    try:
        out = Reader(conn).get_section_name("00000000-0000-0000-0000-000000000000")
        assert out is None
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Live integration — create list, parent, section; assign; verify
# ---------------------------------------------------------------------------


@pytest.mark.skipif(
    os.environ.get("REM_LIVE_HELPER") != "1" or not EVENTKIT_HELPER.exists() or not REMINDERKIT_HELPER.exists(),
    reason="Set REM_LIVE_HELPER=1 with both helpers built to run the live round-trip.",
)
def test_live_assign_section_round_trip():
    """Create list + reminder + section via add_section_and_assign, verify section_name."""
    from mcp_apple_reminders._native import RemindKit
    from mcp_apple_reminders._native.eventkit import create_calendar, delete_calendar

    rk = RemindKit()
    list_name = "REM-TEST-SECTION-S18"
    section_name = "S18-target"
    cal = create_calendar(list_name)
    try:
        native = rk.create_reminder(title="Section target S18", calendar_id=cal.id)
        rid = native.id

        # Use `add_section_and_assign` to create the section and put the
        # reminder in it in one helper call.
        _invoke_action("add_section_and_assign", id=rid, name=section_name)

        # Poll the SQLite reader until section_name surfaces.
        fetched_section = None
        deadline = time.time() + 5
        while time.time() < deadline:
            time.sleep(0.25)
            conn = connect()
            try:
                fetched_section = Reader(conn).get_section_name(rid)
            finally:
                conn.close()
            if fetched_section == section_name:
                break

        assert fetched_section == section_name, f"Expected section_name={section_name!r}, got {fetched_section!r}"

        # And the new section should appear in `list_sections_in_calendar`.
        conn = connect()
        try:
            sections = Reader(conn).list_sections_in_calendar(cal.id)
        finally:
            conn.close()
        names = [n for _id, n in sections]
        assert section_name in names, f"Expected {section_name!r} in {names!r}"
    finally:
        delete_calendar(list_name)
