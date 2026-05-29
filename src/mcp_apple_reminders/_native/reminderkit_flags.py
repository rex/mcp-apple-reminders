"""Typed wrappers for ReminderKit reminder-attribute helper actions.

Urgent flag, Early Reminder delta alerts, and create-section-and-assign. Thin
typed calls over the shared `reminderkit._invoke` transport. Separate native
wrapper module to respect the 8-public-entry-point cap.
"""

from __future__ import annotations

from typing import Optional

from .reminderkit import _invoke


def set_urgent(reminder_id: str, urgent: bool) -> dict:
    """Toggle the 'urgent' state on a reminder (the Reminders.app urgency flag)."""
    if not reminder_id or not reminder_id.strip():
        raise ValueError("reminder_id is required and must be non-empty")
    return _invoke({"action": "set_urgent", "id": reminder_id, "urgent": bool(urgent)})


def set_early_reminder(
    reminder_id: str,
    *,
    unit: Optional[int] = None,
    count: Optional[int] = None,
    clear: bool = False,
) -> dict:
    """Set or clear an Early Reminder (a lead-time alert before the due date).

    `unit`: 0=minutes, 1=hours, 2=days, 3=weeks, 4=months. `count`: how many
    units before due (non-zero). Pass `clear=True` to remove early reminders.
    """
    if not reminder_id or not reminder_id.strip():
        raise ValueError("reminder_id is required and must be non-empty")
    if clear:
        return _invoke({"action": "set_early_reminder", "id": reminder_id, "clear": True})
    if unit is None or count is None:
        raise ValueError("unit and count are required unless clear=True")
    if not 0 <= unit <= 4:
        raise ValueError("unit must be 0-4 (0=minutes, 1=hours, 2=days, 3=weeks, 4=months)")
    if count == 0:
        raise ValueError("count cannot be 0")
    return _invoke({"action": "set_early_reminder", "id": reminder_id, "unit": int(unit), "count": int(count)})


def add_section_and_assign(reminder_id: str, section_name: str) -> dict:
    """Create a section in the reminder's parent list and move the reminder into it."""
    if not reminder_id or not reminder_id.strip():
        raise ValueError("reminder_id is required and must be non-empty")
    if not section_name or not section_name.strip():
        raise ValueError("section_name is required and must be non-empty")
    return _invoke({"action": "add_section_and_assign", "id": reminder_id, "name": section_name})
