"""Workflow error-handling tests.

Verifies that invalid moves raise the right errors:
- Moving a non-existent reminder → ValueError("not found")
- Moving to a non-existent calendar → ValueError("not found")
"""

from __future__ import annotations


def test_error_handling(rk, results):
    """Confirm both lookup paths fail loudly with the expected ValueError."""
    print("\n" + "=" * 70)
    print("TESTING ERROR HANDLING")
    print("=" * 70)

    # Move non-existent reminder
    try:
        fake_reminder_id = "00000000-0000-0000-0000-000000000000"
        fake_calendar_id = "00000000-0000-0000-0000-000000000001"

        try:
            rk.move_reminder(fake_reminder_id, fake_calendar_id)
            results.add_fail("Move non-existent reminder", "Should have raised ValueError")
        except ValueError as e:
            if "not found" in str(e):
                results.add_pass("Move non-existent reminder", "Correctly raised ValueError")
            else:
                results.add_fail("Move non-existent reminder", f"Wrong error: {e}")
    except Exception as e:
        results.add_fail("Error handling for invalid reminder", e)

    # Move to non-existent calendar (using a real reminder)
    try:
        reminder = rk.create_reminder(
            title="Error Test Reminder",
            notes="For testing error handling",
        )
        fake_calendar_id = "00000000-0000-0000-0000-000000000001"

        try:
            rk.move_reminder(reminder.id, fake_calendar_id)
            results.add_fail("Move to non-existent calendar", "Should have raised ValueError")
        except ValueError as e:
            if "not found" in str(e):
                results.add_pass("Move to non-existent calendar", "Correctly raised ValueError")
            else:
                results.add_fail("Move to non-existent calendar", f"Wrong error: {e}")

        rk.delete_reminder(reminder.id)

    except Exception as e:
        results.add_fail("Error handling for invalid calendar", e)
