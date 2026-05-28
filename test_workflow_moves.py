"""Workflow `move_reminder` test surface.

Two distinct test sequences:
- `test_move_reminder_functionality` — creates one reminder, moves it between
  two lists, verifies the move, moves it back. Returns the reminder ID for
  cleanup.
- `test_move_between_all_workflow_lists` — chain-moves a single reminder
  through every workflow list in order, recording success/failure per hop.
"""

from __future__ import annotations

from test_support.harness import get_current_cst_iso8601


def test_move_reminder_functionality(rk, workflow_lists, results):
    """Create a reminder, move it to a second list, verify, move back."""
    print("\n" + "=" * 70)
    print("TESTING MOVE REMINDER FUNCTIONALITY")
    print("=" * 70)

    if len(workflow_lists) < 2:
        results.add_skip(
            "Move reminder tests",
            f"Need at least 2 workflow lists, found {len(workflow_lists)}",
        )
        return None

    cst_timestamp = get_current_cst_iso8601()
    test_title = f"MCP WORKFLOW TEST: {cst_timestamp}"

    try:
        source_list = workflow_lists[0]
        reminder = rk.create_reminder(
            title=test_title,
            notes="Test reminder for workflow movement",
            calendar_id=source_list.id,
        )
        results.add_pass("Create reminder in workflow list", f"Created in '{source_list.name}'")

        assert reminder.list_id == source_list.id
        results.add_pass("Verify reminder in source list", f"Confirmed in '{source_list.name}'")

        # Move to second list
        target_list = workflow_lists[1]
        moved_reminder = rk.move_reminder(reminder.id, target_list.id)
        assert moved_reminder.list_id == target_list.id
        results.add_pass(
            "Move reminder to different list",
            f"Moved from '{source_list.name}' to '{target_list.name}'",
        )

        # Verify via fresh fetch
        verified = rk.get_reminder_by_id(reminder.id)
        assert verified.list_id == target_list.id
        results.add_pass("Verify reminder in target list", f"Confirmed in '{target_list.name}'")

        # Move back
        rk.move_reminder(reminder.id, source_list.id)
        verified = rk.get_reminder_by_id(reminder.id)
        assert verified.list_id == source_list.id
        results.add_pass("Move reminder back to original list", f"Moved back to '{source_list.name}'")

        return reminder.id

    except Exception as e:
        results.add_fail("Move reminder functionality", e)
        return None


def test_move_between_all_workflow_lists(rk, workflow_lists, results):
    """Chain-move one reminder through every workflow list in sequence."""
    print("\n" + "=" * 70)
    print("TESTING MOVE THROUGH ALL WORKFLOW LISTS")
    print("=" * 70)

    if len(workflow_lists) < 2:
        results.add_skip(
            "Move through all lists",
            f"Need at least 2 workflow lists, found {len(workflow_lists)}",
        )
        return None

    cst_timestamp = get_current_cst_iso8601()
    test_title = f"MCP WORKFLOW CHAIN TEST: {cst_timestamp}"

    try:
        reminder = rk.create_reminder(
            title=test_title,
            notes="Test reminder for moving through all workflow lists",
            calendar_id=workflow_lists[0].id,
        )
        results.add_pass("Create reminder for chain test", f"Created in '{workflow_lists[0].name}'")
        reminder_id = reminder.id

        for i, target_list in enumerate(workflow_lists[1:], 1):
            try:
                moved = rk.move_reminder(reminder_id, target_list.id)
                assert moved.list_id == target_list.id
                results.add_pass(
                    f"Move to list {i+1}/{len(workflow_lists)}",
                    f"Moved to '{target_list.name}'",
                )
            except Exception as e:
                results.add_fail(f"Move to '{target_list.name}'", e)
                return reminder_id

        results.add_pass(
            "Complete workflow chain",
            f"Successfully moved through all {len(workflow_lists)} lists",
        )
        return reminder_id

    except Exception as e:
        results.add_fail("Move through all workflow lists", e)
        return None
