"""Unit tests for icons.resolve_icon — emblem-based, with title auto-suggest.

Reminders list icons are a curated emblem catalog (NOT SF Symbols). resolve_icon
auto-suggests an emblem from the title when none is given, validates explicit
tokens against the catalog, and flags SF-symbol names as `invalid`.
"""

from __future__ import annotations

from mcp_apple_reminders.icons import _looks_like_emoji, resolve_icon


def test_auto_suggest_from_title() -> None:
    r = resolve_icon(None, title="Grocery Shopping")
    assert r.symbol == "food"
    assert r.source == "suggested"


def test_auto_keyword_word() -> None:
    r = resolve_icon("auto", title="Gym Routine")
    assert r.symbol == "fitness"
    assert r.source == "suggested"


def test_no_title_is_iconless() -> None:
    r = resolve_icon(None)
    assert r.symbol is None
    assert r.emoji is None
    assert r.source == "none"


def test_no_keyword_match_is_iconless() -> None:
    assert resolve_icon(None, title="Zxqy Blorp").source == "none"


def test_none_skips() -> None:
    r = resolve_icon("none")
    assert r.symbol is None
    assert r.source == "none"


def test_valid_emblem_explicit() -> None:
    r = resolve_icon("weather5")
    assert r.symbol == "weather5"
    assert r.source == "explicit"


def test_sf_symbol_name_is_invalid() -> None:
    r = resolve_icon("star.fill")
    assert r.source == "invalid"
    assert r.requested == "star.fill"
    assert r.symbol is None


def test_emoji_used_as_is() -> None:
    r = resolve_icon("🎉")
    assert r.emoji == "🎉"
    assert r.source == "explicit"


def test_explicit_symbol_overrides_and_is_validated() -> None:
    r = resolve_icon("auto", explicit_symbol="food")
    assert r.symbol == "food"
    assert r.source == "explicit"


def test_explicit_invalid_symbol_flagged() -> None:
    r = resolve_icon(None, explicit_symbol="cart.fill")
    assert r.source == "invalid"
    assert r.requested == "cart.fill"


def test_looks_like_emoji() -> None:
    assert not _looks_like_emoji("weather5")
    assert not _looks_like_emoji("star.fill")
    assert _looks_like_emoji("🎉")
