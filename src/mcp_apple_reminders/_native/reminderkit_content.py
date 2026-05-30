"""Typed wrappers for ReminderKit template + grocery helper actions.

Separate native wrapper module to respect the 8-public-entry-point cap. Thin
typed calls over the shared `reminderkit._invoke` transport (per-call subprocess
to the compiled Obj-C `rem_reminderkit` helper).
"""

from __future__ import annotations

from typing import Optional

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


def categorize_grocery_items(list_id: str, reminder_ids: list[str]) -> dict:
    """Auto-categorize grocery reminders (produce, dairy, …) in a grocery-enabled list."""
    if not list_id or not list_id.strip():
        raise ValueError("list_id is required and must be non-empty")
    if not reminder_ids:
        raise ValueError("reminder_ids must be a non-empty list")
    return _invoke({"action": "categorize_grocery_items", "listId": list_id, "reminderIds": list(reminder_ids)})


def add_url_attachments(reminder_id: str, urls: list[str]) -> dict:
    """Attach one or more web URLs to a reminder (additive)."""
    if not reminder_id or not reminder_id.strip():
        raise ValueError("reminder_id is required and must be non-empty")
    cleaned = [u for u in (urls or []) if u and u.strip()]
    if not cleaned:
        raise ValueError("urls must contain at least one non-empty value")
    return _invoke({"action": "add_url_attachments", "id": reminder_id, "urls": cleaned})


def add_private_metadata(
    reminder_id: str,
    *,
    urls: Optional[list[str]] = None,
    tags: Optional[list[str]] = None,
) -> dict:
    """Attach web URLs and/or hashtags to a reminder (additive)."""
    if not reminder_id or not reminder_id.strip():
        raise ValueError("reminder_id is required and must be non-empty")
    cleaned_urls = [u for u in (urls or []) if u and u.strip()]
    cleaned_tags = [t for t in (tags or []) if t and t.strip()]
    if not cleaned_urls and not cleaned_tags:
        raise ValueError("at least one URL or tag is required")
    return _invoke({"action": "add_private_metadata", "id": reminder_id, "urls": cleaned_urls, "tags": cleaned_tags})


def add_file_attachments(
    reminder_id: str,
    *,
    files: Optional[list[str]] = None,
    images: Optional[list[str]] = None,
) -> dict:
    """Attach local files and/or images to a reminder by path (additive).

    `files` use ReminderKit's generic file attachment; `images` render with a
    thumbnail. The caller MUST validate/authorize every path before calling.
    """
    if not reminder_id or not reminder_id.strip():
        raise ValueError("reminder_id is required and must be non-empty")
    cleaned_files = [f for f in (files or []) if f and f.strip()]
    cleaned_images = [i for i in (images or []) if i and i.strip()]
    if not cleaned_files and not cleaned_images:
        raise ValueError("at least one file or image path is required")
    payload: dict = {"action": "add_attachments", "id": reminder_id}
    if cleaned_files:
        payload["files"] = cleaned_files
    if cleaned_images:
        payload["images"] = cleaned_images
    return _invoke(payload)
