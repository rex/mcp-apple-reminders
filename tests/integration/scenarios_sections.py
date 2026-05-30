"""Subtasks + sections: create_reminder(parent=) → get_subtasks; add/assign section.

`set_parent` is a deferred stub that always raises — asserted as an expected
error. Subtask/section linkage rows can lag the SQLite read after a helper
write, so get_subtasks + assign_section poll briefly before failing.
"""

from __future__ import annotations

import asyncio

from .fixtures import TestStore
from .harness import Reporter, WireClient


async def _poll_subtask(c: WireClient, parent: str, sub: str, tries: int = 8, delay: float = 1.0) -> bool:
    for _ in range(tries):
        subs = await c.call_value("get_subtasks", {"reminder_id": parent})
        if sub in {x.get("id") for x in subs or [] if isinstance(x, dict)}:
            return True
        await asyncio.sleep(delay)
    return False


async def run(c: WireClient, store: TestStore, r: Reporter) -> None:
    lid = store.list_id

    parent = store.track_reminder(
        await c.call_ok("create_reminder", {"title": "IT parent", "calendar_id": lid}, label="create parent")
    )
    if not parent:
        r.check("sections: parent created", False)
        return

    sub = await c.call_ok(
        "create_reminder", {"title": "IT subtask", "parent_reminder_id": parent}, label="create_reminder(subtask)"
    )
    subid = store.track_reminder(sub)
    r.check("subtask carries parent_reminder_id", bool(sub) and sub.get("parent_reminder_id") == parent)
    if subid:
        r.check(
            "get_subtasks includes the subtask (polled)",
            await _poll_subtask(c, parent, subid),
            "subtask not visible via SQLite within poll window",
        )

    section = f"IT-Section-{store.marker}"
    r1 = store.track_reminder(
        await c.call_ok("create_reminder", {"title": "IT sec A", "calendar_id": lid}, label="create sec reminder A")
    )
    if r1:
        asec = await c.call_ok(
            "add_section_and_assign", {"reminder_id": r1, "section_name": section}, label="add_section_and_assign"
        )
        r.check("add_section_and_assign -> status", bool(asec) and bool(asec.get("status")))

    r2 = store.track_reminder(
        await c.call_ok("create_reminder", {"title": "IT sec B", "calendar_id": lid}, label="create sec reminder B")
    )
    if r2:
        assigned = None
        for _ in range(8):  # the section row may lag SQLite after add_section_and_assign
            res = await c.call_raw("assign_section", {"reminder_id": r2, "section_name": section})
            if not res.isError:
                assigned = res.structuredContent
                break
            await asyncio.sleep(1.0)
        r.check("assign_section -> section_name set", bool(assigned) and assigned.get("section_name") == section)

    if subid:
        await c.call_expect_error(
            "set_parent", {"reminder_id": subid, "new_parent_id": parent}, label="set_parent (deferred) -> isError"
        )
