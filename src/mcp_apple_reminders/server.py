"""MCP Apple Reminders Server — orchestration.

Thin top-level orchestrator that:
1. Bootstraps the vendored `pyremindkit` import path.
2. Instantiates `RemindKit` (triggering the macOS Reminders permission prompt
   on first run).
3. Registers the aggregated tool list from `tools/` against the MCP server.
4. Dispatches `call_tool` invocations to the matching handler.

All tool definitions and per-tool handlers live in `tools/<category>.py`. Format
helpers live in `formatting.py`. This module stays small on purpose.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

# Add the vendored pyremindkit library to sys.path before any pyremindkit import.
# Path is derived from this file's location so the repo can be moved freely.
_current_file = Path(__file__).resolve()
_project_root = _current_file.parent.parent.parent
_pyremindkit_path = _project_root / "libs" / "pyremindkit" / "src"
sys.path.insert(0, str(_pyremindkit_path))

import mcp.server.stdio  # noqa: E402
from mcp.server import Server  # noqa: E402
from mcp.types import TextContent, Tool  # noqa: E402
from pyremindkit import RemindKit  # noqa: E402  (must follow sys.path tweak)

from .tools import ALL_HANDLERS, ALL_TOOLS  # noqa: E402

# Initialize the RemindKit instance. Raises PermissionError on first run if
# the user denies the macOS Reminders permission dialog.
try:
    remind = RemindKit()
except PermissionError:
    print(
        "Error: Unable to access Apple Reminders. Please grant permissions in "
        "System Settings > Privacy & Security > Reminders.",
        file=sys.stderr,
    )
    sys.exit(1)
except Exception as e:
    print(f"Error initializing RemindKit: {e}", file=sys.stderr)
    sys.exit(1)


app = Server("mcp-apple-reminders")


@app.list_tools()
async def list_tools() -> list[Tool]:
    """Return every tool registered by the per-category modules."""
    return ALL_TOOLS


@app.call_tool()
async def call_tool(name: str, arguments: Any) -> list[TextContent]:
    """Dispatch a tool invocation to the matching handler.

    All handlers share the signature `(arguments, remind) -> list[TextContent]`.
    User-visible errors (bad inputs, lookup misses) are caught and returned as
    text content; everything else surfaces as `Error executing <name>: ...`.
    """
    handler = ALL_HANDLERS.get(name)
    if handler is None:
        return [TextContent(type="text", text=f"Error: Unknown tool: {name}")]

    try:
        return handler(arguments, remind)
    except ValueError as e:
        return [TextContent(type="text", text=f"Error: {str(e)}")]
    except Exception as e:
        return [TextContent(type="text", text=f"Error executing {name}: {str(e)}")]


async def main() -> None:
    """Run the MCP server over stdio. Entry point invoked by `cli_main`."""
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


def cli_main() -> int:
    """Synchronous entry point for the console-script wrapper."""
    import asyncio

    asyncio.run(main())
    return 0


if __name__ == "__main__":
    raise SystemExit(cli_main())
