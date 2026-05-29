"""Typed wrappers for ReminderKit list / smart-list / appearance helper actions.

Separate from `reminderkit_actions.py` to keep each native wrapper module under
the 8-public-entry-point architecture cap. Each wrapper is a thin typed call
over the shared `reminderkit._invoke` transport (per-call subprocess to the
compiled Obj-C `rem_reminderkit` helper).

Smart lists are Reminders.app's saved-filter lists. The filter predicate
(`filter_data_b64`) is an opaque base64-encoded blob in Reminders' internal
format; most callers create/name a smart list here and refine its filter in
Reminders.app, or pass a previously-captured blob.
"""

from __future__ import annotations

from typing import Optional

from .reminderkit import _invoke


def create_smart_list(
    name: str,
    *,
    color: Optional[str] = None,
    symbol: Optional[str] = None,
    emoji: Optional[str] = None,
    filter_data_b64: Optional[str] = None,
) -> dict:
    """Create a custom smart list. `filter_data_b64` is the optional opaque filter blob."""
    if not name or not name.strip():
        raise ValueError("name is required and must be non-empty")
    payload: dict = {"action": "create_smart_list", "name": name}
    if color:
        payload["color"] = color
    if symbol:
        payload["symbol"] = symbol
    if emoji:
        payload["emoji"] = emoji
    if filter_data_b64:
        payload["filterData"] = filter_data_b64
    return _invoke(payload)


def update_smart_list(
    smart_list_id: str,
    *,
    name: Optional[str] = None,
    color: Optional[str] = None,
    symbol: Optional[str] = None,
    emoji: Optional[str] = None,
    filter_data_b64: Optional[str] = None,
) -> dict:
    """Update a custom smart list's name, appearance, and/or filter blob."""
    if not smart_list_id or not smart_list_id.strip():
        raise ValueError("smart_list_id is required and must be non-empty")
    payload: dict = {"action": "update_smart_list", "smartListId": smart_list_id}
    if name:
        payload["name"] = name
    if color:
        payload["color"] = color
    if symbol:
        payload["symbol"] = symbol
    if emoji:
        payload["emoji"] = emoji
    if filter_data_b64:
        payload["filterData"] = filter_data_b64
    return _invoke(payload)


def delete_smart_list(smart_list_id: str) -> dict:
    """Permanently delete a custom smart list by its UUID."""
    if not smart_list_id or not smart_list_id.strip():
        raise ValueError("smart_list_id is required and must be non-empty")
    return _invoke({"action": "delete_smart_list", "smartListId": smart_list_id})
