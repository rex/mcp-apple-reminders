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

    # KNOWN ISSUE (found by this suite): create_smart_list without filter_data_b64 errors
    # "filterData is required", yet the tool docs say omitting it creates a named smart list
    # to refine in Reminders.app — and there's no agent-accessible way to synthesize a valid
    # opaque filter blob. Either the helper must default an empty filter or the tool must
    # require/document filter_data_b64. Dedicated fix task spawned; asserted as expected-error
    # so the suite stays green and flips loudly when repaired. update_smart_list /
    # set_smart_list_pinned / delete_smart_list are blocked behind this (need a created id).
    err = await c.call_expect_error(
        "create_smart_list",
        {"name": f"IT-smart-{store.marker}", "emoji": "🧪"},
        label="create_smart_list (KNOWN: filterData required)",
    )
    r.check(
        "create_smart_list known-issue signature", "filterdata" in err.lower() or "filter" in err.lower(), err[:120]
    )
