"""Tests for the reminders://appearance options resource (colors + icons)."""

from __future__ import annotations

import asyncio
import json


def test_appearance_resource_registered():
    from mcp_apple_reminders.server import mcp

    uris = {str(r.uri) for r in asyncio.run(mcp.list_resources())}
    assert "reminders://appearance" in uris


def test_appearance_payload_has_ten_named_colors():
    from mcp_apple_reminders.resources.appearance import appearance_options

    payload = json.loads(appearance_options())
    named = payload["colors"]["named"]
    assert len(named) == 10
    assert {c["name"] for c in named} == {
        "red",
        "orange",
        "yellow",
        "green",
        "blue",
        "purple",
        "brown",
        "gray",
        "cyan",
        "teal",
    }
    assert all(c["hex"].startswith("#") and len(c["hex"]) == 7 for c in named)
    assert "emblem" in payload["icons"]["kind"].lower()
    assert payload["icons"]["count"] > 0
    assert "food" in payload["icons"]["by_category"]["food"]
    assert "SF Symbol" in payload["icons"]["warning"]
