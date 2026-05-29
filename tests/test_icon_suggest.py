"""Tests for the list-icon suggester: pure matcher, resolve policy, tool reg.

All async paths run via `asyncio.run` with a minimal fake Context, so no MCP
client, sampling, elicitation, or native helper is required. Sampling is
implicitly disabled because the fake Context has no `.session` attribute (and
the miss tests pass `allow_sampling=False` for determinism).
"""

from __future__ import annotations

import asyncio

from mcp_apple_reminders.icon_catalog import AGENT_FALLBACK_SYMBOL, ICON_KEYWORDS
from mcp_apple_reminders.icon_suggest import _looks_like_emoji, resolve_icon, suggest_icons


class _FakeCtx:
    """Minimal async Context stand-in: log no-ops, no `.session` (sampling off)."""

    async def debug(self, *a, **k): ...

    async def info(self, *a, **k): ...

    async def warning(self, *a, **k): ...

    async def error(self, *a, **k): ...


def test_catalog_is_around_100_groups_all_nonempty():
    assert 90 <= len(ICON_KEYWORDS) <= 130
    assert all(keywords for keywords in ICON_KEYWORDS.values())
    assert AGENT_FALLBACK_SYMBOL == "sparkles"


def test_exact_keyword_match():
    res = suggest_icons("Groceries")
    assert res.confident
    assert res.recommended == "cart.fill"
    assert res.candidates[0].symbol == "cart.fill"


def test_singular_plural_and_case_insensitive():
    assert suggest_icons("Books").recommended == "book.fill"
    assert suggest_icons("WORK").recommended == "briefcase.fill"


def test_multiword_title_scores_higher():
    res = suggest_icons("Grocery Shopping")
    assert res.recommended == "cart.fill"
    assert res.candidates[0].score >= 2


def test_no_match_falls_back_to_agent_glyph():
    res = suggest_icons("Qwzzx Plorbnak")
    assert not res.confident
    assert res.candidates == []
    assert res.recommended == AGENT_FALLBACK_SYMBOL


def test_looks_like_emoji():
    assert _looks_like_emoji("🛒")
    assert not _looks_like_emoji("cart.fill")
    assert not _looks_like_emoji("airplane")


def test_resolve_explicit_symbol_and_emoji():
    sym = asyncio.run(resolve_icon(_FakeCtx(), "Anything", "star.fill"))
    assert sym.symbol == "star.fill"
    assert sym.source == "explicit"
    emo = asyncio.run(resolve_icon(_FakeCtx(), "Party", "🎉"))
    assert emo.emoji == "🎉"
    assert emo.symbol is None
    assert emo.source == "explicit"


def test_resolve_none_opts_out():
    r = asyncio.run(resolve_icon(_FakeCtx(), "Whatever", "none"))
    assert r.symbol is None
    assert r.emoji is None
    assert r.source == "none"


def test_resolve_auto_confident_match():
    r = asyncio.run(resolve_icon(_FakeCtx(), "Groceries", "auto"))
    assert r.symbol == "cart.fill"
    assert r.source == "matched"


def test_resolve_auto_miss_uses_agent_fallback():
    r = asyncio.run(resolve_icon(_FakeCtx(), "Qwzzx", "auto", allow_sampling=False))
    assert r.symbol == AGENT_FALLBACK_SYMBOL
    assert r.source == "fallback"


def test_explicit_symbol_overrides_icon_arg():
    r = asyncio.run(resolve_icon(_FakeCtx(), "Groceries", "auto", explicit_symbol="flag.fill"))
    assert r.symbol == "flag.fill"
    assert r.source == "explicit"


def test_suggest_list_icon_tool_registered():
    from mcp_apple_reminders.server import mcp

    tools = asyncio.run(mcp.list_tools())
    assert "suggest_list_icon" in {t.name for t in tools}
