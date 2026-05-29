"""Slice 4.1 — visibility-plane pilot."""

from __future__ import annotations

import asyncio
import json
import os

import pytest

from mcp_apple_reminders._native.eventkit import DEFAULT_HELPER_PATH


def _read_resource(uri: str):
    from mcp_apple_reminders.server import mcp

    return asyncio.run(mcp.read_resource(uri))


def test_agents_resource_registered():
    """`agents://current/{project_name}` is among the resource templates."""
    from mcp_apple_reminders.server import mcp

    templates = asyncio.run(mcp.list_resource_templates())
    uris = {t.uriTemplate for t in templates}
    assert "agents://current/{project_name}" in uris


def test_agents_resource_unknown_project_returns_bootstrap_note():
    """Unknown project name → JSON with a `note` field pointing at bootstrap."""
    content = _read_resource("agents://current/NeverHeardOf-S41")
    payload = json.loads(content[0].content)
    assert payload["project"] == "NeverHeardOf-S41"
    assert payload["list"] is None
    assert payload["todos"] == []
    assert "bootstrap_agent_list" in payload.get("note", "")


def test_bootstrap_agent_list_blank_project_name_raises():
    """The tool guards against an empty project name via the helper-level path."""
    from mcp_apple_reminders._native.eventkit import create_calendar

    with pytest.raises(ValueError, match="non-empty"):
        create_calendar("")  # the underlying wrapper rejects empty title


@pytest.mark.skipif(
    os.environ.get("REM_LIVE_HELPER") != "1" or not DEFAULT_HELPER_PATH.exists(),
    reason="Set REM_LIVE_HELPER=1 with the helper built to run the live round-trip.",
)
def test_live_create_and_resource_round_trip():
    """Bootstrap creates the list; the resource sees it; cleanup removes it."""
    from mcp_apple_reminders._native.eventkit import create_calendar, delete_calendar

    project = "TestPilot-S41-rt"
    list_name = f"Agents-{project}"

    # Pre-cleanup
    import contextlib

    with contextlib.suppress(Exception):
        delete_calendar(list_name)

    created = create_calendar(list_name, color="gray")
    assert created.name == list_name

    try:
        content = _read_resource(f"agents://current/{project}")
        payload = json.loads(content[0].content)
        assert payload["project"] == project
        assert payload["list"] is not None
        assert payload["list"]["name"] == list_name
    finally:
        delete_calendar(list_name)
