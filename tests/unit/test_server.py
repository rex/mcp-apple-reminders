"""End-to-end tool behavior with a mocked pyremindkit.

These cover the bug-fix matrix from the audit: RFC-3339 ``Z`` parsing,
falsy-value clearing on update, priority unification, today-window
exclusivity, missing-list error path.
"""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from mcp_apple_reminders import server as srv
from tests.unit.conftest import FakeRemindKit


@pytest.fixture
def populated(stub_pyremindkit: FakeRemindKit) -> FakeRemindKit:
    rk = stub_pyremindkit
    inbox = rk.add_calendar("Inbox", default=True)
    rk.add_calendar("Claude-On-Deck")
    rk.add_calendar("Claude-Active")
    rk.add_calendar("Claude-Done")
    rk.add_calendar("Claude-Blocked")
    rk.create_reminder(title="Eat", notes="lunch", priority=5, calendar_id=inbox.id)
    rk.create_reminder(
        title="Overdue thing",
        due_date=datetime.now() - timedelta(days=1),
        calendar_id=inbox.id,
    )
    return rk


class TestCreateReminder:
    def test_z_suffix_due_date(self, populated: FakeRemindKit) -> None:
        rem = srv.create_reminder(title="Standup", due_date="2024-01-15T14:30:00Z")
        assert rem.title == "Standup"
        assert rem.due_date is not None
        assert rem.due_date.tzinfo is not None  # parsed as aware

    def test_named_priority_works(self, populated: FakeRemindKit) -> None:
        rem = srv.create_reminder(title="Important", priority="high")
        assert rem.priority == 9

    def test_int_priority_works(self, populated: FakeRemindKit) -> None:
        rem = srv.create_reminder(title="Mid", priority=3)
        assert rem.priority == 3


class TestUpdateReminder:
    def test_clear_notes_with_empty_string(self, populated: FakeRemindKit) -> None:
        first = next(iter(populated.reminders_dict.values()))
        first.notes = "old notes"
        result = srv.update_reminder(reminder_id=first.id, notes="")
        # Old server treated "" as "leave alone"; new server clears it.
        assert result.notes == ""

    def test_clear_priority_with_zero(self, populated: FakeRemindKit) -> None:
        first = next(iter(populated.reminders_dict.values()))
        first.priority = 9
        result = srv.update_reminder(reminder_id=first.id, priority=0)
        assert result.priority == 0

    def test_omitting_field_leaves_unchanged(self, populated: FakeRemindKit) -> None:
        first = next(iter(populated.reminders_dict.values()))
        first.notes = "keep"
        result = srv.update_reminder(reminder_id=first.id, title="renamed")
        assert result.title == "renamed"
        assert result.notes == "keep"


class TestQueries:
    def test_today_window_excludes_tomorrow(self, populated: FakeRemindKit) -> None:
        # Add a reminder due exactly tomorrow at 00:00 — must NOT appear in "today".
        tomorrow_midnight = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        populated.create_reminder(title="Tomorrow", due_date=tomorrow_midnight)
        result = srv.get_today_reminders()
        titles = {r.title for r in result.reminders}
        assert "Tomorrow" not in titles

    def test_overdue_returns_past_only(self, populated: FakeRemindKit) -> None:
        result = srv.get_overdue_reminders()
        titles = {r.title for r in result.reminders}
        assert "Overdue thing" in titles


class TestWorkflowMoves:
    def test_move_active_succeeds(self, populated: FakeRemindKit) -> None:
        first = next(iter(populated.reminders_dict.values()))
        result = srv.move_reminder_active(reminder_id=first.id)
        active = populated.calendars.get("Claude-Active")
        assert result.list_id == active.id

    def test_move_to_missing_role_raises(
        self, monkeypatch: pytest.MonkeyPatch, stub_pyremindkit: FakeRemindKit
    ) -> None:
        monkeypatch.delenv("MCP_APPLE_REMINDERS_LIST_PREFIX", raising=False)
        rk = stub_pyremindkit
        inbox = rk.add_calendar("Inbox", default=True)
        rk.create_reminder(title="x", calendar_id=inbox.id)
        first = next(iter(rk.reminders_dict.values()))
        from mcp_apple_reminders._workflow import WorkflowListMissingError

        with pytest.raises(WorkflowListMissingError):
            srv.move_reminder_done(reminder_id=first.id)


class TestBatch:
    def test_batch_create(self, populated: FakeRemindKit) -> None:
        result = srv.batch_create_reminders(titles=["a", "b", "c"], calendar_id=None)
        assert result.count == 3
        assert {r.title for r in result.reminders} == {"a", "b", "c"}

    def test_batch_complete(self, populated: FakeRemindKit) -> None:
        ids = list(populated.reminders_dict.keys())
        result = srv.batch_complete_reminders(reminder_ids=ids)
        assert all(r.completed for r in result.reminders)


class TestWorkflowStatus:
    def test_snapshot_shape(self, populated: FakeRemindKit) -> None:
        result = srv.workflow_status()
        assert "on_deck" in result and "active" in result and "done" in result and "blocked" in result
        assert result["active"]["list"] == "Claude-Active"
        assert result["active"]["open_count"] == 0
