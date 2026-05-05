#!/usr/bin/env python3
"""
Comprehensive Test Suite for Workflow Management Tools.

Tests the new workflow management features:
- get_workflow_lists
- move_reminder_to_list
- move_reminder_on_deck
- move_reminder_active
"""

import sys
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

# Add the pyremindkit library to the path
_project_root = Path(__file__).parent
_pyremindkit_path = _project_root / "libs" / "pyremindkit" / "src"
sys.path.insert(0, str(_pyremindkit_path))


class TestResults:
    """Track test results for reporting."""

    def __init__(self):
        self.passed = []
        self.failed = []
        self.skipped = []

    def add_pass(self, test_name, message=""):
        self.passed.append((test_name, message))
        print(f"  ✅ {test_name}" + (f": {message}" if message else ""))

    def add_fail(self, test_name, error):
        self.failed.append((test_name, str(error)))
        print(f"  ❌ {test_name}: {error}")

    def add_skip(self, test_name, reason):
        self.skipped.append((test_name, reason))
        print(f"  ⏭️  {test_name}: {reason}")

    def summary(self):
        total = len(self.passed) + len(self.failed) + len(self.skipped)
        print("\n" + "=" * 70)
        print("TEST SUMMARY")
        print("=" * 70)
        print(f"Total Tests:  {total}")
        print(f"✅ Passed:    {len(self.passed)}")
        print(f"❌ Failed:    {len(self.failed)}")
        print(f"⏭️  Skipped:   {len(self.skipped)}")

        if self.failed:
            print("\n" + "=" * 70)
            print("FAILED TESTS:")
            print("=" * 70)
            for name, error in self.failed:
                print(f"❌ {name}")
                print(f"   Error: {error}")

        print("=" * 70)
        return len(self.failed) == 0


def get_current_cst_iso8601():
    """Get current time in CST timezone as ISO8601 string."""
    cst = ZoneInfo("America/Chicago")
    now = datetime.now(cst)
    return now.strftime("%Y-%m-%dT%H:%M:%S%z")


def test_get_workflow_lists(rk, results):
    """Test getting workflow lists (Claude-* calendars)."""
    print("\n" + "=" * 70)
    print("TESTING GET WORKFLOW LISTS")
    print("=" * 70)

    try:
        workflow_lists = list(rk.calendars.search("Claude-"))

        if workflow_lists:
            results.add_pass(
                "Get workflow lists",
                f"Found {len(workflow_lists)} Claude-* list(s)"
            )

            print("\n  📋 Workflow Lists Found:")
            for cal in workflow_lists:
                print(f"     - {cal.name}")
                print(f"       ID: {cal.id}")

            return workflow_lists
        else:
            results.add_skip(
                "Get workflow lists",
                "No Claude-* lists found in system"
            )
            return []
    except Exception as e:
        results.add_fail("Get workflow lists", e)
        return []


def test_move_reminder_functionality(rk, workflow_lists, results):
    """Test moving reminders between lists."""
    print("\n" + "=" * 70)
    print("TESTING MOVE REMINDER FUNCTIONALITY")
    print("=" * 70)

    if len(workflow_lists) < 2:
        results.add_skip(
            "Move reminder tests",
            f"Need at least 2 workflow lists, found {len(workflow_lists)}"
        )
        return None

    # Create a test reminder
    cst_timestamp = get_current_cst_iso8601()
    test_title = f"MCP WORKFLOW TEST: {cst_timestamp}"

    try:
        # Create in first workflow list
        source_list = workflow_lists[0]
        reminder = rk.create_reminder(
            title=test_title,
            notes="Test reminder for workflow movement",
            calendar_id=source_list.id
        )

        results.add_pass(
            "Create reminder in workflow list",
            f"Created in '{source_list.name}'"
        )

        # Verify it's in the source list
        assert reminder.list_id == source_list.id
        results.add_pass(
            "Verify reminder in source list",
            f"Confirmed in '{source_list.name}'"
        )

        # Move to second workflow list
        target_list = workflow_lists[1]
        moved_reminder = rk.move_reminder(reminder.id, target_list.id)

        assert moved_reminder.list_id == target_list.id
        results.add_pass(
            "Move reminder to different list",
            f"Moved from '{source_list.name}' to '{target_list.name}'"
        )

        # Verify the move by retrieving the reminder
        verified = rk.get_reminder_by_id(reminder.id)
        assert verified.list_id == target_list.id
        results.add_pass(
            "Verify reminder in target list",
            f"Confirmed in '{target_list.name}'"
        )

        # Move back to original list
        rk.move_reminder(reminder.id, source_list.id)
        verified = rk.get_reminder_by_id(reminder.id)
        assert verified.list_id == source_list.id
        results.add_pass(
            "Move reminder back to original list",
            f"Moved back to '{source_list.name}'"
        )

        return reminder.id

    except Exception as e:
        results.add_fail("Move reminder functionality", e)
        return None


