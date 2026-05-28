#!/usr/bin/env python3
"""
End-to-end integration test for MCP Apple Reminders.
This test creates, updates, and deletes a test reminder to verify full functionality.
"""

import sys
from datetime import datetime, timedelta


def test_e2e_reminder_operations():
    """Test creating, updating, and deleting a reminder."""
    print("\n🔬 End-to-End Integration Test")
    print("=" * 60)
    print("This test will create, update, and delete a test reminder.")
    print("=" * 60)

    try:
        from mcp_apple_reminders._native import RemindKit

        # Initialize RemindKit
        rk = RemindKit()
        print("✅ RemindKit initialized")

        # Get default calendar
        default_cal = rk.calendars.get_default()
        print(f"✅ Using calendar: {default_cal.name}")

        # Test 1: Create a reminder
        print("\n📝 Test 1: Creating a reminder...")
        test_title = "MCP Test Reminder - Please Delete"
        due_date = datetime.now() + timedelta(days=1)

        reminder = rk.create_reminder(
            title=test_title,
            notes="This is a test reminder created by the MCP Apple Reminders integration test.",
            due_date=due_date,
            priority=5,  # Medium priority
        )

        print(f"✅ Reminder created with ID: {reminder.id}")
        print(f"   Title: {reminder.title}")
        print(f"   Due: {reminder.due_date}")
        print(f"   Priority: {reminder.priority}")

        # Test 2: Retrieve the reminder
        print("\n📋 Test 2: Retrieving the reminder...")
        retrieved = rk.get_reminder_by_id(reminder.id)
        assert retrieved.id == reminder.id, "Retrieved reminder ID doesn't match"
        assert retrieved.title == test_title, "Retrieved reminder title doesn't match"
        print("✅ Reminder retrieved successfully")
        print(f"   ID matches: {retrieved.id == reminder.id}")
        print(f"   Title matches: {retrieved.title == test_title}")

        # Test 3: Update the reminder
        print("\n✏️  Test 3: Updating the reminder...")
        updated_title = "MCP Test Reminder - UPDATED - Please Delete"
        updated = rk.update_reminder(
            reminder.id,
            title=updated_title,
            priority=9,  # High priority
        )

        assert updated.title == updated_title, "Updated title doesn't match"
        assert updated.priority == 9, "Updated priority doesn't match"
        print("✅ Reminder updated successfully")
        print(f"   New title: {updated.title}")
        print(f"   New priority: {updated.priority}")

        # Test 4: Mark as complete
        print("\n✓  Test 4: Marking reminder as complete...")
        completed = rk.update_reminder(reminder.id, is_completed=True)
        assert completed.completed is True, "Reminder should be marked as complete"
        print("✅ Reminder marked as complete")

        # Test 5: Mark as incomplete
        print("\n○  Test 5: Marking reminder as incomplete...")
        uncompleted = rk.update_reminder(reminder.id, is_completed=False)
        assert uncompleted.completed is False, "Reminder should be marked as incomplete"
        print("✅ Reminder marked as incomplete")

        # Test 6: Search for the reminder
        print("\n🔍 Test 6: Searching for the reminder...")
        search_results = list(rk.search_reminders("UPDATED"))
        found = any(r.id == reminder.id for r in search_results)
        assert found, "Reminder should be found in search results"
        print("✅ Reminder found in search results")
        print(f"   Found {len(search_results)} result(s)")

        # Test 7: Delete the reminder
        print("\n🗑️  Test 7: Deleting the reminder...")
        success = rk.delete_reminder(reminder.id)
        print("✅ Reminder deleted successfully")

        # Test 8: Verify deletion
        print("\n🔍 Test 8: Verifying deletion...")
        try:
            rk.get_reminder_by_id(reminder.id)
            print("❌ Reminder should have been deleted!")
            return False
        except ValueError:
            print("✅ Reminder properly deleted (not found)")

        print("\n" + "=" * 60)
        print("🎉 All end-to-end tests passed!")
        print("=" * 60)

        return True

    except Exception as e:
        print(f"\n❌ End-to-end test failed: {e}")
        import traceback

        traceback.print_exc()

        # Try to clean up if we created a reminder
        try:
            if "reminder" in locals() and reminder:
                print(f"\n🧹 Attempting cleanup: deleting test reminder {reminder.id}")
                rk.delete_reminder(reminder.id)
                print("✅ Cleanup successful")
        except Exception:
            pass

        return False


def main():
    """Run end-to-end tests."""
    print("\n" + "=" * 60)
    print("MCP APPLE REMINDERS - END-TO-END INTEGRATION TEST")
    print("=" * 60)

    success = test_e2e_reminder_operations()

    if success:
        print("\n✨ Integration test complete - all systems operational!")
        print("\nYour MCP Apple Reminders server is fully functional and ready to use.")
        return 0
    else:
        print("\n⚠️  Integration test failed - please review the errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
