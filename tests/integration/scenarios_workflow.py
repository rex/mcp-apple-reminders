"""Workflow board: get_workflow_lists + move_reminder_to_list + named-board moves.

`move_reminder_to_list` is tested with a throwaway target list (safe). The named
`move_reminder_{on_deck,active,done,blocked}` tools route into the user's real
`Claude-*` board, so they're tested tolerantly — a move that succeeds OR cleanly
reports an absent board both pass; only a crash fails. The board reminder is
deleted by id afterwards (cleans up wherever it landed — no leak).
"""

from __future__ import annotations

from .fixtures import TestStore
from .harness import Reporter, WireClient


def _err(res: object) -> str:
    for cb in getattr(res, "content", []) or []:
        if hasattr(cb, "text"):
            return str(cb.text)
    return "isError"


async def run(c: WireClient, store: TestStore, r: Reporter) -> None:
    lid = store.list_id

    wf = await c.call_value("get_workflow_lists", {}, label="get_workflow_lists")
    r.check("get_workflow_lists -> list", isinstance(wf, list))

    tmp_name = f"IT-wf-{store.marker}"
    tmp = await c.call_ok("create_calendar", {"name": tmp_name}, label="create wf target list")
    tmp_id = str(tmp.get("id")) if tmp else ""
    rid = store.track_reminder(
        await c.call_ok("create_reminder", {"title": "IT wf mover", "calendar_id": lid}, label="wf mover reminder")
    )
    if tmp_id and rid:
        moved = await c.call_ok(
            "move_reminder_to_list", {"reminder_id": rid, "calendar_id": tmp_id}, label="move_reminder_to_list"
        )
        r.check("move_reminder_to_list -> new list_id", bool(moved) and moved.get("list_id") == tmp_id)
        await c.call_ok(
            "move_reminder_to_list", {"reminder_id": rid, "calendar_id": lid}, label="move reminder back to fixture"
        )
        await c.call_ok("delete_calendar", {"name": tmp_name, "force": True}, label="delete wf target list")

    brid = store.track_reminder(
        await c.call_ok("create_reminder", {"title": "IT wf board", "calendar_id": lid}, label="wf board reminder")
    )
    if brid:
        for tool in ("move_reminder_on_deck", "move_reminder_active", "move_reminder_done", "move_reminder_blocked"):
            res = await c.call_raw(tool, {"reminder_id": brid})
            err = "" if not res.isError else _err(res)
            ok = (not res.isError) or "not found" in err.lower() or "does not exist" in err.lower()
            r.check(f"{tool} (moved or board absent)", ok, err[:100])
        await c.call_ok("delete_reminder", {"reminder_id": brid}, label="delete wf board reminder")
        if brid in store.reminder_ids:
            store.reminder_ids.remove(brid)
