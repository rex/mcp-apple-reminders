"""Slice 1.5 tests — subtask write path + SQLite read of subtasks.

Coverage:
- `_native/reminderkit_actions.py::create_subtask` blank-arg guards.
- `Reader.iter_subtasks` returns empty for unknown parent.
- `Reader.iter_subtasks` returns children for a real parent (live; skipped
  if no real reminders exist).
- Live round-trip: create a top-level reminder via EventKit, create 3
  subtasks via the ReminderKit helper, assert `Reader.iter_subtasks`
  finds all 3, then clean up.
"""

from __future__ import annotations

import os
import time

import pytest

from mcp_apple_reminders._native.eventkit import DEFAULT_HELPER_PATH as EVENTKIT_HELPER
from mcp_apple_reminders._native.reminderkit import (
    DEFAULT_HELPER_PATH as REMINDERKIT_HELPER,
)
from mcp_apple_reminders._native.reminderkit_actions import (
    create_subtask,
)
from mcp_apple_reminders._native.sqlite import (
    Reader,
    RemindersDBUnavailable,
    connect,
)


def _open_or_skip():
    try:
        return connect()
    except RemindersDBUnavailable as e:
        pytest.skip(f"SQLite store unavailable: {e}")


# ---------------------------------------------------------------------------
# Unit
# ---------------------------------------------------------------------------


def test_create_subtask_requires_parent_id():
    with pytest.raises(ValueError, match="parent_id"):
        create_subtask("", "x")


def test_create_subtask_requires_title():
    with pytest.raises(ValueError, match="title"):
        create_subtask("PARENT", "")


def test_iter_subtasks_unknown_parent_yields_empty():
    conn = _open_or_skip()
    try:
        out = list(Reader(conn).iter_subtasks("00000000-0000-0000-0000-000000000000"))
        assert out == []
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Live integration — full subtask round-trip with cleanup
# ---------------------------------------------------------------------------


@pytest.mark.skipif(
    os.environ.get("REM_LIVE_HELPER") != "1" or not EVENTKIT_HELPER.exists() or not REMINDERKIT_HELPER.exists(),
    reason="Set REM_LIVE_HELPER=1 with both helpers built to run the live round-trip.",
)
def test_live_subtask_round_trip():
    """Create parent + 3 subtasks → assert iter_subtasks finds all 3 → clean up."""
    from mcp_apple_reminders._native import RemindKit
    from mcp_apple_reminders._native.eventkit import delete_calendar

    rk = RemindKit()

    # Use a fresh list so cleanup is one operation.
    test_list_name = "REM-TEST-SUBTASKS-S15"

    # 1. Create a test list via the Swift helper, indirectly via RemindKit's
    #    underlying event store + helper subprocess. We use the helper here
    #    too so the test mirrors what S1.2 ships.
    from mcp_apple_reminders._native.eventkit import create_calendar

    test_list = create_calendar(test_list_name, color="blue")

    parent_id: str | None = None
    try:
        # 2. Create a parent reminder in the test list via EventKit.
        parent_native = rk.create_reminder(
            title="Parent reminder S15",
            calendar_id=test_list.id,
        )
        parent_id = parent_native.id

        # 3. Add 3 subtasks via the ReminderKit helper.
        for i in range(3):
            create_subtask(parent_id, f"Subtask {i + 1}")

        # The helper writes are eventually consistent w/ the SQLite cache —
        # give it a short grace window.
        deadline = time.time() + 4
        subtasks: list = []
        while time.time() < deadline:
            conn = connect()
            try:
                subtasks = list(Reader(conn).iter_subtasks(parent_id))
            finally:
                conn.close()
            if len(subtasks) == 3:
                break
            time.sleep(0.25)

        assert len(subtasks) == 3, f"Expected 3 subtasks, got {len(subtasks)}"
        titles = {s.title for s in subtasks}
        assert titles == {"Subtask 1", "Subtask 2", "Subtask 3"}
    finally:
        # 4. Cascade-delete the whole test list. Cleans up parent + subtasks
        #    in one call.
        try:
            delete_calendar(test_list_name)
        except Exception as e:  # pragma: no cover — cleanup-only diagnostics
            raise AssertionError(f"Cleanup failed; delete {test_list_name!r} manually: {e}") from e
