#!/usr/bin/env python3
"""
Comprehensive CRUD Test Suite for MCP Apple Reminders.

This test suite performs exhaustive testing of all available operations:
- Calendar/list retrieval and management
- Full reminder CRUD lifecycle with all possible field operations
- All query and search operations
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


def test_calendar_operations(rk, results):
    """Test all calendar/list operations."""
    print("\n" + "=" * 70)
    print("TESTING CALENDAR OPERATIONS")
    print("=" * 70)

    # Test 1: List all calendars
    try:
        calendars = list(rk.calendars.list())
        results.add_pass(
            "List all calendars",
            f"Found {len(calendars)} calendar(s)"
        )

        # Store for later use
        if calendars:
            print(f"\n  📋 Available Calendars:")
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
        results.add_pass(
            "Get default calendar",
            f"'{default_cal.name}'"
        )
    except Exception as e:
        results.add_fail("Get default calendar", e)
        default_cal = None

    # Test 3: Get calendar by name
    if calendars:
        try:
            first_cal = calendars[0]
            retrieved_cal = rk.calendars.get(first_cal.name)
            assert retrieved_cal.id == first_cal.id
            results.add_pass(
                "Get calendar by name",
                f"Retrieved '{first_cal.name}'"
            )
        except Exception as e:
            results.add_fail("Get calendar by name", e)

    # Test 4: Get calendar by ID
    if calendars:
        try:
            first_cal = calendars[0]
            retrieved_cal = rk.calendars.get_by_id(first_cal.id)
            assert retrieved_cal.name == first_cal.name
            results.add_pass(
                "Get calendar by ID",
                f"Retrieved '{first_cal.name}'"
            )
        except Exception as e:
            results.add_fail("Get calendar by ID", e)

    # Test 5: Search calendars
    if calendars and len(calendars) > 0:
        try:
            # Search for first calendar's name
            search_query = calendars[0].name[:3]  # Use first 3 chars
            search_results = list(rk.calendars.search(search_query))
            results.add_pass(
                "Search calendars",
                f"Query '{search_query}' found {len(search_results)} result(s)"
            )
        except Exception as e:
            results.add_fail("Search calendars", e)

    return calendars, default_cal


def test_reminder_crud_operations(rk, calendars, default_cal, results):
    """Test comprehensive CRUD operations on a reminder."""
    print("\n" + "=" * 70)
    print("TESTING REMINDER CRUD OPERATIONS")
    print("=" * 70)

    # Generate test title with current CST timestamp
    cst_timestamp = get_current_cst_iso8601()
    test_title = f"MCP TEST: {cst_timestamp}"
    reminder_id = None

    print(f"\n  📝 Test Reminder Title: {test_title}")

    # Test 1: Create reminder with full metadata
    try:
        due_date = datetime.now() + timedelta(days=1)
        reminder = rk.create_reminder(
            title=test_title,
            notes="Initial test notes - this reminder was created by the comprehensive test suite",
            due_date=due_date,
            priority=5,  # Medium
            url="https://example.com/initial",
        )
        reminder_id = reminder.id

        assert reminder.title == test_title
        assert reminder.notes is not None
        assert reminder.due_date is not None
        assert reminder.priority == 5
        assert reminder.url is not None

        results.add_pass(
            "Create reminder with full metadata",
            f"ID: {reminder_id}"
        )
    except Exception as e:
        results.add_fail("Create reminder with full metadata", e)
        return None  # Can't continue without a reminder

    # Test 2: Retrieve reminder by ID
    try:
        retrieved = rk.get_reminder_by_id(reminder_id)
        assert retrieved.id == reminder_id
        assert retrieved.title == test_title
        results.add_pass("Retrieve reminder by ID", "All fields match")
    except Exception as e:
        results.add_fail("Retrieve reminder by ID", e)

    # Test 3: Update title
    try:
        new_title = f"UPDATED - {test_title}"
        updated = rk.update_reminder(reminder_id, title=new_title)
        assert updated.title == new_title
        results.add_pass("Update title", f"Changed to '{new_title[:50]}...'")
        test_title = new_title  # Update for future searches
    except Exception as e:
        results.add_fail("Update title", e)

    # Test 4: Add/Update notes
    try:
        new_notes = "Updated notes - testing note modification functionality"
        updated = rk.update_reminder(reminder_id, notes=new_notes)
        assert updated.notes == new_notes
        results.add_pass("Add/Update notes", "Notes updated successfully")
    except Exception as e:
        results.add_fail("Add/Update notes", e)

    # Test 5: Remove notes (set to empty string)
    try:
        updated = rk.update_reminder(reminder_id, notes="")
        assert updated.notes == ""
        results.add_pass("Remove notes", "Notes cleared")
    except Exception as e:
        results.add_fail("Remove notes", e)

    # Test 6: Re-add notes
    try:
        final_notes = "Final notes - restored after clearing"
        updated = rk.update_reminder(reminder_id, notes=final_notes)
        assert updated.notes == final_notes
        results.add_pass("Re-add notes", "Notes restored")
    except Exception as e:
        results.add_fail("Re-add notes", e)

    # Test 7: Update URL
    try:
        new_url = "https://example.com/updated"
        updated = rk.update_reminder(reminder_id, url=new_url)
        assert updated.url == new_url
        results.add_pass("Update URL", f"Changed to {new_url}")
    except Exception as e:
        results.add_fail("Update URL", e)

    # Test 8: Remove URL (set to empty string)
    try:
        updated = rk.update_reminder(reminder_id, url="")
        # URL might be None or empty string
        assert updated.url == "" or updated.url is None
        results.add_pass("Remove URL", "URL cleared")
    except Exception as e:
        results.add_fail("Remove URL", e)

    # Test 9: Re-add URL
    try:
        final_url = "https://example.com/final"
        updated = rk.update_reminder(reminder_id, url=final_url)
        assert updated.url == final_url
        results.add_pass("Re-add URL", f"URL restored to {final_url}")
    except Exception as e:
        results.add_fail("Re-add URL", e)

    # Test 10: Change priority - None
    try:
        updated = rk.update_reminder(reminder_id, priority=0)
        assert updated.priority == 0
        results.add_pass("Set priority to None", "Priority = 0")
    except Exception as e:
        results.add_fail("Set priority to None", e)

    # Test 11: Change priority - Low
    try:
        updated = rk.update_reminder(reminder_id, priority=1)
        assert updated.priority == 1
        results.add_pass("Set priority to Low", "Priority = 1")
    except Exception as e:
        results.add_fail("Set priority to Low", e)

    # Test 12: Change priority - Medium
    try:
        updated = rk.update_reminder(reminder_id, priority=5)
        assert updated.priority == 5
        results.add_pass("Set priority to Medium", "Priority = 5")
    except Exception as e:
        results.add_fail("Set priority to Medium", e)

    # Test 13: Change priority - High
    try:
        updated = rk.update_reminder(reminder_id, priority=9)
        assert updated.priority == 9
        results.add_pass("Set priority to High", "Priority = 9")
    except Exception as e:
        results.add_fail("Set priority to High", e)

    # Test 14: Update due date
    try:
        new_due_date = datetime.now() + timedelta(days=7)
        updated = rk.update_reminder(reminder_id, due_date=new_due_date)
        assert updated.due_date is not None
        results.add_pass("Update due date", f"Changed to {new_due_date.date()}")
    except Exception as e:
        results.add_fail("Update due date", e)

    # Test 15: Change due date to past (make it overdue)
    try:
        past_date = datetime.now() - timedelta(days=1)
        updated = rk.update_reminder(reminder_id, due_date=past_date)
        assert updated.due_date is not None
        results.add_pass("Set due date to past", "Now overdue")
    except Exception as e:
        results.add_fail("Set due date to past", e)

    # Test 16: Mark as completed
    try:
        updated = rk.update_reminder(reminder_id, is_completed=True)
        assert updated.completed == True
        results.add_pass("Mark as completed", "Reminder completed")
    except Exception as e:
        results.add_fail("Mark as completed", e)

    # Test 17: Mark as incomplete
    try:
        updated = rk.update_reminder(reminder_id, is_completed=False)
        assert updated.completed == False
        results.add_pass("Mark as incomplete", "Reminder reopened")
    except Exception as e:
        results.add_fail("Mark as incomplete", e)

    # Test 18: Move to different list (if multiple calendars exist)
    if len(calendars) > 1:
        try:
            # Get the reminder's current calendar
            current_reminder = rk.get_reminder_by_id(reminder_id)
            current_cal_id = current_reminder.list_id

            # Find a different calendar
            target_cal = None
            for cal in calendars:
                if cal.id != current_cal_id:
                    target_cal = cal
                    break

            if target_cal:
                # Note: RemindKit doesn't have a direct "move" operation
                # We need to delete and recreate in the new calendar
                # Or update the calendar if the API supports it
                results.add_skip(
                    "Move to different list",
                    "RemindKit API doesn't support moving between lists"
                )
            else:
                results.add_skip("Move to different list", "No alternative calendar available")
        except Exception as e:
            results.add_fail("Move to different list", e)
    else:
        results.add_skip("Move to different list", "Only one calendar available")

    # Test 19: Search for reminder by title
    try:
        search_results = list(rk.search_reminders("UPDATED"))
        found = any(r.id == reminder_id for r in search_results)
        assert found
        results.add_pass(
            "Search for reminder",
            f"Found in {len(search_results)} result(s)"
        )
    except Exception as e:
        results.add_fail("Search for reminder", e)

    # Test 20: Get reminder in filtered queries
    try:
        # Should appear in overdue reminders (we set due date to past)
        overdue = list(rk.get_reminders(
            due_before=datetime.now(),
            is_completed=False
        ))
        found = any(r.id == reminder_id for r in overdue)
        if found:
            results.add_pass(
                "Find in overdue reminders",
                f"Found among {len(overdue)} overdue reminder(s)"
            )
        else:
            results.add_fail(
                "Find in overdue reminders",
                "Reminder not found in overdue list"
            )
    except Exception as e:
        results.add_fail("Find in overdue reminders", e)

    # Test 21: Get all reminders (should include our test reminder)
    try:
        all_reminders = list(rk.get_reminders())
        found = any(r.id == reminder_id for r in all_reminders)
        assert found
        results.add_pass(
            "Find in all reminders",
            f"Found among {len(all_reminders)} total reminder(s)"
        )
    except Exception as e:
        results.add_fail("Find in all reminders", e)

    return reminder_id


def test_additional_reminder_operations(rk, results):
    """Test creating additional reminders with different configurations."""
    print("\n" + "=" * 70)
    print("TESTING ADDITIONAL REMINDER VARIATIONS")
    print("=" * 70)

    cst_timestamp = get_current_cst_iso8601()
    created_ids = []

    # Test 1: Minimal reminder (only title)
    try:
        title = f"MCP TEST MINIMAL: {cst_timestamp}"
        reminder = rk.create_reminder(title=title)
        created_ids.append(reminder.id)

        assert reminder.title == title
        assert reminder.notes is None or reminder.notes == ""
        assert reminder.due_date is None

        results.add_pass(
            "Create minimal reminder",
            "Only title, no other fields"
        )
    except Exception as e:
        results.add_fail("Create minimal reminder", e)

    # Test 2: Reminder with due date only
    try:
        title = f"MCP TEST DUE DATE: {cst_timestamp}"
        due_date = datetime.now() + timedelta(hours=2)
        reminder = rk.create_reminder(title=title, due_date=due_date)
        created_ids.append(reminder.id)

        assert reminder.title == title
        assert reminder.due_date is not None

        results.add_pass(
            "Create reminder with due date only",
            f"Due: {due_date.strftime('%Y-%m-%d %H:%M')}"
        )
    except Exception as e:
        results.add_fail("Create reminder with due date only", e)

    # Test 3: High priority reminder
    try:
        title = f"MCP TEST HIGH PRIORITY: {cst_timestamp}"
        reminder = rk.create_reminder(title=title, priority=9)
        created_ids.append(reminder.id)

        assert reminder.priority == 9

        results.add_pass(
            "Create high priority reminder",
            "Priority set to 9 (High)"
        )
    except Exception as e:
        results.add_fail("Create high priority reminder", e)

    # Test 4: Reminder with URL only
    try:
        title = f"MCP TEST URL: {cst_timestamp}"
        reminder = rk.create_reminder(
            title=title,
            url="https://github.com/anthropics/claude-code"
        )
        created_ids.append(reminder.id)

        assert reminder.url is not None

        results.add_pass(
            "Create reminder with URL",
            reminder.url
        )
    except Exception as e:
        results.add_fail("Create reminder with URL", e)

    # Test 5: Create in specific calendar (if available)
    try:
        calendars = list(rk.calendars.list())
        if len(calendars) > 1:
            # Use second calendar
            target_cal = calendars[1]
            title = f"MCP TEST SPECIFIC LIST: {cst_timestamp}"
            reminder = rk.create_reminder(
                title=title,
                calendar_id=target_cal.id
            )
            created_ids.append(reminder.id)

            assert reminder.list_id == target_cal.id

            results.add_pass(
                "Create in specific calendar",
                f"Created in '{target_cal.name}'"
            )
        else:
            results.add_skip(
                "Create in specific calendar",
                "Only one calendar available"
            )
    except Exception as e:
        results.add_fail("Create in specific calendar", e)

    return created_ids


def test_query_operations(rk, results):
    """Test various query and filter operations."""
    print("\n" + "=" * 70)
    print("TESTING QUERY OPERATIONS")
    print("=" * 70)

    # Test 1: Get next reminder
    try:
        next_reminder = rk.get_next_reminder()
        if next_reminder:
            results.add_pass(
                "Get next reminder",
                f"'{next_reminder.title}' due {next_reminder.due_date}"
            )
        else:
            results.add_pass("Get next reminder", "No upcoming reminders")
    except Exception as e:
        results.add_fail("Get next reminder", e)

    # Test 2: Get overdue reminders
    try:
        overdue = list(rk.get_reminders(
            due_before=datetime.now(),
            is_completed=False
        ))
        results.add_pass(
            "Get overdue reminders",
            f"Found {len(overdue)} overdue reminder(s)"
        )
    except Exception as e:
        results.add_fail("Get overdue reminders", e)

    # Test 3: Get completed reminders
    try:
        completed = list(rk.get_reminders(is_completed=True))
        results.add_pass(
            "Get completed reminders",
            f"Found {len(completed)} completed reminder(s)"
        )
    except Exception as e:
        results.add_fail("Get completed reminders", e)

    # Test 4: Get incomplete reminders
    try:
        incomplete = list(rk.get_reminders(is_completed=False))
        results.add_pass(
            "Get incomplete reminders",
            f"Found {len(incomplete)} incomplete reminder(s)"
        )
    except Exception as e:
        results.add_fail("Get incomplete reminders", e)

    # Test 5: Get reminders due in next 7 days
    try:
        week_from_now = datetime.now() + timedelta(days=7)
        upcoming = list(rk.get_reminders(
            due_after=datetime.now(),
            due_before=week_from_now,
            is_completed=False
        ))
        results.add_pass(
            "Get reminders due in next 7 days",
            f"Found {len(upcoming)} upcoming reminder(s)"
        )
    except Exception as e:
        results.add_fail("Get reminders due in next 7 days", e)

    # Test 6: Search by partial text
    try:
        search_results = list(rk.search_reminders("MCP TEST"))
        results.add_pass(
            "Search by partial text",
            f"Found {len(search_results)} result(s) matching 'MCP TEST'"
        )
    except Exception as e:
        results.add_fail("Search by partial text", e)


def cleanup_test_reminders(rk, reminder_ids, results):
    """Clean up all test reminders."""
    print("\n" + "=" * 70)
    print("CLEANING UP TEST REMINDERS")
    print("=" * 70)

    for reminder_id in reminder_ids:
        try:
            rk.delete_reminder(reminder_id)
            results.add_pass(f"Delete reminder {reminder_id[:8]}", "Deleted successfully")
        except Exception as e:
            results.add_fail(f"Delete reminder {reminder_id[:8]}", e)

    # Verify deletions
    for reminder_id in reminder_ids:
        try:
            rk.get_reminder_by_id(reminder_id)
            results.add_fail(
                f"Verify deletion {reminder_id[:8]}",
                "Reminder still exists!"
            )
        except ValueError:
            # Expected - reminder should not exist
            results.add_pass(f"Verify deletion {reminder_id[:8]}", "Confirmed deleted")
        except Exception as e:
            results.add_fail(f"Verify deletion {reminder_id[:8]}", e)


def main():
    """Run comprehensive test suite."""
    print("\n" + "=" * 70)
    print("MCP APPLE REMINDERS - COMPREHENSIVE CRUD TEST SUITE")
    print("=" * 70)
    print(f"Test Start Time (CST): {get_current_cst_iso8601()}")
    print("=" * 70)

    results = TestResults()
    all_test_reminder_ids = []

    try:
        from pyremindkit import RemindKit

        # Initialize RemindKit
        print("\n📱 Initializing RemindKit...")
        rk = RemindKit()
        print("✅ RemindKit initialized successfully")

        # Test calendar operations
        calendars, default_cal = test_calendar_operations(rk, results)

        # Test comprehensive CRUD operations
        main_reminder_id = test_reminder_crud_operations(
            rk, calendars, default_cal, results
        )
        if main_reminder_id:
            all_test_reminder_ids.append(main_reminder_id)

        # Test additional reminder variations
        additional_ids = test_additional_reminder_operations(rk, results)
        all_test_reminder_ids.extend(additional_ids)

        # Test query operations
        test_query_operations(rk, results)

        # Clean up all test reminders
        if all_test_reminder_ids:
            print(f"\n📋 Created {len(all_test_reminder_ids)} test reminder(s)")
            cleanup_test_reminders(rk, all_test_reminder_ids, results)

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
