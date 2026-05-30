"""Integration-suite entrypoint.

Run from the repo root (the interpreter must hold Reminders permission):

    ./venv/bin/python -m tests.integration.run

Spins up a fresh stdio server, builds the isolated `MCP-IntegTest` fixture, runs
every scenario module, tears the fixture down, prints a pass/fail report, and
exits non-zero if any check failed.
"""

from __future__ import annotations

import asyncio
import sys

from . import (
    scenarios_alarms,
    scenarios_calendars,
    scenarios_crud,
    scenarios_groups,
    scenarios_lists,
    scenarios_reads,
    scenarios_sections,
    scenarios_workflow,
)
from .fixtures import TestStore
from .harness import Reporter, wire_session

# Scenario modules run in order; each exposes `async def run(client, store, reporter)`.
SCENARIOS = [
    ("CRUD + read paths", scenarios_crud),
    ("alarms / recurrence / early-reminder read-back", scenarios_alarms),
    ("queries + reminders:// resources", scenarios_reads),
    ("calendars (list lifecycle)", scenarios_calendars),
    ("groups (sidebar folders)", scenarios_groups),
    ("workflow board moves", scenarios_workflow),
    ("smart lists + appearance + pinning", scenarios_lists),
    ("subtasks + sections", scenarios_sections),
]


async def main(marker: str) -> int:
    r = Reporter()
    print(f"\n=== mcp-apple-reminders integration suite (run {marker}) ===", flush=True)
    async with wire_session(r) as client:
        store = TestStore(client=client, marker=marker)
        try:
            if await store.setup():
                for title, module in SCENARIOS:
                    print(f"\n-- {title} --", flush=True)
                    await module.run(client, store, r)
        finally:
            print("\n-- teardown --", flush=True)
            await store.cleanup()
    print(f"\n=== {r.summary()} ===\n", flush=True)
    return 1 if r.failed else 0


def _entry() -> int:
    # marker passed via argv (callers stamp the time); default is stable for reruns.
    marker = sys.argv[1] if len(sys.argv) > 1 else "manual"
    return asyncio.run(main(marker))


if __name__ == "__main__":
    sys.exit(_entry())
