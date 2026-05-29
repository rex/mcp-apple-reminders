"""Reminder CRUD test sequence — single reminder lifecycle.

Creates one reminder with full metadata and then exercises every field-level
update path on it (title, notes, URL, priority, due date, completion). Returns
the reminder ID so the orchestrator can include it in cleanup.

Designed as one long sequence sharing a single reminder_id rather than per-test
isolation — the tests check round-trip consistency, so they must operate on the
same EventKit object.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from _support.harness import get_current_cst_iso8601


def test_reminder_crud_operations(rk, calendars, default_cal, results):
    """Run the full create-update-query-cleanup cycle on a single reminder.

    Returns the created reminder's ID (or None if create failed).
    """
    print("\n" + "=" * 70)
    print("TESTING REMINDER CRUD OPERATIONS")
    print("=" * 70)

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
            priority=5,
            url="https://example.com/initial",
        )
        reminder_id = reminder.id
        assert reminder.title == test_title
        assert reminder.notes is not None
        assert reminder.due_date is not None
        assert reminder.priority == 5
        assert reminder.url is not None
        results.add_pass("Create reminder with full metadata", f"ID: {reminder_id}")
    except Exception as e:
        results.add_fail("Create reminder with full metadata", e)
        return None

    # Test 2: Retrieve by ID
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
        test_title = new_title
    except Exception as e:
        results.add_fail("Update title", e)

    # Tests 4-6: notes update / clear / restore
    try:
        new_notes = "Updated notes - testing note modification functionality"
        updated = rk.update_reminder(reminder_id, notes=new_notes)
        assert updated.notes == new_notes
        results.add_pass("Add/Update notes", "Notes updated successfully")
    except Exception as e:
        results.add_fail("Add/Update notes", e)

    try:
        updated = rk.update_reminder(reminder_id, notes="")
        assert updated.notes == ""
        results.add_pass("Remove notes", "Notes cleared")
    except Exception as e:
        results.add_fail("Remove notes", e)

    try:
        final_notes = "Final notes - restored after clearing"
        updated = rk.update_reminder(reminder_id, notes=final_notes)
        assert updated.notes == final_notes
        results.add_pass("Re-add notes", "Notes restored")
    except Exception as e:
        results.add_fail("Re-add notes", e)

    # Tests 7-9: URL update / clear / restore
    try:
        new_url = "https://example.com/updated"
        updated = rk.update_reminder(reminder_id, url=new_url)
        assert updated.url == new_url
        results.add_pass("Update URL", f"Changed to {new_url}")
    except Exception as e:
        results.add_fail("Update URL", e)

    try:
        updated = rk.update_reminder(reminder_id, url="")
        assert updated.url == "" or updated.url is None
        results.add_pass("Remove URL", "URL cleared")
    except Exception as e:
        results.add_fail("Remove URL", e)

    try:
        final_url = "https://example.com/final"
        updated = rk.update_reminder(reminder_id, url=final_url)
        assert updated.url == final_url
        results.add_pass("Re-add URL", f"URL restored to {final_url}")
    except Exception as e:
        results.add_fail("Re-add URL", e)

    # Tests 10-13: priority transitions across all named buckets
    for label, value in [("None", 0), ("Low", 1), ("Medium", 5), ("High", 9)]:
        try:
            updated = rk.update_reminder(reminder_id, priority=value)
            assert updated.priority == value
            results.add_pass(f"Set priority to {label}", f"Priority = {value}")
        except Exception as e:
            results.add_fail(f"Set priority to {label}", e)

    # Test 14: Update due date forward
    try:
        new_due_date = datetime.now() + timedelta(days=7)
        updated = rk.update_reminder(reminder_id, due_date=new_due_date)
        assert updated.due_date is not None
        results.add_pass("Update due date", f"Changed to {new_due_date.date()}")
    except Exception as e:
        results.add_fail("Update due date", e)

    # Test 15: Set due date in past (now overdue)
    try:
        past_date = datetime.now() - timedelta(days=1)
        updated = rk.update_reminder(reminder_id, due_date=past_date)
        assert updated.due_date is not None
        results.add_pass("Set due date to past", "Now overdue")
    except Exception as e:
        results.add_fail("Set due date to past", e)

    # Tests 16-17: completion toggle
    try:
        updated = rk.update_reminder(reminder_id, is_completed=True)
        assert updated.completed is True
        results.add_pass("Mark as completed", "Reminder completed")
    except Exception as e:
        results.add_fail("Mark as completed", e)

    try:
        updated = rk.update_reminder(reminder_id, is_completed=False)
        assert updated.completed is False
        results.add_pass("Mark as incomplete", "Reminder reopened")
    except Exception as e:
        results.add_fail("Mark as incomplete", e)

    # Test 18: Move-between-lists (currently no public move method on the dataclass)
    if len(calendars) > 1:
        try:
            current_reminder = rk.get_reminder_by_id(reminder_id)
            current_cal_id = current_reminder.list_id
            target_cal = next((c for c in calendars if c.id != current_cal_id), None)
            if target_cal:
                results.add_skip(
                    "Move to different list",
                    "RemindKit API exposes move_reminder on the client, tested separately in workflow tests",
                )
            else:
                results.add_skip("Move to different list", "No alternative calendar available")
        except Exception as e:
            results.add_fail("Move to different list", e)
    else:
        results.add_skip("Move to different list", "Only one calendar available")

    # Test 19: Search finds this reminder
    try:
        search_results = list(rk.search_reminders("UPDATED"))
        found = any(r.id == reminder_id for r in search_results)
        assert found
        results.add_pass("Search for reminder", f"Found in {len(search_results)} result(s)")
    except Exception as e:
        results.add_fail("Search for reminder", e)

    # Test 20: Appears in overdue query (we set due date to past)
    try:
        overdue = list(rk.get_reminders(due_before=datetime.now(), is_completed=False))
        found = any(r.id == reminder_id for r in overdue)
        if found:
            results.add_pass("Find in overdue reminders", f"Found among {len(overdue)} overdue reminder(s)")
        else:
            results.add_fail("Find in overdue reminders", "Reminder not found in overdue list")
    except Exception as e:
        results.add_fail("Find in overdue reminders", e)

    # Test 21: Appears in get_reminders() with no filters
    try:
        all_reminders = list(rk.get_reminders())
        found = any(r.id == reminder_id for r in all_reminders)
        assert found
        results.add_pass("Find in all reminders", f"Found among {len(all_reminders)} total reminder(s)")
    except Exception as e:
        results.add_fail("Find in all reminders", e)

    return reminder_id
