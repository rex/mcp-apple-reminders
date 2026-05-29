"""CL-2.5 — reminder flag/extra tool tests (guards + registration)."""

from __future__ import annotations

import asyncio

import pytest

from mcp_apple_reminders._native.reminderkit_flags import (
    add_section_and_assign,
    set_early_reminder,
    set_urgent,
)


def _tool_names():
    from mcp_apple_reminders.server import mcp

    return {t.name for t in asyncio.run(mcp.list_tools())}


def test_flag_tools_registered():
    assert {"set_urgent", "set_early_reminder", "add_section_and_assign"}.issubset(_tool_names())


def test_set_urgent_requires_id():
    with pytest.raises(ValueError, match="non-empty"):
        set_urgent("", True)


def test_set_early_reminder_validates():
    with pytest.raises(ValueError, match="non-empty"):
        set_early_reminder("")
    with pytest.raises(ValueError, match="unit and count"):
        set_early_reminder("r1")
    with pytest.raises(ValueError, match="unit must be"):
        set_early_reminder("r1", unit=9, count=1)
    with pytest.raises(ValueError, match="count cannot be 0"):
        set_early_reminder("r1", unit=2, count=0)


def test_add_section_and_assign_requires_args():
    with pytest.raises(ValueError, match="non-empty"):
        add_section_and_assign("", "Sec")
    with pytest.raises(ValueError, match="non-empty"):
        add_section_and_assign("r1", "")
