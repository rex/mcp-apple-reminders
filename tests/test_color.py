"""Unit tests for `_native/_color.py::decode_list_color`.

ZCOLOR is an NSKeyedArchiver `REMColor` blob (or NULL), never a plain string;
the decoder must pull the hex (preferred) or palette name out and never leak a
raw `b'...'` repr.
"""

from __future__ import annotations

import plistlib

from mcp_apple_reminders._native._color import decode_list_color


def test_none_returns_empty() -> None:
    assert decode_list_color(None) == ""


def test_plain_string_passthrough() -> None:
    assert decode_list_color("#FF9500") == "#FF9500"


def test_non_plist_bytes_returns_empty() -> None:
    assert decode_list_color(b"not a plist at all") == ""


def test_unexpected_type_returns_empty() -> None:
    assert decode_list_color(1234) == ""


def test_decodes_hex_from_archive() -> None:
    blob = plistlib.dumps({"$objects": ["$null", "custom", "#5856D6", "indigo"]}, fmt=plistlib.FMT_BINARY)
    assert decode_list_color(blob) == "#5856D6"  # hex preferred over the symbolic name


def test_falls_back_to_palette_name_without_hex() -> None:
    blob = plistlib.dumps({"$objects": ["$null", "custom", "purple"]}, fmt=plistlib.FMT_BINARY)
    assert decode_list_color(blob) == "purple"


def test_archive_without_color_returns_empty() -> None:
    blob = plistlib.dumps({"$objects": ["$null", "custom"]}, fmt=plistlib.FMT_BINARY)
    assert decode_list_color(blob) == ""
