"""Workflow-list naming convention and resolution.

The server exposes a small "kanban" workflow on top of Apple Reminders
using four lists named with a configurable prefix (default ``Claude-``):

    {prefix}On-Deck   queued for work
    {prefix}Active    currently in progress
    {prefix}Done      completed
    {prefix}Blocked   waiting on something

Override the prefix with the ``MCP_APPLE_REMINDERS_LIST_PREFIX`` env var.
"""

from __future__ import annotations

import os
from typing import Any, Literal

WorkflowRole = Literal["on_deck", "active", "done", "blocked"]

_DEFAULT_PREFIX = "Claude-"


def list_prefix() -> str:
    """The configured workflow-list prefix.

    Looked up at call time so tests can monkey-patch ``os.environ``.
    """
    return os.environ.get("MCP_APPLE_REMINDERS_LIST_PREFIX", _DEFAULT_PREFIX)


def workflow_list_name(role: WorkflowRole) -> str:
    """Apple-Reminders list name for a given workflow role."""
    suffix = {
        "on_deck": "On-Deck",
        "active": "Active",
        "done": "Done",
        "blocked": "Blocked",
    }[role]
    return f"{list_prefix()}{suffix}"


def all_workflow_names() -> list[str]:
    """All four workflow list names in stable role order."""
    return [workflow_list_name(role) for role in ("on_deck", "active", "done", "blocked")]


class WorkflowListMissingError(RuntimeError):
    """Raised when a workflow list isn't present in the Reminders database."""

    def __init__(self, role: WorkflowRole, expected_name: str) -> None:
        super().__init__(
            f"Workflow list {expected_name!r} (role: {role}) not found. "
            f"Create it in Apple Reminders, or set MCP_APPLE_REMINDERS_LIST_PREFIX "
            f"to match your existing list naming convention."
        )
        self.role = role
        self.expected_name = expected_name


def resolve_workflow_calendar(remind: Any, role: WorkflowRole) -> Any:
    """Look up the Calendar object for a workflow role, or raise.

    Single source of truth — replaces four near-identical lookup blocks in
    the legacy server. Calling code should catch ``WorkflowListMissingError``
    and surface a helpful error.
    """
    expected = workflow_list_name(role)
    matches = list(remind.calendars.search(expected))
    for cal in matches:
        if cal.name == expected:
            return cal
    if matches:  # prefix match but not exact — best-effort fallback
        return matches[0]
    raise WorkflowListMissingError(role, expected)
