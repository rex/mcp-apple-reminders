"""Templates (create/apply/delete) + grocery categorization (CL-2.3 / 2.4)."""

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

    tpl = await c.call_ok(
        "create_template", {"name": f"IT-tpl-{store.marker}", "source_list_id": lid}, label="create_template"
    )
    tid = str(tpl.get("id")) if tpl else ""
    r.check("create_template -> id", bool(tid))
    if tid:
        store.template_ids.append(tid)
        applied = await c.call_ok("apply_template", {"template_id": tid}, label="apply_template")
        r.check("apply_template -> status", bool(applied) and bool(applied.get("status")))
        new_id = str((applied or {}).get("id") or "")
        if new_id:  # apply creates a new list — resolve its name + delete it
            cal = await c.call_raw("get_calendar_by_id", {"calendar_id": new_id})
            nm = (cal.structuredContent or {}).get("name") if not cal.isError else None
            if nm:
                await c.call_ok("delete_calendar", {"name": nm, "force": True}, label="cleanup applied-template list")
        deleted = await c.call_ok("delete_template", {"template_id": tid}, label="delete_template")
        r.check("delete_template -> deleted=True", bool(deleted) and deleted.get("deleted") is True)
        if tid in store.template_ids:
            store.template_ids.remove(tid)

    # grocery: categorize a few grocery-ish items (may require a grocery-type list)
    items = []
    for nm in ("Milk", "Apples", "Bread"):
        rid = store.track_reminder(
            await c.call_ok("create_reminder", {"title": nm, "calendar_id": lid}, label=f"grocery item {nm}")
        )
        if rid:
            items.append(rid)
    if items:
        res = await c.call_raw("categorize_grocery_items", {"list_id": lid, "reminder_ids": items})
        if not res.isError:
            r.check("categorize_grocery_items -> status", bool((res.structuredContent or {}).get("status")))
        else:
            err = _err(res)
            r.check(
                "categorize_grocery_items (ok or grocery-list required)",
                "grocery" in err.lower() or "not found" in err.lower(),
                err[:120],
            )
