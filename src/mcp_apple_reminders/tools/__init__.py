"""MCP tool registry (FastMCP edition).

Importing this package (or its submodules) registers all tools against the
shared `mcp_apple_reminders.server.mcp` FastMCP instance via the `@mcp.tool()`
decorators at module scope. FastMCP owns the registry directly — there is no
`ALL_TOOLS` / `ALL_HANDLERS` aggregation and no low-level `call_tool` dispatch.

Layout:
- `calendars.py` — calendar lifecycle + list/get/search tools.
- `reminders.py` — CRUD + complete/uncomplete tools.
- `queries.py` — filter/search/today/overdue/next/completed-range tools.
- `workflow.py` — Claude-* workflow-list move + lookup tools.
- `groups.py` — list-group (sidebar folder) tools.
- `alarms.py` — time/location alarm + recurrence tools.
- `bulk.py` — bulk complete/move/delete-completed tools.
- `sections.py` — subtask/parent/section tools.
- `smartlists.py` — custom smart-list create/update/delete + pin tools.
- `appearance.py` — list/group appearance + pinning tools.
- `templates.py` / `grocery.py` / `flags.py` — template, grocery, flag/extra tools.
- `agents.py` — agent-visibility bootstrap tool.
- `sampling.py` — sampling-backed triage tool.
"""

from __future__ import annotations

# Re-export the per-category modules so callers can introspect what's wired up.
from . import (
    agents,
    alarms,
    appearance,
    attachments,
    bulk,
    calendars,
    flags,
    grocery,
    groups,
    queries,
    reminders,
    sampling,
    sections,
    smartlists,
    templates,
    workflow,
)

__all__ = [
    "agents",
    "alarms",
    "appearance",
    "attachments",
    "bulk",
    "calendars",
    "flags",
    "grocery",
    "groups",
    "queries",
    "reminders",
    "sampling",
    "sections",
    "smartlists",
    "templates",
    "workflow",
]
