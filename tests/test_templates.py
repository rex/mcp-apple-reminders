"""CL-2.3 — template tool tests (guards + registration)."""

from __future__ import annotations

import asyncio

import pytest

from mcp_apple_reminders._native.reminderkit_content import (
    apply_template,
    create_template,
    delete_template,
)


def _tool_names():
    from mcp_apple_reminders.server import mcp

    return {t.name for t in asyncio.run(mcp.list_tools())}


def test_template_tools_registered():
    assert {"create_template", "apply_template", "delete_template"}.issubset(_tool_names())


def test_create_template_requires_name_and_source():
    with pytest.raises(ValueError, match="non-empty"):
        create_template("", "list-id")
    with pytest.raises(ValueError, match="non-empty"):
        create_template("Tmpl", "")


def test_apply_template_requires_id():
    with pytest.raises(ValueError, match="non-empty"):
        apply_template("")


def test_delete_template_requires_id():
    with pytest.raises(ValueError, match="non-empty"):
        delete_template("")
