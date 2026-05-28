"""Workflow-list discovery tests.

Checks that the `Claude-*` workflow lists exist and can be enumerated.
Returns the discovered list so downstream workflow tests can use it.
"""

from __future__ import annotations


def test_get_workflow_lists(rk, results):
    """Search for all `Claude-*` calendars; return them as a list (possibly empty)."""
    print("\n" + "=" * 70)
    print("TESTING GET WORKFLOW LISTS")
    print("=" * 70)

    try:
        workflow_lists = list(rk.calendars.search("Claude-"))

        if workflow_lists:
            results.add_pass(
                "Get workflow lists",
                f"Found {len(workflow_lists)} Claude-* list(s)",
            )
            print("\n  📋 Workflow Lists Found:")
            for cal in workflow_lists:
                print(f"     - {cal.name}")
                print(f"       ID: {cal.id}")
            return workflow_lists
        else:
            results.add_skip("Get workflow lists", "No Claude-* lists found in system")
            return []
    except Exception as e:
        results.add_fail("Get workflow lists", e)
        return []
