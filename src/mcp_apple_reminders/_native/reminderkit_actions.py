"""Typed per-action wrappers for the ReminderKit helper subprocess.

Split out of `_native/reminderkit.py` so each module stays under the
module-shape cap (max 8 public entry points). `reminderkit.py` owns the
protocol surface (`_invoke`, `ping`, `is_available`, exceptions); this
module owns the per-action public API consumed by tool handlers.

Every function here ultimately calls `_invoke()` from `reminderkit.py`
with a single `{"action": ..., ...}` payload.
"""

from __future__ import annotations

from typing import Any, Optional

from .reminderkit import _invoke


def create_subtask(parent_id: str, title: str, **extras: Any) -> dict:
    """Create one new subtask under `parent_id` via the `add_subtasks` action.

    Subtasks inherit the parent's list automatically. Additional kwargs flow
    through to the helper's per-subtask spec dict (e.g. `priority`).

    Raises:
        ValueError: blank input.
        ReminderKitHelperUnavailable / ReminderKitHelperError on helper failure.
    """
    if not parent_id or not parent_id.strip():
        raise ValueError("parent_id is required and must be non-empty")
    if not title or not title.strip():
        raise ValueError("title is required and must be non-empty")
    spec: dict[str, Any] = {"title": title, **extras}
    return _invoke({"action": "add_subtasks", "id": parent_id, "subtasks": [spec]})


def set_flagged(reminder_id: str, flagged: bool) -> dict:
    """Set the flagged flag on a reminder via the `set_flagged` action."""
    if not reminder_id or not reminder_id.strip():
        raise ValueError("reminder_id is required and must be non-empty")
    return _invoke({"action": "set_flagged", "id": reminder_id, "flagged": bool(flagged)})


def add_tags(reminder_id: str, tags: list[str]) -> dict:
    """Append tags to a reminder via the `add_tags` action (additive only).

    Existing tags are preserved. A `clear_tags` action will land in a
    follow-up patch to enable replacement semantics.

    Raises:
        ValueError: blank `reminder_id` or empty `tags` list.
    """
    if not reminder_id or not reminder_id.strip():
        raise ValueError("reminder_id is required and must be non-empty")
    cleaned = [t for t in (tags or []) if t and t.strip()]
    if not cleaned:
        raise ValueError("tags is required and must contain at least one non-empty value")
    return _invoke({"action": "add_tags", "id": reminder_id, "tags": cleaned})


def assign_section(reminder_id: str, section_id: str) -> dict:
    """Move a reminder into a section via the `assign_section` action.

    Resolve `section_id` via `Reader.list_sections_in_calendar`.
    """
    if not reminder_id or not reminder_id.strip():
        raise ValueError("reminder_id is required and must be non-empty")
    if not section_id or not section_id.strip():
        raise ValueError("section_id is required and must be non-empty")
    return _invoke({"action": "assign_section", "id": reminder_id, "sectionId": section_id})


def create_group(name: str) -> dict:
    """Create a Reminders.app list-group (ADR 0001 / S5.1).

    Mirrors `ZISGROUP=1` in the SQLite schema. Helper uses the private
    `REMListChangeItem.setIsGroup:` selector.
    """
    if not name or not name.strip():
        raise ValueError("name is required and must be non-empty")
    return _invoke({"action": "create_group", "name": name})


def move_list_to_group(list_id: str, group_id: Optional[str]) -> dict:
    """Reparent a list under a group, or detach back to the account root.

    Args:
        list_id: UUID of the child list.
        group_id: UUID of the target group, OR None to detach.

    Backed by the helper's `move_list_to_group` action, which uses the
    private `REMListChangeItem.setParentListID:` selector.
    """
    if not list_id or not list_id.strip():
        raise ValueError("list_id is required and must be non-empty")
    payload: dict[str, Any] = {"action": "move_list_to_group", "listId": list_id}
    if group_id:
        payload["groupId"] = group_id
    return _invoke(payload)


__all__ = [
    "add_tags",
    "assign_section",
    "create_group",
    "create_subtask",
    "move_list_to_group",
    "set_flagged",
]
