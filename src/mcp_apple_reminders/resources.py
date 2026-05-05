"""MCP Resources for Apple Reminders.

Resources let agents browse reminders data via stable URIs without spending
tool turns. We expose three URI shapes:

- ``apple-reminders://lists``
    A JSON array of all reminder lists.
- ``apple-reminders://list/{list_id}``
    A JSON envelope containing the list and all open reminders in it.
- ``apple-reminders://reminder/{reminder_id}``
    A single reminder, by ID.

The resources are read-only; mutations always go through tools so the LLM
sees an explicit acknowledgement.
"""

from __future__ import annotations

import json
from typing import Any

from ._models import calendar_from_obj, reminder_from_obj
from .server import _remindkit, mcp


@mcp.resource("apple-reminders://lists")
def list_all_lists() -> str:
    """All reminder lists, as a JSON array."""
    cals = [calendar_from_obj(c).model_dump(mode="json") for c in _remindkit().calendars.list()]
    return json.dumps({"lists": cals, "count": len(cals)}, indent=2)


@mcp.resource("apple-reminders://list/{list_id}")
def list_resource(list_id: str) -> str:
    """A single list and its open reminders.

    Args:
        list_id: The unique identifier of the list.
    """
    rk = _remindkit()
    cal = calendar_from_obj(rk.calendars.get_by_id(list_id))
    items: list[dict[str, Any]] = [
        reminder_from_obj(r).model_dump(mode="json") for r in rk.get_reminders(calendar_id=list_id, is_completed=False)
    ]
    return json.dumps(
        {"list": cal.model_dump(mode="json"), "reminders": items, "count": len(items)},
        indent=2,
        default=str,
    )


@mcp.resource("apple-reminders://reminder/{reminder_id}")
def reminder_resource(reminder_id: str) -> str:
    """A single reminder by ID, serialized as JSON."""
    item = reminder_from_obj(_remindkit().get_reminder_by_id(reminder_id))
    return json.dumps(item.model_dump(mode="json"), indent=2, default=str)
