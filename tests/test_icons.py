"""Tests for icon resolution (caller-supplied; no server-side guesser)."""

from __future__ import annotations

import asyncio

from mcp_apple_reminders.icons import AGENT_DEFAULT_SYMBOL, _looks_like_emoji, resolve_icon


def test_agent_default_is_sparkles():
    assert AGENT_DEFAULT_SYMBOL == "sparkles"


def test_omitted_icon_uses_agent_default():
    r = resolve_icon(None)
    assert r.symbol == AGENT_DEFAULT_SYMBOL
    assert r.source == "default"


def test_auto_aliases_agent_default():
    r = resolve_icon("auto")
    assert r.symbol == AGENT_DEFAULT_SYMBOL
    assert r.source == "default"


def test_none_opts_out():
    r = resolve_icon("none")
    assert r.symbol is None
    assert r.emoji is None
    assert r.source == "none"


def test_explicit_sf_symbol():
    r = resolve_icon("cart.fill")
    assert r.symbol == "cart.fill"
    assert r.emoji is None
    assert r.source == "explicit"


def test_explicit_emoji():
    r = resolve_icon("🎉")
    assert r.emoji == "🎉"
    assert r.symbol is None
    assert r.source == "explicit"


def test_low_level_symbol_overrides_icon_arg():
    r = resolve_icon("none", explicit_symbol="flag.fill")
    assert r.symbol == "flag.fill"
    assert r.source == "explicit"


def test_looks_like_emoji():
    assert _looks_like_emoji("🎯")
    assert not _looks_like_emoji("star.fill")
    assert not _looks_like_emoji("airplane")


def test_suggester_tool_gone_create_calendar_remains():
    from mcp_apple_reminders.server import mcp

    names = {t.name for t in asyncio.run(mcp.list_tools())}
    assert "suggest_list_icon" not in names
    assert "create_calendar" in names