def test_workflow_convenience_functions(rk, workflow_lists, results):
    """Test convenience functions for moving to specific workflow lists."""
    print("\n" + "=" * 70)
    print("TESTING WORKFLOW CONVENIENCE FUNCTIONS")
    print("=" * 70)

    # Find specific workflow lists
    on_deck_lists = [cal for cal in workflow_lists if "On-Deck" in cal.name]
    active_lists = [cal for cal in workflow_lists if "Active" in cal.name]
    done_lists = [cal for cal in workflow_lists if "Done" in cal.name]
    waiting_lists = [cal for cal in workflow_lists if "Waiting" in cal.name]

    if not on_deck_lists:
        results.add_skip(
            "Move to On-Deck tests",
            "Claude-On-Deck list not found"
        )
        on_deck_list = None
    else:
        on_deck_list = on_deck_lists[0]
        results.add_pass(
            "Found Claude-On-Deck list",
            f"ID: {on_deck_list.id}"
        )

    if not active_lists:
        results.add_skip(
            "Move to Active tests",
            "Claude-Active list not found"
        )
        active_list = None
    else:
        active_list = active_lists[0]
        results.add_pass(
            "Found Claude-Active list",
            f"ID: {active_list.id}"
        )

    if not done_lists:
        results.add_skip(
            "Move to Done tests",
            "Claude-Done list not found"
        )
        done_list = None
    else:
        done_list = done_lists[0]
        results.add_pass(
            "Found Claude-Done list",
            f"ID: {done_list.id}"
        )

    if not waiting_lists:
        results.add_skip(
            "Move to Waiting tests",
            "Claude-Waiting list not found"
        )
        waiting_list = None
    else:
        waiting_list = waiting_lists[0]
        results.add_pass(
            "Found Claude-Waiting list",
            f"ID: {waiting_list.id}"
        )

    # Create test reminder in default list
    cst_timestamp = get_current_cst_iso8601()
    test_title = f"MCP WORKFLOW CONVENIENCE TEST: {cst_timestamp}"

    try:
        reminder = rk.create_reminder(
            title=test_title,
            notes="Test reminder for workflow convenience functions"
        )
        results.add_pass(
            "Create reminder for convenience tests",
            f"ID: {reminder.id[:8]}..."
        )

        reminder_id = reminder.id

        # Test moving to On-Deck
        if on_deck_list:
            try:
                moved = rk.move_reminder(reminder_id, on_deck_list.id)
                assert moved.list_id == on_deck_list.id
                results.add_pass(
                    "Move to Claude-On-Deck",
                    "Successfully moved to On-Deck list"
                )
            except Exception as e:
                results.add_fail("Move to Claude-On-Deck", e)

        # Test moving to Active
        if active_list:
            try:
                moved = rk.move_reminder(reminder_id, active_list.id)
                assert moved.list_id == active_list.id
                results.add_pass(
                    "Move to Claude-Active",
                    "Successfully moved to Active list"
                )
            except Exception as e:
                results.add_fail("Move to Claude-Active", e)

        # Test moving to Done
        if done_list:
            try:
                moved = rk.move_reminder(reminder_id, done_list.id)
                assert moved.list_id == done_list.id
                results.add_pass(
                    "Move to Claude-Done",
                    "Successfully moved to Done list"
                )
            except Exception as e:
                results.add_fail("Move to Claude-Done", e)

        # Test moving to Waiting (Blocked)
        if waiting_list:
            try:
                moved = rk.move_reminder(reminder_id, waiting_list.id)
                assert moved.list_id == waiting_list.id
                results.add_pass(
                    "Move to Claude-Waiting",
                    "Successfully moved to Waiting list"
                )
            except Exception as e:
                results.add_fail("Move to Claude-Waiting", e)

        return reminder_id

    except Exception as e:
        results.add_fail("Workflow convenience functions", e)
        return None


def test_move_between_all_workflow_lists(rk, workflow_lists, results):
    """Test moving a reminder through all workflow lists."""
    print("\n" + "=" * 70)
    print("TESTING MOVE THROUGH ALL WORKFLOW LISTS")
    print("=" * 70)

    if len(workflow_lists) < 2:
        results.add_skip(
            "Move through all lists",
            f"Need at least 2 workflow lists, found {len(workflow_lists)}"
        )
        return None

    cst_timestamp = get_current_cst_iso8601()
    test_title = f"MCP WORKFLOW CHAIN TEST: {cst_timestamp}"

    try:
        # Create in first list
        reminder = rk.create_reminder(
            title=test_title,
            notes="Test reminder for moving through all workflow lists",
            calendar_id=workflow_lists[0].id
        )

        results.add_pass(
            "Create reminder for chain test",
            f"Created in '{workflow_lists[0].name}'"
        )

        reminder_id = reminder.id

        # Move through each workflow list
        for i, target_list in enumerate(workflow_lists[1:], 1):
            try:
                moved = rk.move_reminder(reminder_id, target_list.id)
                assert moved.list_id == target_list.id
                results.add_pass(
                    f"Move to list {i+1}/{len(workflow_lists)}",
                    f"Moved to '{target_list.name}'"
                )
            except Exception as e:
                results.add_fail(f"Move to '{target_list.name}'", e)
                return reminder_id

        results.add_pass(
            "Complete workflow chain",
            f"Successfully moved through all {len(workflow_lists)} lists"
        )

        return reminder_id

    except Exception as e:
        results.add_fail("Move through all workflow lists", e)
        return None


