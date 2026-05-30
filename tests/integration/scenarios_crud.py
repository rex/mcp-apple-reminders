"""Core CRUD + structured-output + RFC-3339 datetime scenarios.

Exercises the create → get → update → tag → complete/uncomplete → flag → delete
lifecycle over the wire, asserting the typed structuredContent (Reminder /
DeleteResult) and that every serialized datetime is offset-bearing (the wire bug
class). One negative case confirms a bogus id is surfaced as `isError`.
"""

from __future__ import annotations

from .fixtures import TestStore
from .harness import Reporter, WireClient


def _has_offset(iso: str) -> bool:
    """True if `iso` is RFC-3339 offset-bearing (ends with Z or ±HH:MM)."""
    if not iso:
        return False
    if iso.endswith("Z"):
        return True
    return len(iso) >= 6 and iso[-6] in "+-" and iso[-3] == ":"


async def run(c: WireClient, store: TestStore, r: Reporter) -> None:
    lid = store.list_id
    due = "2026-09-01T09:30:00"

    created = await c.call_ok(
        "create_reminder",
        {"title": "IT CRUD alpha", "due_date": due, "notes": "note-1", "priority": "high", "calendar_id": lid},
        label="create_reminder",
    )
    rid = store.track_reminder(created)
    r.check("create_reminder -> id", bool(rid))
    if created:
        r.check(
            "create_reminder due_date is RFC-3339",
            _has_offset(str(created.get("due_date") or "")),
            str(created.get("due_date")),
        )
        r.check("create_reminder list_id == fixture list", created.get("list_id") == lid)

    if not rid:
        return

    got = await c.call_ok("get_reminder", {"reminder_id": rid}, label="get_reminder")
    if got:
        r.check("get_reminder title", got.get("title") == "IT CRUD alpha")
        r.check("get_reminder notes", got.get("notes") == "note-1")
        r.check("get_reminder priority in high bucket", isinstance(got.get("priority"), int) and got["priority"] >= 5)
        r.check(
            "get_reminder created_date RFC-3339",
            _has_offset(str(got.get("created_date") or "")),
            str(got.get("created_date")),
        )

    upd = await c.call_ok(
        "update_reminder",
        {"reminder_id": rid, "title": "IT CRUD alpha v2", "add_tags": ["integ", "crud"]},
        label="update_reminder",
    )
    if upd:
        r.check("update_reminder title applied", upd.get("title") == "IT CRUD alpha v2")
        r.check("update_reminder tags merged", {"integ", "crud"} <= set(upd.get("tags") or []))

    cleared = await c.call_ok(
        "update_reminder",
        {"reminder_id": rid, "clear_tags": True, "add_tags": ["only"]},
        label="update_reminder(clear_tags+add => replacement)",
    )
    if cleared:
        r.check("clear_tags + add_tags == replacement", set(cleared.get("tags") or []) == {"only"})

    comp = await c.call_ok("complete_reminder", {"reminder_id": rid}, label="complete_reminder")
    if comp:
        r.check("complete -> completed=True", comp.get("completed") is True)
    unc = await c.call_ok("uncomplete_reminder", {"reminder_id": rid}, label="uncomplete_reminder")
    if unc:
        r.check("uncomplete -> completed=False", unc.get("completed") is False)

    flagged = await c.call_ok(
        "update_reminder", {"reminder_id": rid, "flagged": True}, label="update_reminder(flagged)"
    )
    if flagged:
        r.check("update sets flagged=True", flagged.get("flagged") is True)

    await c.call_expect_error(
        "get_reminder",
        {"reminder_id": "00000000-0000-0000-0000-000000000000"},
        label="get_reminder(bogus id) -> isError",
    )

    deleted = await c.call_ok("delete_reminder", {"reminder_id": rid}, label="delete_reminder")
    if deleted:
        r.check("delete_reminder -> deleted=True", deleted.get("deleted") is True)
    if rid in store.reminder_ids:
        store.reminder_ids.remove(rid)
