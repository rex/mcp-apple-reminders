"""Slice 1.6 — set_flagged via the ReminderKit helper.

Unit: blank-input guard. Live: round-trip on a real reminder created in a
test list, verifying the SQLite reader reflects the flag flipped on/off.
"""

from __future__ import annotations

import os
import time

import pytest

from mcp_apple_reminders._native.eventkit import DEFAULT_HELPER_PATH as EVENTKIT_HELPER
from mcp_apple_reminders._native.reminderkit import (
    DEFAULT_HELPER_PATH as REMINDERKIT_HELPER,
)
from mcp_apple_reminders._native.reminderkit_actions import set_flagged

# ---------------------------------------------------------------------------
# Unit
# ---------------------------------------------------------------------------


def test_set_flagged_requires_id():
    with pytest.raises(ValueError, match="reminder_id"):
        set_flagged("", True)


# ---------------------------------------------------------------------------
# Live integration
# ---------------------------------------------------------------------------


@pytest.mark.skipif(
    os.environ.get("REM_LIVE_HELPER") != "1" or not EVENTKIT_HELPER.exists() or not REMINDERKIT_HELPER.exists(),
    reason="Set REM_LIVE_HELPER=1 with both helpers built to run the live round-trip.",
)
def test_live_set_and_clear_flag():
    from mcp_apple_reminders._native import RemindKit
    from mcp_apple_reminders._native.eventkit import create_calendar, delete_calendar
    from mcp_apple_reminders._native.sqlite import Reader, connect

    rk = RemindKit()
    list_name = "REM-TEST-FLAGGED-S16"
    cal = create_calendar(list_name)
    try:
        native = rk.create_reminder(title="Flag target S16", calendar_id=cal.id)
        rid = native.id

        # 1. Set the flag.
        set_flagged(rid, True)
        # Wait for the SQLite cache to reflect.
        for _ in range(20):
            time.sleep(0.25)
            conn = connect()
            try:
                fetched = Reader(conn).get_reminder_by_id(rid)
            finally:
                conn.close()
            if fetched is not None and fetched.flagged:
                break
        assert fetched is not None, "Reminder vanished from SQLite between set and read"
        assert fetched.flagged is True, f"Flag was not set; flagged={fetched.flagged!r}"

        # 2. Clear it.
        set_flagged(rid, False)
        for _ in range(20):
            time.sleep(0.25)
            conn = connect()
            try:
                fetched = Reader(conn).get_reminder_by_id(rid)
            finally:
                conn.close()
            if fetched is not None and not fetched.flagged:
                break
        assert fetched is not None, "Reminder vanished from SQLite between clear and read"
        assert fetched.flagged is False, f"Flag was not cleared; flagged={fetched.flagged!r}"
    finally:
        delete_calendar(list_name)
