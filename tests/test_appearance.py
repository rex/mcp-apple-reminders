"""CL-2.2 — list appearance + pinning tool tests (guards + registration)."""

from __future__ import annotations

import asyncio

import pytest

from mcp_apple_reminders._native.reminderkit_lists import (
    set_list_appearance,
    set_list_pinned,
    set_smart_list_pinned,
)


def _tool_names():
    from mcp_apple_reminders.server import mcp

    return {t.name for t in asyncio.run(mcp.list_tools())}


def test_appearance_tools_registered():
    assert {"set_list_appearance", "set_list_pinned", "set_smart_list_pinned"}.issubset(_tool_names())


def test_set_list_appearance_requires_list_id():
    with pytest.raises(ValueError, match="non-empty"):
        set_list_appearance("")


def test_set_list_pinned_requires_list_id():
    with pytest.raises(ValueError, match="non-empty"):
        set_list_pinned("", True)


def test_set_smart_list_pinned_requires_id():
    with pytest.raises(ValueError, match="non-empty"):
        set_smart_list_pinned("", True)
