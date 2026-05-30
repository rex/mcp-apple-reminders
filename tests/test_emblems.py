"""Unit tests for the emblem catalog + keyword auto-suggest (emblems.py).

The catalog is the curated Reminders emblem set extracted from RemindersUICore;
suggest_emblem maps a list title to a best-fit emblem.
"""

from __future__ import annotations

from mcp_apple_reminders.emblems import EMBLEMS, is_valid_emblem, suggest_emblem


def test_catalog_nonempty_and_real_emblems_present() -> None:
    assert len(EMBLEMS) >= 80
    # known-good emblems observed in real stores
    for e in ("food", "weather5", "symbol4", "education1", "work1", "sport6"):
        assert is_valid_emblem(e), e


def test_sf_symbols_are_not_valid_emblems() -> None:
    for s in ("star.fill", "cart.fill", "sparkles", "house.fill"):
        assert not is_valid_emblem(s), s


def test_suggest_maps_keywords_to_emblems() -> None:
    cases = {
        "Grocery Shopping": "food",
        "Q3 Work Project": "work1",
        "Gym Routine": "fitness",
        "Kids School Stuff": "education1",
        "Monthly Budget": "finance1",
        "Italy Vacation": "travel",
        "Doctor Appointments": "health1",
        "Birthday Party": "people1",
        "Home Repairs": "home",
    }
    for title, emblem in cases.items():
        assert suggest_emblem(title) == emblem, title


def test_suggest_returns_none_when_nothing_fits() -> None:
    assert suggest_emblem("Zxqy Blorp Quux") is None
    assert suggest_emblem("") is None
    assert suggest_emblem(None) is None


def test_every_suggested_emblem_is_valid() -> None:
    # every mapping target must itself be a real emblem
    for title in [
        "food",
        "run",
        "gym",
        "school",
        "money",
        "trip",
        "car",
        "health",
        "shop",
        "weather",
        "nature",
        "music",
        "movie",
        "pet",
        "party",
        "tech",
        "game",
        "science",
        "art",
        "work",
        "location",
    ]:
        s = suggest_emblem(title)
        assert s is None or is_valid_emblem(s), (title, s)
