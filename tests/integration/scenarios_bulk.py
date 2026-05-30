"""Bulk ops: bulk_complete, bulk_delete_completed (scoped to the fixture list),
bulk_move (to a throwaway target). Asserts the typed BulkResult counts.

bulk_delete_completed elicits a confirmation; over the wire the test client
advertises no elicitation capability, so the server's degrade-and-proceed guard
(the v0.1.78 fix) lets it run — scoping `calendar_id` to the fixture list keeps
the deletion contained to our own completed reminders.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from .fixtures import TestStore
from .harness import Reporter, WireClient


async def run(c: WireClient, store: TestStore, r: Reporter) -> None:
    lid = store.list_id
    now = datetime.now()

    ids = []
    for i in range(3):
        rid = store.track_reminder(
            await c.call_ok("create_reminder", {"title": f"IT bulk {i}", "calendar_id": lid}, label=f"bulk seed {i}")
        )
        if rid:
            ids.append(rid)
    bc = await c.call_ok("bulk_complete", {"reminder_ids": ids}, label="bulk_complete")
    r.check(
        "bulk_complete processed all, none failed",
        bool(bc) and bc.get("processed") == len(ids) and not bc.get("failed"),
    )

    window = {
        "start": (now - timedelta(days=1)).isoformat(),
        "end": (now + timedelta(days=1)).isoformat(),
        "calendar_id": lid,
    }
    bd = await c.call_ok("bulk_delete_completed", window, label="bulk_delete_completed(fixture list)")
    r.check("bulk_delete_completed processed >= seeds", bool(bd) and (bd.get("processed") or 0) >= len(ids))
    for rid in ids:
        if rid in store.reminder_ids:
            store.reminder_ids.remove(rid)

    mids = []
    for i in range(2):
        rid = store.track_reminder(
            await c.call_ok("create_reminder", {"title": f"IT bmove {i}", "calendar_id": lid}, label=f"bmove seed {i}")
        )
        if rid:
            mids.append(rid)
    tgt_name = f"IT-bulk-{store.marker}"
    tgt = await c.call_ok("create_calendar", {"name": tgt_name}, label="bulk-move target list")
    tgt_id = str(tgt.get("id")) if tgt else ""
    if tgt_id and mids:
        bm = await c.call_ok("bulk_move", {"reminder_ids": mids, "calendar_id": tgt_id}, label="bulk_move")
        r.check("bulk_move processed all", bool(bm) and bm.get("processed") == len(mids))
        await c.call_ok("delete_calendar", {"name": tgt_name, "force": True}, label="delete bulk-move target (cascade)")
        for rid in mids:
            if rid in store.reminder_ids:
                store.reminder_ids.remove(rid)
