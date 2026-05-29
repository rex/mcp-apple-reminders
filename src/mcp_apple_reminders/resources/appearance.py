"""Appearance-options resource — the canonical list colors + icon guidance.

Lets a client discover the valid values to pass to the appearance tools
(`set_list_appearance`, `create_calendar`, `create_smart_list`,
`update_smart_list`, `set_list_appearance` on groups) without guessing.

The color palette is AUTHORITATIVE: it mirrors exactly the named colors the
Obj-C helper's `makeREMColor()` accepts (`_native/src/rem_reminderkit.m`). Any
`#RRGGBB` hex is also accepted. Icons are SF Symbols — the helper accepts any
SF Symbol name (or any emoji); Reminders.app's picker shows a curated subset,
but the server does not restrict to it.
"""

from __future__ import annotations

import json

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

# Common SF Symbols seen in Reminders.app's icon picker. NOT exhaustive and NOT
# enforced — any valid SF Symbol name works as `symbol`, any emoji as `emoji`.
COMMON_ICONS: list[str] = [
    "list.bullet",
    "star.fill",
    "flag.fill",
    "house.fill",
    "briefcase.fill",
    "cart.fill",
    "gift.fill",
    "book.fill",
    "graduationcap.fill",
    "heart.fill",
    "airplane",
    "car.fill",
    "fork.knife",
    "cup.and.saucer.fill",
    "dumbbell.fill",
    "figure.run",
    "leaf.fill",
    "pawprint.fill",
    "music.note",
    "gamecontroller.fill",
    "creditcard.fill",
    "dollarsign.circle.fill",
    "stethoscope",
    "pills.fill",
    "sun.max.fill",
    "moon.fill",
    "calendar",
    "clock.fill",
    "bell.fill",
    "tag.fill",
    "paperclip",
    "folder.fill",
    "lightbulb.fill",
    "bolt.fill",
    "flame.fill",
    "camera.fill",
    "paintbrush.fill",
    "hammer.fill",
    "wrench.and.screwdriver.fill",
    "key.fill",
    "lock.fill",
    "gearshape.fill",
    "person.2.fill",
    "phone.fill",
    "envelope.fill",
    "globe",
    "map.fill",
    "building.2.fill",
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
        "kind": "SF Symbols",
        "accepts_any": True,
        "note": (
            "`symbol` accepts ANY SF Symbol name (e.g. 'star.fill', 'cart.fill', 'house.fill'); "
            "`emoji` accepts any emoji character. The server does NOT restrict to a list — "
            "Reminders.app's picker shows a curated subset, but any valid SF Symbol renders. "
            "`common` below are frequent picker choices, not an exhaustive set."
        ),
        "common": COMMON_ICONS,
    },
}


@mcp.resource(
    "reminders://appearance",
    name="Appearance options",
    description="Canonical list colors (name + hex) and icon (SF Symbol / emoji) guidance for the appearance tools.",
    mime_type="application/json",
)
def appearance_options() -> str:
    """Return the valid color palette + icon guidance as JSON."""
    return json.dumps(_PAYLOAD, indent=2)
