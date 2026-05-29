"""MCP Apple Reminders Server — FastMCP edition (post-S0.4).

Thin top-level orchestrator that:
1. Builds a `FastMCP` instance with the lifespan that owns the RemindKit
   bridge.
2. Imports the per-category tool modules — each module decorates its tools
   with `@mcp.tool()`, registering them at import time.
3. Runs the server over stdio (default) when invoked as a script.

All tool definitions and per-tool handlers live in `tools/<category>.py`. Format
helpers (datetime + priority parsing) live in `formatting.py`. The single
`RemindKit` instance lives in `lifespan.py`.
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from .lifespan import app_lifespan

mcp = FastMCP(
    "mcp-apple-reminders",
    instructions=(
        "Access Apple Reminders on macOS. Use list_calendars to discover "
        "lists, get_reminders / search_reminders / get_today_reminders / "
        "get_overdue_reminders to query, create_reminder / update_reminder "
        "/ complete_reminder / delete_reminder to manage individual items, "
        "and the move_reminder_* family to organize via Pierce's Claude-* "
        "workflow lists."
    ),
    lifespan=app_lifespan,
)


# Register every tool at import time. The per-category modules decorate
# their handlers with `@mcp.tool()` at module-load — importing them is
# what wires them up.
from .prompts import workflows as _prompts_workflows  # noqa: E402, F401
from .resources import agents as _resources_agents  # noqa: E402, F401
from .resources import reminders as _resources_reminders  # noqa: E402, F401
from .tools import agents as _agents_tool  # noqa: E402, F401
from .tools import alarms as _alarms  # noqa: E402, F401
from .tools import bulk as _bulk  # noqa: E402, F401
from .tools import calendars as _calendars  # noqa: E402, F401
from .tools import queries as _queries  # noqa: E402, F401
from .tools import reminders as _reminders  # noqa: E402, F401
from .tools import sampling as _sampling  # noqa: E402, F401
from .tools import sections as _sections  # noqa: E402, F401
from .tools import workflow as _workflow  # noqa: E402, F401


def cli_main() -> int:
    """Synchronous entry point for the console-script wrapper."""
    mcp.run(transport="stdio")
    return 0


if __name__ == "__main__":
    raise SystemExit(cli_main())
