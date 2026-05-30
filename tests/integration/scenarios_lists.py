"""List appearance + pinning + custom smart-list lifecycle (CL-2.1 / 2.2)."""

from __future__ import annotations

from .fixtures import TestStore
from .harness import Reporter, WireClient


async def run(c: WireClient, store: TestStore, r: Reporter) -> None:
    lid = store.list_id

    app = await c.call_ok(
        "set_list_appearance", {"list_id": lid, "color": "purple", "symbol": "star.fill"}, label="set_list_appearance"
    )
    r.check("set_list_appearance -> status", bool(app) and bool(app.get("status")))
    pin = await c.call_ok("set_list_pinned", {"list_id": lid, "pinned": True}, label="set_list_pinned(true)")
    r.check("set_list_pinned -> status", bool(pin) and bool(pin.get("status")))
    await c.call_ok("set_list_pinned", {"list_id": lid, "pinned": False}, label="set_list_pinned(false)")

    # create_smart_list with NO filter_data_b64 creates a named custom smart list to refine
    # in Reminders.app (filterData is now optional — fixed v0.1.94).
    sl = await c.call_ok(
        "create_smart_list", {"name": f"IT-smart-{store.marker}", "emoji": "🧪"}, label="create_smart_list (no filter)"
    )
    sid = str(sl.get("id")) if sl else ""
    r.check("create_smart_list -> id", bool(sid))
    if not sid:
        return
    store.smart_list_ids.append(sid)  # teardown safety net if a later step throws

    upd = await c.call_ok(
        "update_smart_list", {"smart_list_id": sid, "name": f"IT-smart2-{store.marker}"}, label="update_smart_list"
    )
    r.check("update_smart_list -> status", bool(upd) and bool(upd.get("status")))
    slpin = await c.call_ok(
        "set_smart_list_pinned", {"smart_list_id": sid, "pinned": True}, label="set_smart_list_pinned(true)"
    )
    r.check("set_smart_list_pinned -> status", bool(slpin) and bool(slpin.get("status")))
    await c.call_ok(
        "set_smart_list_pinned", {"smart_list_id": sid, "pinned": False}, label="set_smart_list_pinned(false)"
    )

    deleted = await c.call_ok("delete_smart_list", {"smart_list_id": sid}, label="delete_smart_list")
    r.check("delete_smart_list -> deleted=True", bool(deleted) and deleted.get("deleted") is True)
    if sid in store.smart_list_ids:
        store.smart_list_ids.remove(sid)
