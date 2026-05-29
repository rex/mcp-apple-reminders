"""Four canned MCP Prompts — Slice 2.2.

Each prompt builds a `list[base.Message]` from the live SQLite store so the
agent can act immediately. Prompts are conceptually frozen workflows that
clients can invoke by name; they're how the spec's "agent visibility
plane" shows up to the user.

The four:

- `daily_review` — quick AM/PM review of today + overdue.
- `weekly_retro` — last 7 days' completed + still-open.
- `brain_dump_triage` — pull from a Claude-Brain-Dump list and route.
- `agent_visibility_sync` — surface the Agents-<project> list for sync.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from mcp.server.fastmcp.prompts import base

from .._native.sqlite import Reader, RemindersDBUnavailable, connect
from ..server import mcp


def _bullet_list(reminders: list, *, empty_note: str = "(none)") -> str:
    if not reminders:
        return empty_note
    lines = []
    for r in reminders:
        due = f" — due {r.due_date:%Y-%m-%d %H:%M}" if r.due_date else ""
        flag = " ⚐" if r.flagged else ""
        lines.append(f"- {r.title}{due}{flag} ({r.deeplink})")
    return "\n".join(lines)


@mcp.prompt(
    name="daily_review",
    description=(
        "Quick AM/PM review prompt: surfaces today's reminders + everything "
        "overdue, plus a brief agenda for triage. Reads live from SQLite."
    ),
)
def daily_review() -> list[base.Message]:
    """Build the daily review prompt messages."""
    now = datetime.now()
    start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end_of_day = now.replace(hour=23, minute=59, second=59, microsecond=999999)
    try:
        with connect() as conn:
            reader = Reader(conn)
            today = list(
                reader.iter_reminders(
                    completed=False,
                    due_after=start_of_day,
                    due_before=end_of_day,
                )
            )
            overdue = list(reader.iter_reminders(completed=False, due_before=start_of_day))
    except RemindersDBUnavailable as e:
        return [base.UserMessage(f"Daily review unavailable — SQLite read failed: {e}")]

    body = (
        f"# Daily Review — {now:%Y-%m-%d %H:%M}\n\n"
        f"## Due today ({len(today)})\n{_bullet_list(today)}\n\n"
        f"## Overdue ({len(overdue)})\n{_bullet_list(overdue)}\n\n"
        f"### Triage plan\n"
        f"For each overdue item, decide: complete now, reschedule, delegate, or delete.\n"
        f"For today's items, identify the **one** that must be done first."
    )
    return [
        base.UserMessage(
            "Run my morning review. I want a clean picture of what's overdue and what's due today, "
            "with a recommended order of operations."
        ),
        base.AssistantMessage(body),
    ]


@mcp.prompt(
    name="weekly_retro",
    description=("Weekly retro: last 7 days of completed work + still-open items. " "Reads live from SQLite."),
)
def weekly_retro(window_days: int = 7) -> list[base.Message]:
    """Build a weekly-retro prompt; window_days defaults to 7."""
    now = datetime.now()
    window_start = now - timedelta(days=int(window_days))
    try:
        with connect() as conn:
            reader = Reader(conn)
            completed = list(reader.iter_reminders(completed=True, due_after=window_start))
            open_now = list(reader.iter_reminders(completed=False))
    except RemindersDBUnavailable as e:
        return [base.UserMessage(f"Weekly retro unavailable — SQLite read failed: {e}")]

    body = (
        f"# Weekly Retro — last {window_days} day(s)\n\n"
        f"## Completed ({len(completed)})\n{_bullet_list(completed)}\n\n"
        f"## Still open ({len(open_now)})\n{_bullet_list(open_now, empty_note='Clean — nothing open. 🚀')}\n\n"
        f"### Retro questions\n"
        f"1. What went well?\n"
        f"2. What slipped, and why?\n"
        f"3. What's the single biggest blocker on the open list?"
    )
    return [
        base.UserMessage(
            "Lead me through a weekly retro. Show me what landed in the last week and what's still on my plate."
        ),
        base.AssistantMessage(body),
    ]


@mcp.prompt(
    name="brain_dump_triage",
    description=(
        "Pull every reminder from the `Claude-Brain-Dump` list and propose "
        "where each one should go (active / on-deck / waiting / done)."
    ),
)
def brain_dump_triage(list_name: str = "Claude-Brain-Dump") -> list[base.Message]:
    """Surface every Brain Dump item for routing."""
    try:
        with connect() as conn:
            reader = Reader(conn)
            cal = reader.get_calendar_by_name(list_name)
            if cal is None:
                return [
                    base.UserMessage(
                        f"List {list_name!r} not found. Create it in Apple Reminders first, "
                        f"or pass `list_name=` with an existing list."
                    )
                ]
            items = list(reader.iter_reminders(calendar_id=cal.id, completed=False))
    except RemindersDBUnavailable as e:
        return [base.UserMessage(f"Brain-dump triage unavailable — SQLite read failed: {e}")]

    body = (
        f"# Brain Dump Triage — {list_name}\n\n"
        f"## Items to route ({len(items)})\n{_bullet_list(items, empty_note='Brain Dump is empty.')}\n\n"
        f"### Routing options\n"
        f"For each item, propose the destination list and reasoning:\n"
        f"- `Claude-Active`: working on it now\n"
        f"- `Claude-On-Deck`: queued for the next session\n"
        f"- `Claude-Waiting`: blocked by external input\n"
        f"- `Claude-Done`: actually already finished\n"
        f"- Delete: not worth doing"
    )
    return [
        base.UserMessage("Triage my brain dump and propose where each item should go."),
        base.AssistantMessage(body),
    ]


@mcp.prompt(
    name="agent_visibility_sync",
    description=(
        "Surface the `Agents-<project>` reminder list so the agent can sync "
        "its current todos there. Pass `project_name` to target a specific list."
    ),
)
def agent_visibility_sync(project_name: str) -> list[base.Message]:
    """Surface the project's Agents-* list for a sync round-trip."""
    list_name = f"Agents-{project_name}"
    try:
        with connect() as conn:
            reader = Reader(conn)
            cal = reader.get_calendar_by_name(list_name)
            items: list = []
            if cal is not None:
                items = list(reader.iter_reminders(calendar_id=cal.id))
    except RemindersDBUnavailable as e:
        return [base.UserMessage(f"Visibility sync unavailable — SQLite read failed: {e}")]

    if cal is None:
        body = (
            f"# Agents Visibility — {list_name}\n\n"
            f"List `{list_name}` does not exist yet. "
            f"Run `create_calendar(name={list_name!r}, color='gray')` to bootstrap it, "
            f"then re-invoke this prompt to surface the state."
        )
    else:
        body = (
            f"# Agents Visibility — {list_name}\n\n"
            f"## Current state ({len(items)} item(s))\n{_bullet_list(items, empty_note='List is empty.')}\n\n"
            f"### Sync plan\n"
            f"Compare each item to your in-memory todo list. For each: create, update, mark complete, or delete."
        )

    return [
        base.UserMessage(f"Sync your current todos into `{list_name}` so the user can see what you're working on."),
        base.AssistantMessage(body),
    ]
