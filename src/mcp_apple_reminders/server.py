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
from .tools import appearance as _appearance  # noqa: E402, F401
from .tools import bulk as _bulk  # noqa: E402, F401
from .tools import calendars as _calendars  # noqa: E402, F401
from .tools import groups as _groups  # noqa: E402, F401
from .tools import queries as _queries  # noqa: E402, F401
from .tools import reminders as _reminders  # noqa: E402, F401
from .tools import sampling as _sampling  # noqa: E402, F401
from .tools import sections as _sections  # noqa: E402, F401
from .tools import smartlists as _smartlists  # noqa: E402, F401
from .tools import templates as _templates  # noqa: E402, F401
from .tools import workflow as _workflow  # noqa: E402, F401


def _resolve_transport() -> str:
    """Pick the transport.

    Reads `MCP_APPLE_REMINDERS_TRANSPORT` from the environment first, then
    falls back to the `server.transport` field in `VIBE.yaml` if present.
    Default: `stdio`. Recognized values: `stdio`, `sse`, `streamable_http`.

    Note on `streamable_http`: per the MCP spec, the server boots a small
    HTTP listener and accepts MCP requests there. Clients that don't speak
    HTTP will fail to connect; the default `stdio` remains correct for
    Claude Desktop, Claude Code, and Codex.
    """
    import os

    env = os.environ.get("MCP_APPLE_REMINDERS_TRANSPORT")
    if env:
        return env.strip().lower()
    # Best-effort VIBE.yaml lookup. Failures fall back to stdio.
    try:
        from pathlib import Path

        import yaml

        repo_vibe = Path(__file__).resolve().parents[2] / "VIBE.yaml"
        if repo_vibe.exists():
            data = yaml.safe_load(repo_vibe.read_text()) or {}
            transport = ((data.get("server") or {}).get("transport") or "stdio").strip().lower()
            return transport
    except Exception:
        pass
    return "stdio"


def cli_main() -> int:
    """Synchronous entry point for the console-script wrapper.

    Transport selection: `MCP_APPLE_REMINDERS_TRANSPORT` env var > `VIBE.yaml
    ::server.transport` field > `stdio` default.
    """
    transport_raw = _resolve_transport()
    # FastMCP's `run()` is typed against a Literal of valid transport names.
    # Normalize and narrow with explicit branches so mypy is happy and
    # unknown values fall through to stdio rather than crashing the client
    # startup path.
    if transport_raw == "sse":
        mcp.run(transport="sse")
    elif transport_raw in ("streamable_http", "streamable-http"):
        mcp.run(transport="streamable-http")
    else:
        mcp.run(transport="stdio")
    return 0


if __name__ == "__main__":
    raise SystemExit(cli_main())
