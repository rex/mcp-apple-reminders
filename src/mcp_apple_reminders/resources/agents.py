"""Agent visibility-plane Resource — Slice 4.1.

Surfaces the current state of an `Agents-<project_name>` list to the
client. The client can fetch this without invoking a tool, which makes
it cheap to poll from a UI.

The URI template lets clients pin a specific project.
"""

from __future__ import annotations

import json

from .._native.sqlite import Reader, RemindersDBUnavailable, connect
from ..server import mcp

AGENT_LIST_PREFIX = "Agents-"


@mcp.resource(
    uri="agents://current/{project_name}",
    name="Agents visibility plane",
    title="Agents Visibility Plane",
    description=(
        "Live state of the `Agents-<project_name>` reminder list — the "
        "agent's mirrored todo board. Returns JSON: "
        '{"project": str, "list": Calendar|null, "todos": list[Reminder]}.'
    ),
    mime_type="application/json",
)
def agents_current(project_name: str) -> str:
    """Surface the project's Agents-* list state."""
    list_name = f"{AGENT_LIST_PREFIX}{project_name}"
    try:
        with connect() as conn:
            reader = Reader(conn)
            cal = reader.get_calendar_by_name(list_name)
            if cal is None:
                return json.dumps(
                    {
                        "project": project_name,
                        "list": None,
                        "todos": [],
                        "note": (
                            f"List {list_name!r} does not exist yet. Call "
                            f"`bootstrap_agent_list(project_name={project_name!r})` "
                            f"to create it."
                        ),
                    }
                )
            todos = list(reader.iter_reminders(calendar_id=cal.id))
            return json.dumps(
                {
                    "project": project_name,
                    "list": cal.model_dump(mode="json"),
                    "todos": [t.model_dump(mode="json") for t in todos],
                },
                default=str,
            )
    except RemindersDBUnavailable as e:
        return json.dumps({"project": project_name, "error": f"SQLite unavailable: {e}", "todos": []})
