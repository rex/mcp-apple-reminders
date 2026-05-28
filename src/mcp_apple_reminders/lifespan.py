"""FastMCP lifespan + shared bridge context.

The single `RemindKit` instance lives here, owned by the lifespan context
manager. Every tool handler accesses it through `ctx.request_context.lifespan_context.bridge`.

This is the post-S0.4 substitute for the module-level `remind = RemindKit()`
in the pre-FastMCP server.py: one place to fail fast on permission errors,
one place to inject a fake bridge for tests.
"""

from __future__ import annotations

import sys
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import TYPE_CHECKING, AsyncIterator

from ._native import RemindKit

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP


@dataclass
class AppContext:
    """The lifespan-owned context handed to every tool through `ctx.request_context.lifespan_context`."""

    bridge: RemindKit


@asynccontextmanager
async def app_lifespan(server: "FastMCP") -> AsyncIterator[AppContext]:
    """Build the `RemindKit` bridge once at server start; clean up on stop.

    On macOS the underlying EventKit init triggers the Reminders permission
    prompt the first time a never-prompted interpreter binary runs. If the
    user denies, `PermissionError` is raised and the server exits 1 — there
    is no MCP session yet to log through, so we route the message through
    stderr (the only legal pre-session diagnostic channel).
    """
    try:
        bridge = RemindKit()
    except PermissionError:
        print(
            "Error: Unable to access Apple Reminders. Please grant permissions in "
            "System Settings > Privacy & Security > Reminders.",
            file=sys.stderr,
        )
        sys.exit(1)
    except Exception as e:  # pragma: no cover — pre-session crash path
        print(f"Error initializing RemindKit: {e}", file=sys.stderr)
        sys.exit(1)

    try:
        yield AppContext(bridge=bridge)
    finally:
        # `_native` has no explicit shutdown hook (the EKEventStore is GC'd).
        # Hook reserved for future helper-subprocess teardown (S0.6+).
        pass


__all__ = ["AppContext", "app_lifespan"]
