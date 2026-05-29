"""FastMCP lifespan + shared application context.

Two reader/writer surfaces live here, both owned by the lifespan:

1. `bridge` — the `RemindKit` (EventKit-backed) bridge. Single instance.
   Used as the fallback read path when SQLite is unavailable and as the
   primary write path until the Swift/Obj-C helpers come online in
   S1.2+ / S1.4+.

2. `sqlite_db_path` — the location of the active Reminders SQLite store,
   resolved once at startup. `app_context.open_sqlite()` returns a fresh
   read-only connection per call (cheap: <1 ms) so handlers can use it
   in a `with` block. Resolved-but-unopenable stores degrade to EventKit
   reads with a `ctx.warning(...)`.
"""

from __future__ import annotations

import sqlite3
import sys
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, AsyncIterator, Optional

from ._native import RemindKit
from ._native.sqlite import RemindersDBUnavailable, connect, find_db_path

if TYPE_CHECKING:
    from mcp.server.fastmcp import Context, FastMCP


@dataclass
class AppContext:
    """The lifespan-owned context handed to every tool via `ctx.request_context.lifespan_context`."""

    bridge: RemindKit
    sqlite_db_path: Optional[Path]

    def open_sqlite(self) -> sqlite3.Connection:
        """Open a fresh read-only SQLite connection.

        Raises `RemindersDBUnavailable` if no store was found at startup
        or the store can't be reopened. Tool handlers should catch this
        and degrade to `self.bridge` (EventKit) with a `ctx.warning(...)`.
        """
        if self.sqlite_db_path is None:
            raise RemindersDBUnavailable("Reminders SQLite store path not resolved at startup.")
        return connect(self.sqlite_db_path)


def app_context(ctx: Context) -> AppContext:
    """Return the lifespan-owned AppContext for a tool/resource Context."""
    return ctx.request_context.lifespan_context


def bridge_from_ctx(ctx: Context) -> RemindKit:
    """Return the RemindKit (EventKit) bridge from a tool/resource Context."""
    return ctx.request_context.lifespan_context.bridge


@asynccontextmanager
async def app_lifespan(server: "FastMCP") -> AsyncIterator[AppContext]:
    """Build the `RemindKit` bridge + resolve the SQLite store path on server start.

    On macOS the underlying EventKit init triggers the Reminders permission
    prompt the first time a never-prompted interpreter binary runs. If the
    user denies, `PermissionError` is raised and the server exits 1 — there
    is no MCP session yet to log through, so we route the message through
    stderr (the only legal pre-session diagnostic channel).

    The SQLite store path is best-effort: failure to find a store at startup
    is *not* a server-fatal error; the per-tool fallback to EventKit takes
    over with a logged warning.
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

    sqlite_db_path: Optional[Path]
    try:
        sqlite_db_path = find_db_path()
    except RemindersDBUnavailable as e:
        # Don't fail the server — the read path will fall through to EventKit.
        print(
            f"Note: Reminders SQLite store not located ({e}); read tools will use the EventKit fallback path.",
            file=sys.stderr,
        )
        sqlite_db_path = None

    try:
        yield AppContext(bridge=bridge, sqlite_db_path=sqlite_db_path)
    finally:
        # `_native` has no explicit shutdown hook (the EKEventStore is GC'd).
        # Hook reserved for future helper-subprocess teardown (S1.4+).
        pass


__all__ = ["AppContext", "app_context", "app_lifespan", "bridge_from_ctx"]
