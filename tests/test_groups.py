"""Slice 5.1 (ADR 0001) — list-group support tests.

Coverage:
- Pydantic tail-append fields (`is_group`, `parent_group_id`) construct cleanly.
- `_native.reminderkit_actions.create_group / move_list_to_group` input guards.
- `Reader.list_groups()` + `Reader.iter_lists_in_group()` against the live store
  if Pierce's `Claude` group exists (skipped on fresh installs).
- Opt-in live round-trip: create test group + child list + move + verify +
  cleanup. Guarded by `REM_LIVE_HELPER=1`.
"""

from __future__ import annotations

import json
import os
import subprocess
import time

import pytest

from mcp_apple_reminders._native.eventkit import DEFAULT_HELPER_PATH as EVENTKIT_HELPER
from mcp_apple_reminders._native.reminderkit import (
    DEFAULT_HELPER_PATH as REMINDERKIT_HELPER,
)
from mcp_apple_reminders._native.reminderkit_actions import (
    create_group,
    delete_group,
    move_list_to_group,
)
from mcp_apple_reminders._native.sqlite import (
    Reader,
    RemindersDBUnavailable,
    connect,
)
from mcp_apple_reminders.models import Calendar, calendar_deeplink


def _open_or_skip():
    try:
        return connect()
    except RemindersDBUnavailable as e:
        pytest.skip(f"SQLite store unavailable: {e}")


# ---------------------------------------------------------------------------
# Pydantic tail-append (ADR 0001)
# ---------------------------------------------------------------------------


def test_calendar_defaults_to_not_a_group():
    """The `is_group` + `parent_group_id` tail fields default cleanly."""
    cal = Calendar(
        id="X",
        name="N",
        color="",
        is_default=False,
        deeplink=calendar_deeplink("X"),
    )
    assert cal.is_group is False
    assert cal.parent_group_id is None


def test_calendar_can_be_constructed_as_a_group():
    cal = Calendar(
        id="GROUP-UUID",
        name="MyGroup",
        color="",
        is_default=False,
        deeplink=calendar_deeplink("GROUP-UUID"),
        is_group=True,
    )
    assert cal.is_group is True
    assert cal.parent_group_id is None


# ---------------------------------------------------------------------------
# Wrapper input guards
# ---------------------------------------------------------------------------


def test_create_group_requires_name():
    with pytest.raises(ValueError, match="non-empty"):
        create_group("")
    with pytest.raises(ValueError, match="non-empty"):
        create_group("   ")


def test_move_list_to_group_requires_list_id():
    with pytest.raises(ValueError, match="non-empty"):
        move_list_to_group("", group_id=None)
    with pytest.raises(ValueError, match="non-empty"):
        move_list_to_group("   ", group_id="any")


# ---------------------------------------------------------------------------
# Reader smoke against the live store (skipped cleanly when store absent)
# ---------------------------------------------------------------------------


def test_reader_list_groups_against_live_store():
    """`Reader.list_groups()` returns rows where ZISGROUP=1.

    Pierce's repo has a `Claude` group; on a fresh store the list may be
    empty — that's fine, just exercises the SQL.
    """
    conn = _open_or_skip()
    try:
        groups = Reader(conn).list_groups()
        assert isinstance(groups, list)
        for g in groups:
            assert isinstance(g, Calendar)
            assert g.is_group is True, f"list_groups returned a non-group row: {g!r}"
    finally:
        conn.close()


def test_reader_iter_lists_in_unknown_group_yields_empty():
    conn = _open_or_skip()
    try:
        out = list(Reader(conn).iter_lists_in_group("00000000-0000-0000-0000-000000000000"))
        assert out == []
    finally:
        conn.close()


def test_list_calendars_include_groups_toggle():
    """`include_groups=False` excludes group rows; True returns them."""
    conn = _open_or_skip()
    try:
        reader = Reader(conn)
        without = reader.list_calendars(include_groups=False)
        with_groups = reader.list_calendars(include_groups=True)
        # Every row in `without` should be a non-group.
        assert all(c.is_group is False for c in without)
        # With-groups returns at least as many rows; if any groups exist,
        # the difference equals the number of groups in `list_groups`.
        assert len(with_groups) >= len(without)
        delta = len(with_groups) - len(without)
        assert delta == len(reader.list_groups())
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Live round-trip: create_group + create_list + move + verify + cleanup
# ---------------------------------------------------------------------------


@pytest.mark.skipif(
    os.environ.get("REM_LIVE_HELPER") != "1" or not REMINDERKIT_HELPER.exists() or not EVENTKIT_HELPER.exists(),
    reason="Set REM_LIVE_HELPER=1 with both helpers built to run the live S5.1 round-trip.",
)
def test_live_group_round_trip():
    """Create group + child list + move + verify via SQLite + clean up."""
    group_name = "REM-TEST-GROUP-S51"
    child_name = "REM-TEST-CHILDLIST-S51"

    # Pre-cleanup
    def _delete(title: str) -> None:
        subprocess.run(
            [str(EVENTKIT_HELPER)],
            input=json.dumps({"action": "delete_list", "title": title}),
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )

    _delete(group_name)
    _delete(child_name)
    time.sleep(0.5)

    group_resp = create_group(group_name)
    group_id = str(group_resp["id"])
    assert group_id

    # Use the Obj-C helper's create_list action (so both objects are
    # ReminderKit-owned, which is required for the reparent path).
    child_resp = subprocess.run(
        [str(REMINDERKIT_HELPER)],
        input=json.dumps({"action": "create_list", "name": child_name}),
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    assert child_resp.returncode == 0, child_resp.stderr
    child_id = str(json.loads(child_resp.stdout)["id"])
    assert child_id

    time.sleep(0.5)

    try:
        move_resp = move_list_to_group(child_id, group_id)
        assert move_resp.status == "moved"

        time.sleep(0.5)

        conn = connect()
        try:
            child = Reader(conn).get_calendar_by_id(child_id)
            assert child is not None
            assert (
                child.parent_group_id == group_id
            ), f"parent_group_id mismatch: got {child.parent_group_id!r}, want {group_id!r}"
        finally:
            conn.close()
    finally:
        # Detach the child from the group BEFORE either delete — groups can
        # only be deleted when empty (the delete_group action validates this).
        import contextlib

        with contextlib.suppress(Exception):
            move_list_to_group(child_id, None)
        _delete(child_name)
        # Group is invisible to EventKit; delete via Obj-C helper.
        with contextlib.suppress(Exception):
            delete_group(group_id)
