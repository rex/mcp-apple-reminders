"""Reminder creation variation tests.

Exercises `create_reminder` with progressively less metadata (full → minimal),
and with placement into specific calendars. Returns the list of created IDs so
the orchestrator can include them in cleanup.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from _support.harness import get_current_cst_iso8601


def test_additional_reminder_operations(rk, results):
    """Create reminders with varied configurations and record outcomes."""
    print("\n" + "=" * 70)
    print("TESTING ADDITIONAL REMINDER VARIATIONS")
    print("=" * 70)

    cst_timestamp = get_current_cst_iso8601()
    created_ids = []

    # Minimal reminder (title only)
    try:
        title = f"MCP TEST MINIMAL: {cst_timestamp}"
        reminder = rk.create_reminder(title=title)
        created_ids.append(reminder.id)
        assert reminder.title == title
        assert reminder.notes is None or reminder.notes == ""
        assert reminder.due_date is None
        results.add_pass("Create minimal reminder", "Only title, no other fields")
    except Exception as e:
        results.add_fail("Create minimal reminder", e)

    # Reminder with due date only
    try:
        title = f"MCP TEST DUE DATE: {cst_timestamp}"
        due_date = datetime.now() + timedelta(hours=2)
        reminder = rk.create_reminder(title=title, due_date=due_date)
        created_ids.append(reminder.id)
        assert reminder.title == title
        assert reminder.due_date is not None
        results.add_pass(
            "Create reminder with due date only",
            f"Due: {due_date.strftime('%Y-%m-%d %H:%M')}",
        )
    except Exception as e:
        results.add_fail("Create reminder with due date only", e)

    # High priority reminder
    try:
        title = f"MCP TEST HIGH PRIORITY: {cst_timestamp}"
        reminder = rk.create_reminder(title=title, priority=9)
        created_ids.append(reminder.id)
        assert reminder.priority == 9
        results.add_pass("Create high priority reminder", "Priority set to 9 (High)")
    except Exception as e:
        results.add_fail("Create high priority reminder", e)

    # Reminder with URL only
    try:
        title = f"MCP TEST URL: {cst_timestamp}"
        reminder = rk.create_reminder(
            title=title,
            url="https://github.com/anthropics/claude-code",
        )
        created_ids.append(reminder.id)
        assert reminder.url is not None
        results.add_pass("Create reminder with URL", reminder.url)
    except Exception as e:
        results.add_fail("Create reminder with URL", e)

    # Create in specific calendar (if multiple available)
    try:
        calendars = list(rk.calendars.list())
        if len(calendars) > 1:
            target_cal = calendars[1]
            title = f"MCP TEST SPECIFIC LIST: {cst_timestamp}"
            reminder = rk.create_reminder(title=title, calendar_id=target_cal.id)
            created_ids.append(reminder.id)
            assert reminder.list_id == target_cal.id
            results.add_pass("Create in specific calendar", f"Created in '{target_cal.name}'")
        else:
            results.add_skip("Create in specific calendar", "Only one calendar available")
    except Exception as e:
        results.add_fail("Create in specific calendar", e)

    return created_ids
