"""Sweep leftover integration fixtures (after `run.py --keep`, or post-crash).

Deletes every `IntegTest-*` list (cascading its reminders) and the
`MCP-IntegTest` group(s). Safe to run anytime — it only touches the suite's own
namespaced fixtures, never your real lists.

    ./venv/bin/python -m tests.integration.cleanup
"""

from __future__ import annotations

import asyncio
import sys

from .fixtures import GROUP_NAME
from .harness import Reporter, wire_session


async def main() -> int:
    r = Reporter()
    print("\n=== integration fixture sweep ===", flush=True)
    async with wire_session(r) as c:
        cals = await c.call_value("list_calendars", {"include_groups": True}, label="list_calendars")
        items = [x for x in cals or [] if isinstance(x, dict)]
        lists = [x for x in items if not x.get("is_group") and str(x.get("name", "")).startswith("IntegTest-")]
        groups = [x for x in items if x.get("is_group") and x.get("name") == GROUP_NAME]
        for cal in lists:  # lists first — delete cascades their reminders
            res = await c.call_raw("delete_calendar", {"name": cal["name"], "force": True})
            r.check(f"deleted list {cal['name']}", not res.isError)
        for grp in groups:
            res = await c.call_raw("delete_group", {"group_id": grp.get("id")})
            r.check(f"deleted group {grp.get('name')}", not res.isError)
        if not lists and not groups:
            r.check("nothing to sweep (already clean)", True)
    print(f"\n=== {r.summary()} ===\n", flush=True)
    return 1 if r.failed else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
