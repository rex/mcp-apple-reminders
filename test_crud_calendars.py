"""Calendar-related CRUD tests.

Tests the read-only calendar surface: list, get_default, get-by-name, get-by-id,
search. Returns the discovered calendar list + default for downstream tests.
"""

from __future__ import annotations


def test_calendar_operations(rk, results):
    """Run every calendar lookup operation and record pass/fail.

    Returns a (calendars_list, default_calendar_or_None) tuple so downstream
    test functions can use them without re-fetching.
    """
    print("\n" + "=" * 70)
    print("TESTING CALENDAR OPERATIONS")
    print("=" * 70)

    # Test 1: List all calendars
    try:
        calendars = list(rk.calendars.list())
        results.add_pass("List all calendars", f"Found {len(calendars)} calendar(s)")

        if calendars:
            print("\n  📋 Available Calendars:")
            for i, cal in enumerate(calendars[:5], 1):
                default = " (default)" if cal.is_default else ""
                print(f"     {i}. {cal.name}{default}")
                print(f"        ID: {cal.id}")
            if len(calendars) > 5:
                print(f"     ... and {len(calendars) - 5} more")
    except Exception as e:
        results.add_fail("List all calendars", e)
        calendars = []

    # Test 2: Get default calendar
    try:
        default_cal = rk.calendars.get_default()
        results.add_pass("Get default calendar", f"'{default_cal.name}'")
    except Exception as e:
        results.add_fail("Get default calendar", e)
        default_cal = None

    # Test 3: Get calendar by name
    if calendars:
        try:
            first_cal = calendars[0]
            retrieved_cal = rk.calendars.get(first_cal.name)
            assert retrieved_cal.id == first_cal.id
            results.add_pass("Get calendar by name", f"Retrieved '{first_cal.name}'")
        except Exception as e:
            results.add_fail("Get calendar by name", e)

    # Test 4: Get calendar by ID
    if calendars:
        try:
            first_cal = calendars[0]
            retrieved_cal = rk.calendars.get_by_id(first_cal.id)
            assert retrieved_cal.name == first_cal.name
            results.add_pass("Get calendar by ID", f"Retrieved '{first_cal.name}'")
        except Exception as e:
            results.add_fail("Get calendar by ID", e)

    # Test 5: Search calendars
    if calendars and len(calendars) > 0:
        try:
            search_query = calendars[0].name[:3]
            search_results = list(rk.calendars.search(search_query))
            results.add_pass(
                "Search calendars",
                f"Query '{search_query}' found {len(search_results)} result(s)",
            )
        except Exception as e:
            results.add_fail("Search calendars", e)

    # Test 6: is_default correctness — exactly one True, and its id matches get_default
    if calendars and default_cal:
        try:
            default_matches = [cal for cal in calendars if cal.is_default]
            assert len(default_matches) == 1, f"Expected exactly 1 default calendar, got {len(default_matches)}"
            assert default_matches[0].id == default_cal.id, (
                f"Default calendar id mismatch: list()={default_matches[0].id!r} "
                f"vs get_default()={default_cal.id!r}"
            )
            results.add_pass(
                "is_default correctness",
                f"Exactly one default ('{default_matches[0].name}') matching get_default()",
            )
        except Exception as e:
            results.add_fail("is_default correctness", e)

    return calendars, default_cal
