"""Integration-suite entrypoint.

Run from the repo root (the interpreter must hold Reminders permission):

    ./venv/bin/python -m tests.integration.run [marker] [--keep]

Spins up a fresh stdio server, builds the isolated `MCP-IntegTest` fixture, runs
every scenario module, tears the fixture down, prints a pass/fail report, and
exits non-zero if any check failed. Pass `--keep` to SKIP teardown and leave the
fixture in Reminders.app for inspection — sweep it afterwards with
`./venv/bin/python -m tests.integration.cleanup`.
"""

from __future__ import annotations

import asyncio
import sys

from . import (
    scenarios_alarms,
    scenarios_attachments,
    scenarios_bulk,
    scenarios_calendars,
    scenarios_crud,
    scenarios_groups,
    scenarios_lists,
    scenarios_prompts,
    scenarios_reads,
    scenarios_sections,
    scenarios_templates,
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
    ("templates + grocery", scenarios_templates),
    ("attachments (URL / metadata / file gate)", scenarios_attachments),
    ("bulk operations", scenarios_bulk),
    ("prompts", scenarios_prompts),
]


async def main(marker: str, keep: bool = False) -> int:
    r = Reporter()
    suffix = " · KEEP (no teardown)" if keep else ""
    print(f"\n=== mcp-apple-reminders integration suite (run {marker}{suffix}) ===", flush=True)
    async with wire_session(r) as client:
        store = TestStore(client=client, marker=marker, keep=keep)
        try:
            if await store.setup():
                for title, module in SCENARIOS:
                    print(f"\n-- {title} --", flush=True)
                    await module.run(client, store, r)
        finally:
            if keep:
                print("\n-- teardown SKIPPED (--keep) --", flush=True)
                print(
                    f"   Left in place: group 'MCP-IntegTest' -> list '{store.list_name}' ({store.list_id}).",
                    flush=True,
                )
                print("   Open Reminders.app to inspect; sweep when done with:", flush=True)
                print("     ./venv/bin/python -m tests.integration.cleanup", flush=True)
            else:
                print("\n-- teardown --", flush=True)
                await store.cleanup()
    print(f"\n=== {r.summary()} ===\n", flush=True)
    return 1 if r.failed else 0


def _entry() -> int:
    # marker passed via argv (callers stamp the time); `--keep` leaves the fixture in place.
    argv = sys.argv[1:]
    keep = "--keep" in argv
    positional = [a for a in argv if not a.startswith("-")]
    marker = positional[0] if positional else "manual"
    return asyncio.run(main(marker, keep=keep))


if __name__ == "__main__":
    sys.exit(_entry())
