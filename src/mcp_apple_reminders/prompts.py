"""MCP Prompts for ADHD-friendly task workflows.

Prompts are curated, named conversation starters the client can surface
to the user (e.g. as slash commands). Each one is a multi-step recipe
that uses the underlying tools — so the LLM follows a known-good script
instead of figuring it out from scratch every time.
"""

from __future__ import annotations

from mcp.server.fastmcp.prompts.base import Message, UserMessage

from .server import mcp


@mcp.prompt(description="Plan today: triage overdue, surface today's items, pick the top 3 to focus on.")
def plan_my_day() -> list[Message]:
    return [
        UserMessage(
            "Help me plan my day. Use the apple-reminders tools to:\n"
            "1. Call `workflow_status` for a kanban snapshot.\n"
            "2. Call `get_overdue_reminders(limit=10)` and surface anything urgent.\n"
            "3. Call `get_today_reminders()` for what's due today.\n"
            "4. Recommend exactly 3 items to put in the Active list and explain why "
            "those three (consider priority, due date, and energy/context fit).\n"
            "5. Offer to move them with `move_reminder_active` once I confirm.\n\n"
            "Be concise. Lead with the recommendation, not the data dump."
        ),
    ]


@mcp.prompt(description="Triage the inbox: identify orphan reminders and propose homes for each.")
def triage_inbox() -> list[Message]:
    return [
        UserMessage(
            "Triage my reminders inbox. Use the apple-reminders tools to:\n"
            "1. Call `get_default_calendar` to find the default list.\n"
            "2. Call `get_reminders(calendar_id=<default_id>, is_completed=False, limit=50)`.\n"
            "3. For each item, propose ONE of: keep here, move to On-Deck, move to Blocked, "
            "delete (looks stale), or rename (if the title is too vague).\n"
            "4. Group your suggestions by action so I can approve them in batches.\n"
            "5. After I approve, execute the moves with `move_reminder_*` and "
            "`batch_delete_reminders` as appropriate."
        ),
    ]


@mcp.prompt(description="Weekly review: summarize done, surface stale items, retire what shouldn't be active.")
def weekly_review() -> list[Message]:
    return [
        UserMessage(
            "Run my weekly review. Use the apple-reminders tools to:\n"
            "1. Call `workflow_status`.\n"
            "2. Summarize what's in Done since last week (use `get_reminders` with the Done list).\n"
            "3. Find Active items I haven't touched in 7+ days (consider modified_date) "
            "and ask whether each should stay Active, move to Blocked, or move back to On-Deck.\n"
            "4. Find Blocked items and ask what's still blocking each — propose unblock or close.\n"
            "5. End with a one-sentence theme for the upcoming week."
        ),
    ]


@mcp.prompt(description="Quick capture a brain-dump: parse a list of items into reminders with smart defaults.")
def quick_capture(items: str) -> list[Message]:
    """Args:
    items: Free-text list of things to capture. Newline-, comma-, or
        bullet-separated all work.
    """
    return [
        UserMessage(
            f"I want to capture the following items as reminders:\n\n{items}\n\n"
            "Parse them into individual reminder titles. For each, suggest a list "
            "(Inbox = default, On-Deck if I'll start soon, Blocked if it's waiting on someone). "
            "Use `batch_create_reminders` for the inbox dump, then `move_reminder_*` for "
            "the items that need a different home. Confirm the plan before executing."
        ),
    ]


@mcp.prompt(description="Defer items to 'someday' so they're out of the way without being lost.")
def defer_to_someday() -> list[Message]:
    return [
        UserMessage(
            "I want to defer some active reminders to 'Someday' so they stop nagging me. "
            "Show me everything currently in Active and On-Deck. For each, ask whether to "
            "(a) keep, (b) move to Blocked with a reason, or (c) defer to Someday — "
            "which I'll set up by giving it a due_date 6 months out and moving to On-Deck. "
            "Use `update_reminder` to push the date, then `move_reminder_on_deck`."
        ),
    ]


@mcp.prompt(description="Snooze a specific reminder by pushing its due date forward.")
def snooze(reminder_title_or_id: str, until: str = "tomorrow") -> list[Message]:
    """Args:
    reminder_title_or_id: Either a reminder ID or a fragment of its title.
    until: Free-text when to snooze until — "tomorrow", "next week", "2024-01-20".
    """
    return [
        UserMessage(
            f"Snooze the reminder matching '{reminder_title_or_id}' until {until}. "
            "If a title fragment is given, call `search_reminders` first and confirm "
            "the match before updating. Use `update_reminder(due_date=...)` with an "
            "ISO 8601 timestamp."
        ),
    ]
