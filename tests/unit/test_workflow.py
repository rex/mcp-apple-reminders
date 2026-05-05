"""Tests for workflow-list resolution."""

from __future__ import annotations

import pytest

from mcp_apple_reminders._workflow import (
    WorkflowListMissingError,
    all_workflow_names,
    list_prefix,
    resolve_workflow_calendar,
    workflow_list_name,
)
from tests.unit.conftest import FakeRemindKit


class TestPrefixConfig:
    def test_default_prefix(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("MCP_APPLE_REMINDERS_LIST_PREFIX", raising=False)
        assert list_prefix() == "Claude-"
        assert workflow_list_name("on_deck") == "Claude-On-Deck"

    def test_env_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("MCP_APPLE_REMINDERS_LIST_PREFIX", "Work/")
        assert list_prefix() == "Work/"
        assert workflow_list_name("active") == "Work/Active"

    def test_all_names_in_role_order(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("MCP_APPLE_REMINDERS_LIST_PREFIX", raising=False)
        names = all_workflow_names()
        assert names == ["Claude-On-Deck", "Claude-Active", "Claude-Done", "Claude-Blocked"]


class TestResolve:
    def test_resolves_exact_match(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("MCP_APPLE_REMINDERS_LIST_PREFIX", raising=False)
        rk = FakeRemindKit()
        rk.add_calendar("Claude-On-Deck")
        rk.add_calendar("Claude-Active")
        cal = resolve_workflow_calendar(rk, "active")
        assert cal.name == "Claude-Active"

    def test_missing_raises_helpful_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("MCP_APPLE_REMINDERS_LIST_PREFIX", raising=False)
        rk = FakeRemindKit()
        rk.add_calendar("Personal")
        with pytest.raises(WorkflowListMissingError) as exc:
            resolve_workflow_calendar(rk, "done")
        assert "Claude-Done" in str(exc.value)
