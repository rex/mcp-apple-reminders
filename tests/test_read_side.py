"""Tests for CL-2.7 read-side: parent/subtask mapping, query filters, reg.

The mapper and query-builder are pure functions, so they're tested directly with
plain-dict fake rows (sqlite3.Row supports `[]` and `.keys()`, and so does dict).
No live store or Reminders permission required.
"""

from __future__ import annotations

import asyncio

from mcp_apple_reminders._native._sqlite_helpers import _build_reminders_query, _reminder_from_row

_BASE_ROW = {
    "ZCKIDENTIFIER": "child-uuid",
    "ZTITLE": "Child",
    "ZDUEDATE": None,
    "ZNOTES": None,
    "ZCOMPLETED": 0,
    "ZICSURL": None,
    "ZPRIORITY": 0,
    "ZCREATIONDATE": None,
    "ZLASTMODIFIEDDATE": None,
    "ZFLAGGED": 0,
    "ZCOMPLETIONDATE": None,
}


def test_row_maps_parent_and_subtasks():
    row = {**_BASE_ROW, "tags_csv": "", "parent_ckid": "parent-uuid", "subtask_ckids": "a,b,c"}
    rem = _reminder_from_row(row, "list-uuid")
    assert rem.parent_reminder_id == "parent-uuid"
    assert rem.subtasks == ["a", "b", "c"]


def test_row_no_parent_no_subtasks():
    row = {**_BASE_ROW, "tags_csv": "", "parent_ckid": None, "subtask_ckids": None}
    rem = _reminder_from_row(row, "list-uuid")
    assert rem.parent_reminder_id is None
    assert rem.subtasks == []


def test_row_tolerates_missing_optional_columns():
    # Rows from queries that don't SELECT the new columns must still map.
    rem = _reminder_from_row(dict(_BASE_ROW), "list-uuid")
    assert rem.parent_reminder_id is None
    assert rem.subtasks == []


def test_build_query_default_excludes_deleted():
    sql, params = _build_reminders_query(None, None, None, None)
    assert "r.ZMARKEDFORDELETION = ?" in sql
    assert params[0] == 0


def test_build_query_marked_for_deletion():
    _, params = _build_reminders_query(None, None, None, None, marked_for_deletion=True)
    assert params[0] == 1


def test_build_query_flagged_filter():
    sql, params = _build_reminders_query(None, None, None, None, flagged=True)
    assert "r.ZFLAGGED = ?" in sql
    assert params[1:] == [1]


def test_read_side_registered():
    from mcp_apple_reminders.server import mcp

    tool_names = {t.name for t in asyncio.run(mcp.list_tools())}
    assert "get_recently_deleted" in tool_names
    res_uris = {str(r.uri) for r in asyncio.run(mcp.list_resources())}
    assert "reminders://recently-deleted" in res_uris
