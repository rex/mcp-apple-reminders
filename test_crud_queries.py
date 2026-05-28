"""Query / filter / search test surface.

Exercises every read-only query the RemindKit client exposes:
`get_next_reminder`, `get_reminders` with date/completion filters,
`search_reminders`. Does not create or modify any reminders.
"""

from __future__ import annotations

from datetime import datetime, timedelta


def test_query_operations(rk, results):
    """Run the full query/filter surface and record pass/fail."""
    print("\n" + "=" * 70)
    print("TESTING QUERY OPERATIONS")
    print("=" * 70)

    # Next upcoming reminder
    try:
        next_reminder = rk.get_next_reminder()
        if next_reminder:
            results.add_pass(
                "Get next reminder",
                f"'{next_reminder.title}' due {next_reminder.due_date}",
            )
        else:
            results.add_pass("Get next reminder", "No upcoming reminders")
    except Exception as e:
        results.add_fail("Get next reminder", e)

    # Overdue (incomplete + due before now)
    try:
        overdue = list(rk.get_reminders(due_before=datetime.now(), is_completed=False))
        results.add_pass("Get overdue reminders", f"Found {len(overdue)} overdue reminder(s)")
    except Exception as e:
        results.add_fail("Get overdue reminders", e)

    # Completed reminders
    try:
        completed = list(rk.get_reminders(is_completed=True))
        results.add_pass("Get completed reminders", f"Found {len(completed)} completed reminder(s)")
    except Exception as e:
        results.add_fail("Get completed reminders", e)

    # Incomplete reminders
    try:
        incomplete = list(rk.get_reminders(is_completed=False))
        results.add_pass("Get incomplete reminders", f"Found {len(incomplete)} incomplete reminder(s)")
    except Exception as e:
        results.add_fail("Get incomplete reminders", e)

    # Next 7 days
    try:
        week_from_now = datetime.now() + timedelta(days=7)
        upcoming = list(
            rk.get_reminders(
                due_after=datetime.now(),
                due_before=week_from_now,
                is_completed=False,
            )
        )
        results.add_pass("Get reminders due in next 7 days", f"Found {len(upcoming)} upcoming reminder(s)")
    except Exception as e:
        results.add_fail("Get reminders due in next 7 days", e)

    # Substring search
    try:
        search_results = list(rk.search_reminders("MCP TEST"))
        results.add_pass(
            "Search by partial text",
            f"Found {len(search_results)} result(s) matching 'MCP TEST'",
        )
    except Exception as e:
        results.add_fail("Search by partial text", e)
