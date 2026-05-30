"""Appearance-options resource — canonical list colors + the emblem catalog.

Lets a client discover the valid values for the appearance tools
(`set_list_appearance`, `create_calendar`, `create_smart_list`,
`update_smart_list`) without guessing.

The color palette is AUTHORITATIVE: it mirrors the named colors the Obj-C
helper's `makeREMColor()` accepts (`_native/src/rem_reminderkit.m`); any `#RRGGBB`
hex also works. Icons are a curated EMBLEM catalog (see `emblems.py`, extracted
from RemindersUICore) — NOT SF Symbols (an SF Symbol name like 'star.fill' is
accepted by the API but renders BLANK). Pass an emblem id or an emoji, or let
`create_calendar` auto-suggest one from the list name.
"""

from __future__ import annotations

import json

from ..emblems import EMBLEMS, EMBLEMS_BY_CATEGORY
from ..server import mcp

# Canonical Apple Reminders list palette. MUST stay in sync with
# `_native/src/rem_reminderkit.m::makeREMColor` (name -> hex).
LIST_COLORS: list[dict[str, str]] = [
    {"name": "red", "hex": "#FF2968"},
    {"name": "orange", "hex": "#FF8D28"},
    {"name": "yellow", "hex": "#FFCC00"},
    {"name": "green", "hex": "#63DA38"},
    {"name": "blue", "hex": "#0088FF"},
    {"name": "purple", "hex": "#CC73E1"},
    {"name": "brown", "hex": "#A2845E"},
    {"name": "gray", "hex": "#5B626A"},
    {"name": "cyan", "hex": "#5AC8FA"},
    {"name": "teal", "hex": "#30B0C7"},
]

_PAYLOAD = {
    "colors": {
        "named": LIST_COLORS,
        "custom_hex": "Any #RRGGBB value is also accepted (e.g. '#34C759').",
        "note": (
            "Pass a named token (preferred) or a #RRGGBB hex to the `color` argument of "
            "set_list_appearance / create_calendar / create_smart_list / update_smart_list. "
            "Anything else is rejected."
        ),
    },
    "icons": {
        "kind": "Reminders emblem catalog (NOT SF Symbols)",
        "warning": (
            "Reminders list icons are a CURATED EMBLEM SET. SF Symbol names like 'star.fill' or "
            "'cart.fill' are accepted by the API but render BLANK — do NOT use them. Pass an "
            "emblem id from `by_category` below, or an `emoji` for an arbitrary glyph."
        ),
        "count": len(EMBLEMS),
        "by_category": EMBLEMS_BY_CATEGORY,
        "usage": (
            "Pass `symbol` = an emblem id (e.g. 'food', 'weather5', 'work1') or an `emoji` to "
            "set_list_appearance; or `icon` to create_calendar / create_smart_list. Omit the icon "
            "(or pass 'auto') and create_calendar AUTO-SUGGESTS an emblem from the list name; pass "
            "icon='none' to skip. An unrecognised emblem is rejected (set_list_appearance) or "
            "warned + skipped (create tools)."
        ),
        "auto_suggest": (
            "create_calendar / create_smart_list map the list title to a best-fit emblem via a "
            "keyword heuristic (groceries->food, work->work1, gym->fitness, school->education1, …)."
        ),
        "note": "Groups (sidebar folders) have NO color/icon in Reminders — only rename applies to a group.",
    },
}


@mcp.resource(
    "reminders://appearance",
    name="Appearance options",
    title="Appearance Options",
    description="Canonical list colors (name + hex) and the curated emblem catalog for list icons.",
    mime_type="application/json",
)
def appearance_options() -> str:
    """Return the valid color palette + emblem catalog as JSON."""
    return json.dumps(_PAYLOAD, indent=2)
