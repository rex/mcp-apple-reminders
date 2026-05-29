"""MCP tool registry (post-S0.4 FastMCP edition).

Importing this package (or its submodules) registers all 22 tools against the
shared `mcp_apple_reminders.server.mcp` FastMCP instance via the `@mcp.tool()`
decorators at module scope.

There is no longer an `ALL_TOOLS` / `ALL_HANDLERS` aggregation — FastMCP owns
the registry directly. The pre-S0.4 dispatch path (`call_tool` + handler dict)
was removed alongside the low-level `Server` class.

Layout:
- `calendars.py` — 5 list/get/search/default tools.
- `reminders.py` — 6 CRUD + complete/uncomplete tools.
- `queries.py` — 5 filter/search/today/overdue/next tools.
- `workflow.py` — 6 Claude-* list lookup + move tools.
"""

from __future__ import annotations

# Re-export the per-category modules so callers can introspect what's wired up.
from . import calendars, queries, reminders, sections, workflow

__all__ = ["calendars", "queries", "reminders", "sections", "workflow"]