def test_error_handling(rk, results):
    """Test error handling for invalid operations."""
    print("\n" + "=" * 70)
    print("TESTING ERROR HANDLING")
    print("=" * 70)

    # Test moving non-existent reminder
    try:
        fake_reminder_id = "00000000-0000-0000-0000-000000000000"
        fake_calendar_id = "00000000-0000-0000-0000-000000000001"

        try:
            rk.move_reminder(fake_reminder_id, fake_calendar_id)
            results.add_fail(
                "Move non-existent reminder",
                "Should have raised ValueError"
            )
        except ValueError as e:
            if "not found" in str(e):
                results.add_pass(
                    "Move non-existent reminder",
                    "Correctly raised ValueError"
                )
            else:
                results.add_fail("Move non-existent reminder", f"Wrong error: {e}")
    except Exception as e:
        results.add_fail("Error handling for invalid reminder", e)

    # Test moving to non-existent calendar
    try:
        # Create a real reminder first
        reminder = rk.create_reminder(
            title="Error Test Reminder",
            notes="For testing error handling"
        )

        fake_calendar_id = "00000000-0000-0000-0000-000000000001"

        try:
            rk.move_reminder(reminder.id, fake_calendar_id)
            results.add_fail(
                "Move to non-existent calendar",
                "Should have raised ValueError"
            )
        except ValueError as e:
            if "not found" in str(e):
                results.add_pass(
                    "Move to non-existent calendar",
                    "Correctly raised ValueError"
                )
            else:
                results.add_fail("Move to non-existent calendar", f"Wrong error: {e}")

        # Clean up
        rk.delete_reminder(reminder.id)

    except Exception as e:
        results.add_fail("Error handling for invalid calendar", e)


def cleanup_test_reminders(rk, reminder_ids, results):
    """Clean up all test reminders."""
    print("\n" + "=" * 70)
    print("CLEANING UP TEST REMINDERS")
    print("=" * 70)

    for reminder_id in reminder_ids:
        if reminder_id:
            try:
                rk.delete_reminder(reminder_id)
                results.add_pass(
                    f"Delete reminder {reminder_id[:8]}",
                    "Deleted successfully"
                )
            except Exception as e:
                results.add_fail(f"Delete reminder {reminder_id[:8]}", e)


def main():
    """Run comprehensive workflow tools test suite."""
    print("\n" + "=" * 70)
    print("MCP APPLE REMINDERS - WORKFLOW TOOLS TEST SUITE")
    print("=" * 70)
    print(f"Test Start Time (CST): {get_current_cst_iso8601()}")
    print("=" * 70)

    results = TestResults()
    test_reminder_ids = []

    try:
        from pyremindkit import RemindKit

        # Initialize RemindKit
        print("\n📱 Initializing RemindKit...")
        rk = RemindKit()
        print("✅ RemindKit initialized successfully")

        # Test getting workflow lists
        workflow_lists = test_get_workflow_lists(rk, results)

        if not workflow_lists:
            print("\n⚠️  No workflow lists found!")
            print("To test workflow features, create lists in Apple Reminders:")
            print("  - Claude-Brain-Dump")
            print("  - Claude-On-Deck")
            print("  - Claude-Active")
            print("  - Claude-Done")
            print("  - Claude-Waiting")
        else:
            # Test move functionality
            reminder_id = test_move_reminder_functionality(rk, workflow_lists, results)
            if reminder_id:
                test_reminder_ids.append(reminder_id)

            # Test convenience functions
            reminder_id = test_workflow_convenience_functions(rk, workflow_lists, results)
            if reminder_id:
                test_reminder_ids.append(reminder_id)

            # Test moving through all lists
            reminder_id = test_move_between_all_workflow_lists(rk, workflow_lists, results)
            if reminder_id:
                test_reminder_ids.append(reminder_id)

        # Test error handling
        test_error_handling(rk, results)

        # Clean up
        if test_reminder_ids:
            cleanup_test_reminders(rk, test_reminder_ids, results)

    except PermissionError as e:
        print(f"\n❌ Permission Error: {e}")
        print("\n💡 To grant permissions:")
        print("   1. Go to System Settings → Privacy & Security → Reminders")
        print("   2. Enable access for Terminal or your Python interpreter")
        print("   3. Run this test again")
        return 1

    except Exception as e:
        print(f"\n❌ Fatal Error: {e}")
        import traceback
        traceback.print_exc()
        return 1

    # Print summary
    success = results.summary()

    print(f"\nTest End Time (CST): {get_current_cst_iso8601()}")
    print("=" * 70)

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
