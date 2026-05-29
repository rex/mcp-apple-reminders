"""Typed wrappers for ReminderKit template + grocery helper actions.

Separate native wrapper module to respect the 8-public-entry-point cap. Thin
typed calls over the shared `reminderkit._invoke` transport (per-call subprocess
to the compiled Obj-C `rem_reminderkit` helper).
"""

from __future__ import annotations

from .reminderkit import _invoke


def create_template(name: str, source_list_id: str, *, include_completed: bool = False) -> dict:
    """Save an existing list as a reusable template."""
    if not name or not name.strip():
        raise ValueError("name is required and must be non-empty")
    if not source_list_id or not source_list_id.strip():
        raise ValueError("source_list_id is required and must be non-empty")
    return _invoke(
        {
            "action": "create_template",
            "name": name,
            "listId": source_list_id,
            "includeCompleted": bool(include_completed),
        }
    )


def apply_template(template_id: str) -> dict:
    """Create a new list from a template. Returns the new list's id."""
    if not template_id or not template_id.strip():
        raise ValueError("template_id is required and must be non-empty")
    return _invoke({"action": "apply_template", "templateId": template_id})


def delete_template(template_id: str) -> dict:
    """Permanently delete a template by its UUID."""
    if not template_id or not template_id.strip():
        raise ValueError("template_id is required and must be non-empty")
    return _invoke({"action": "delete_template", "templateId": template_id})
