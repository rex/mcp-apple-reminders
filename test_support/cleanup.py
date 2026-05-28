"""Shared cleanup helper for test reminders.

`cleanup_test_reminders` deletes a list of reminder IDs and verifies each one
is actually gone afterward. Returns nothing — records pass/fail into the
supplied `TestResults` accumulator.
"""

from __future__ import annotations


def cleanup_test_reminders(rk, reminder_ids, results) -> None:
    """Delete each reminder ID, then verify it's actually removed.

    A reminder ID of `None` or empty string is skipped silently (caller may
    have collected misses from upstream failed creates).
    """
    print("\n" + "=" * 70)
    print("CLEANING UP TEST REMINDERS")
    print("=" * 70)

    for reminder_id in reminder_ids:
        if not reminder_id:
            continue
        try:
            rk.delete_reminder(reminder_id)
            results.add_pass(f"Delete reminder {reminder_id[:8]}", "Deleted successfully")
        except Exception as e:
            results.add_fail(f"Delete reminder {reminder_id[:8]}", e)

    # Second pass — confirm each one actually disappeared.
    for reminder_id in reminder_ids:
        if not reminder_id:
            continue
        try:
            rk.get_reminder_by_id(reminder_id)
            results.add_fail(f"Verify deletion {reminder_id[:8]}", "Reminder still exists!")
        except ValueError:
            results.add_pass(f"Verify deletion {reminder_id[:8]}", "Confirmed deleted")
        except Exception as e:
            results.add_fail(f"Verify deletion {reminder_id[:8]}", e)
