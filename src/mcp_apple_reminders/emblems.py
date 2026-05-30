"""Reminders list-icon EMBLEM catalog + keyword auto-suggest.

CRITICAL CORRECTION: Reminders.app list icons are a small, **curated emblem
catalog** — NOT arbitrary SF Symbols. The badge field (`ZBADGEEMBLEM`) accepts
an emblem id like ``weather5`` / ``food`` / ``symbol4``; an SF Symbol name such
as ``star.fill`` is stored but renders **blank**. (An earlier version of this
server wrongly documented "any SF Symbol renders" and dropped the icon
auto-suggest feature on that false premise — both are fixed here.)

The catalog below was extracted from ``RemindersUICore`` (the framework behind
the Reminders emblem picker) and validated as a superset of every emblem in use
in a real store. ``suggest_emblem`` maps a list title to the best-fit emblem —
the small categorized catalog is exactly what makes that tractable.

Use ``emoji`` on the appearance tools for an arbitrary glyph instead.
"""

from __future__ import annotations

from typing import Optional

# Emblem ids grouped by the catalog's category (bare category name = the
# category's default emblem; numbered variants are the alternates).
EMBLEMS_BY_CATEGORY: dict[str, list[str]] = {
    "activity": ["activity"],
    "animals": ["animals"],
    "arts": ["arts"],
    "business": ["business", "business2"],
    "education": ["education", "education1", "education2", "education3", "education4", "education5"],
    "finance": ["finance", "finance1", "finance2", "finance3"],
    "fitness": ["fitness"],
    "food": ["food"],
    "gaming": ["gaming"],
    "health": ["health", "health1", "health2"],
    "home": ["home"],
    "lifestyle": ["lifestyle", "lifestyle1", "lifestyle2"],
    "location": ["location", "location1", "location2", "location3"],
    "media": ["media", "media1", "media2", "media3", "media4", "media5"],
    "music": ["music"],
    "nature": ["nature", "nature1", "nature2"],
    "objects": ["objects"],
    "people": ["people", "people1", "people2", "people3"],
    "science": ["science"],
    "shopping": ["shopping", "shopping1", "shopping2", "shopping3", "shopping4"],
    "social": ["social"],
    "sport": ["sport", "sport1", "sport2", "sport3", "sport4", "sport5", "sport6"],
    "symbol": ["symbol", "symbol1", "symbol2", "symbol3", "symbol4", "symbol5", "symbol6", "symbol7"],
    "tech": ["tech"],
    "transit": ["transit"],
    "transport": ["transport", "transport1", "transport2", "transport3", "transport4"],
    "travel": ["travel"],
    "weather": ["weather", "weather1", "weather2", "weather3", "weather4", "weather5"],
    "work": ["work", "work1", "work2", "work3", "work4", "work5"],
}

EMBLEMS: frozenset[str] = frozenset(e for ems in EMBLEMS_BY_CATEGORY.values() for e in ems)

# Keyword → emblem id. First matching rule wins; keywords are substring-matched
# against the lowercased title. Mapped targets are all in EMBLEMS.
_SUGGEST_RULES: list[tuple[tuple[str, ...], str]] = [
    (
        (
            "grocer",
            "food",
            "meal",
            "cook",
            "recipe",
            "dinner",
            "lunch",
            "breakfast",
            "snack",
            "eat",
            "restaurant",
            "menu",
        ),
        "food",
    ),
    (("gym", "workout", "exercise", "fitness", "training", "yoga", "run", "jog"), "fitness"),
    (
        ("sport", "soccer", "basketball", "tennis", "football", "baseball", "golf", "match", "game day", "team"),
        "sport1",
    ),
    (
        (
            "school",
            "study",
            "learn",
            "class",
            "course",
            "homework",
            "exam",
            "lecture",
            "college",
            "university",
            "education",
            "reading list",
        ),
        "education1",
    ),
    (
        ("money", "budget", "finance", "bill", "invoice", "tax", "bank", "expense", "salary", "payment", "spend"),
        "finance1",
    ),
    (
        ("trip", "travel", "vacation", "flight", "hotel", "holiday", "journey", "itinerary", "passport", "packing"),
        "travel",
    ),
    (("car", "drive", "transport", "commute", "bus", "train", "subway", "parking", "fuel", "gas"), "transport1"),
    (("transit", "metro", "tram"), "transit"),
    (("home", "house", "chore", "apartment", "rent", "mortgage", "household"), "home"),
    (
        (
            "health",
            "doctor",
            "medical",
            "medicine",
            "dentist",
            "pharmacy",
            "appointment",
            "prescription",
            "therapy",
            "clinic",
        ),
        "health1",
    ),
    (("shop", "buy", "purchase", "store", "mall", "order", "wishlist", "cart", "shopping"), "shopping1"),
    (("weather", "rain", "snow", "forecast", "storm", "umbrella"), "weather1"),
    (("nature", "plant", "garden", "outdoor", "hike", "camp", "tree", "flower", "trail"), "nature1"),
    (("music", "song", "concert", "playlist", "band", "album", "gig"), "music"),
    (("movie", "film", "tv", "show", "watch", "book", "podcast", "video", "photo", "media", "stream"), "media1"),
    (("pet", "dog", "cat", "animal", "vet"), "animals"),
    (("party", "birthday", "wedding", "family", "friend", "social", "call", "guest", "rsvp"), "people1"),
    (("tech", "computer", "code", "software", "app", "device", "laptop", "server", "hardware", "it "), "tech"),
    (("play", "gaming", "video game", "xbox", "playstation", "nintendo", "console"), "gaming"),
    (("science", "lab", "experiment", "research", "chemistry", "biology", "physics"), "science"),
    (("art", "draw", "paint", "design", "craft", "sketch", "creative", "diy"), "arts"),
    (
        (
            "work",
            "job",
            "office",
            "meeting",
            "project",
            "deadline",
            "client",
            "career",
            "business",
            "standup",
            "agenda",
            "task",
        ),
        "work1",
    ),
    (("location", "place", "map", "address", "directions", "venue"), "location1"),
]


def is_valid_emblem(value: str) -> bool:
    """True if `value` is a real Reminders emblem id (renderable)."""
    return value in EMBLEMS


def suggest_emblem(title: Optional[str]) -> Optional[str]:
    """Best-fit emblem id for a list title, or None if nothing matches.

    Keyword → emblem heuristic over the curated catalog. Returns None (icon-less)
    rather than guessing when no keyword fits — a wrong icon is worse than none.
    """
    if not title:
        return None
    low = title.lower()
    for keywords, emblem in _SUGGEST_RULES:
        if any(kw in low for kw in keywords):
            return emblem
    return None
