"""CL-2.4 — grocery tool tests (guards + registration)."""

from __future__ import annotations

import asyncio

import pytest

from mcp_apple_reminders._native.reminderkit_content import categorize_grocery_items


def test_grocery_tool_registered():
    from mcp_apple_reminders.server import mcp

    assert "categorize_grocery_items" in {t.name for t in asyncio.run(mcp.list_tools())}


def test_categorize_requires_list_id():
    with pytest.raises(ValueError, match="non-empty"):
        categorize_grocery_items("", ["r1"])


def test_categorize_requires_reminder_ids():
    with pytest.raises(ValueError, match="non-empty list"):
        categorize_grocery_items("list-id", [])
