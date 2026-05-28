"""MCP tool registry.

Aggregates per-category tool definitions and handlers into the two flat
collections the server's `list_tools()` and `call_tool()` dispatchers consume:

- `ALL_TOOLS: list[Tool]` — every tool schema, in canonical category order.
- `ALL_HANDLERS: dict[str, Handler]` — name → handler callable.

Each handler has signature `(arguments: dict, remind: RemindKit) -> list[TextContent]`.
The server wraps the call in a single `try/except` so handlers can raise
`ValueError` for user errors or any other exception for runtime errors.
"""

from __future__ import annotations

from . import calendars, queries, reminders, workflow

ALL_TOOLS = calendars.TOOLS + reminders.TOOLS + queries.TOOLS + workflow.TOOLS

ALL_HANDLERS = {
    **calendars.HANDLERS,
    **reminders.HANDLERS,
    **queries.HANDLERS,
    **workflow.HANDLERS,
}

__all__ = ["ALL_TOOLS", "ALL_HANDLERS"]
