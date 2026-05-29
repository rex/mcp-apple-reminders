"""MCP tool registry (FastMCP edition).

Importing this package (or its submodules) registers all 41 tools against the
shared `mcp_apple_reminders.server.mcp` FastMCP instance via the `@mcp.tool()`
decorators at module scope. FastMCP owns the registry directly — there is no
`ALL_TOOLS` / `ALL_HANDLERS` aggregation and no low-level `call_tool` dispatch.

Layout (10 modules):
- `calendars.py` — 8 calendar lifecycle + list/get/search tools.
- `reminders.py` — 6 CRUD + complete/uncomplete tools.
- `queries.py` — 6 filter/search/today/overdue/next/completed-range tools.
- `workflow.py` — 6 Claude-* workflow-list move + lookup tools.
- `groups.py` — 4 list-group (sidebar folder) tools.
- `alarms.py` — 3 time/location alarm + recurrence tools.
- `bulk.py` — 3 bulk complete/move/delete-completed tools.
- `sections.py` — 3 subtask/parent/section tools.
- `agents.py` — 1 agent-visibility bootstrap tool.
- `sampling.py` — 1 sampling-backed triage tool.
"""

from __future__ import annotations

# Re-export the per-category modules so callers can introspect what's wired up.
from . import (
    agents,
    alarms,
    appearance,
    bulk,
    calendars,
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
    "bulk",
    "calendars",
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
