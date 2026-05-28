"""Workflow convenience-function tests.

Tests the four named-list move shortcuts: On-Deck, Active, Done, Waiting.
Each test verifies the corresponding `Claude-*` list exists, then moves a
single test reminder through each in sequence.
"""

from __future__ import annotations

from test_support.harness import get_current_cst_iso8601


def test_workflow_convenience_functions(rk, workflow_lists, results):
    """Identify each named workflow list, then move a test reminder through each."""
    print("\n" + "=" * 70)
    print("TESTING WORKFLOW CONVENIENCE FUNCTIONS")
    print("=" * 70)

    on_deck_lists = [cal for cal in workflow_lists if "On-Deck" in cal.name]
    active_lists = [cal for cal in workflow_lists if "Active" in cal.name]
    done_lists = [cal for cal in workflow_lists if "Done" in cal.name]
    waiting_lists = [cal for cal in workflow_lists if "Waiting" in cal.name]

    on_deck_list = on_deck_lists[0] if on_deck_lists else None
    active_list = active_lists[0] if active_lists else None
    done_list = done_lists[0] if done_lists else None
    waiting_list = waiting_lists[0] if waiting_lists else None

    if on_deck_list:
        results.add_pass("Found Claude-On-Deck list", f"ID: {on_deck_list.id}")
    else:
        results.add_skip("Move to On-Deck tests", "Claude-On-Deck list not found")

    if active_list:
        results.add_pass("Found Claude-Active list", f"ID: {active_list.id}")
    else:
        results.add_skip("Move to Active tests", "Claude-Active list not found")

    if done_list:
        results.add_pass("Found Claude-Done list", f"ID: {done_list.id}")
    else:
        results.add_skip("Move to Done tests", "Claude-Done list not found")

    if waiting_list:
        results.add_pass("Found Claude-Waiting list", f"ID: {waiting_list.id}")
    else:
        results.add_skip("Move to Waiting tests", "Claude-Waiting list not found")

    cst_timestamp = get_current_cst_iso8601()
    test_title = f"MCP WORKFLOW CONVENIENCE TEST: {cst_timestamp}"

    try:
        reminder = rk.create_reminder(
            title=test_title,
            notes="Test reminder for workflow convenience functions",
        )
        results.add_pass("Create reminder for convenience tests", f"ID: {reminder.id[:8]}...")
        reminder_id = reminder.id

        for label, target in [
            ("On-Deck", on_deck_list),
            ("Active", active_list),
            ("Done", done_list),
            ("Waiting", waiting_list),
        ]:
            if not target:
                continue
            try:
                moved = rk.move_reminder(reminder_id, target.id)
                assert moved.list_id == target.id
                results.add_pass(
                    f"Move to Claude-{label}",
                    f"Successfully moved to {label} list",
                )
            except Exception as e:
                results.add_fail(f"Move to Claude-{label}", e)

        return reminder_id

    except Exception as e:
        results.add_fail("Workflow convenience functions", e)
        return None
