"""Slice 2.1 — MCP Resources smoke tests."""

from __future__ import annotations

import asyncio
import json

from mcp_apple_reminders.server import mcp


def _all_resources():
    return asyncio.run(mcp.list_resources())


def _all_templates():
    return asyncio.run(mcp.list_resource_templates())


def _read(uri: str):
    return asyncio.run(mcp.read_resource(uri))


def test_three_static_resources_registered():
    """The three non-templated resources are registered."""
    uris = {str(r.uri) for r in _all_resources()}
    assert "reminders://default" in uris
    assert "reminders://overdue" in uris
    assert "reminders://today" in uris


def test_one_templated_resource_registered():
    """The list-by-id template is registered."""
    templates = {t.uriTemplate for t in _all_templates()}
    assert "reminders://list/{calendar_id}" in templates


def test_default_resource_returns_json_payload():
    """`reminders://default` returns a JSON envelope with reminders + context."""
    content = _read("reminders://default")
    assert content, "Expected at least one content item"
    payload = json.loads(content[0].content)
    assert "reminders" in payload
    assert "context" in payload
    # Calendar key present when default resolved (skip the schema assertion
    # if the runner has no default — payload['context'] either has
    # 'calendar' or 'note').
    assert "calendar" in payload["context"] or "note" in payload["context"]


def test_overdue_resource_returns_json_payload():
    """`reminders://overdue` returns the JSON envelope and only incomplete items."""
    content = _read("reminders://overdue")
    payload = json.loads(content[0].content)
    assert payload["context"]["incomplete_only"] is True
    for r in payload["reminders"]:
        assert r["completed"] is False


def test_today_resource_returns_json_payload():
    """`reminders://today` returns the JSON envelope with a window context."""
    content = _read("reminders://today")
    payload = json.loads(content[0].content)
    assert "window" in payload["context"]
