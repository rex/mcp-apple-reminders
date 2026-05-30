"""Decode a Reminders list's ``ZCOLOR`` column into a usable color string.

``ZREMCDBASELIST.ZCOLOR`` is either NULL or an ``NSKeyedArchiver``-archived
``REMColor`` (a binary plist) — it is *never* a plain string. The naive
``str(blob)`` the reader used stringified the raw bytes into a useless
``b'bplist00...'`` repr for every colored list, so the SQLite reader routes the
column through :func:`decode_list_color`, which pulls the hex (preferred) or the
symbolic palette name out of the archive. Returns ``""`` when the column is NULL
or the blob can't be parsed.
"""

from __future__ import annotations

import plistlib
import re

_HEX_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")
_PALETTE_NAMES = frozenset(
    {
        "red",
        "orange",
        "yellow",
        "green",
        "mint",
        "teal",
        "cyan",
        "blue",
        "indigo",
        "purple",
        "pink",
        "brown",
        "gray",
        "grey",
    }
)


def decode_list_color(raw: object) -> str:
    """Return a hex (``#RRGGBB``) or palette name from a ZCOLOR value; ``""`` if none."""
    if raw is None:
        return ""
    if isinstance(raw, str):
        return raw  # defensive — Reminders stores a blob, but honor a plain string if one appears
    if not isinstance(raw, (bytes, bytearray)):
        return ""
    try:
        objects = plistlib.loads(bytes(raw)).get("$objects", [])
    except Exception:
        return ""
    strings = [o for o in objects if isinstance(o, str)]
    for s in strings:
        if _HEX_RE.match(s):
            return s.upper()
    for s in strings:
        if s.lower() in _PALETTE_NAMES:
            return s.lower()
    return ""
