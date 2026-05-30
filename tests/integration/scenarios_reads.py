"""Read surface: query tools + `reminders://` resources reflect live writes.

Seeds overdue / today / future reminders (dates relative to the real clock, so
the server's today/overdue windows line up), then asserts each query tool and
each resource surfaces them by id. Membership checks (not counts) keep it robust
against the rest of the user's store. Closes with a delete → recently-deleted
round-trip.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta

from .fixtures import TestStore
from .harness import Reporter, WireClient

TAG = "itreadtag"


def _ids(items: object) -> set:
    return {x.get("id") for x in items or [] if isinstance(x, dict)}


async def _poll_tag(c: WireClient, tag: str, tries: int = 8, delay: float = 1.0) -> bool:
    """Hashtag rows (ZREMCDHASHTAGLABEL) can lag the SQLite read after a helper
    write — poll a few seconds before deciding the resource is wrong."""
    for _ in range(tries):
        tags = (await c.read_json("reminders://tags") or {}).get("tags") or []
        if tag in tags:
            return True
        await asyncio.sleep(delay)
    return False


async def run(c: WireClient, store: TestStore, r: Reporter) -> None:
    lid = store.list_id
    now = datetime.now()
    overdue_due = (now - timedelta(days=2)).replace(microsecond=0).isoformat()
    today_due = now.replace(hour=12, minute=0, second=0, microsecond=0).isoformat()
    future_due = (now + timedelta(days=30)).replace(microsecond=0).isoformat()

    od = store.track_reminder(
        await c.call_ok(
            "create_reminder",
            {"title": "IT reads overdue", "due_date": overdue_due, "calendar_id": lid},
            label="seed overdue",
        )
    )
    td = store.track_reminder(
        await c.call_ok(
            "create_reminder",
            {"title": "IT reads today", "due_date": today_due, "calendar_id": lid},
            label="seed today",
        )
    )
    fut = store.track_reminder(
        await c.call_ok(
            "create_reminder",
            {"title": "IT reads future", "due_date": future_due, "calendar_id": lid},
            label="seed future",
        )
    )
    if not (od and td and fut):
        r.check("reads: seeds created", False)
        return
    await c.call_ok("update_reminder", {"reminder_id": td, "add_tags": [TAG]}, label="tag today seed")

    # --- query tools ---
    in_list = _ids(await c.call_value("get_reminders", {"calendar_id": lid}, label="get_reminders(by list)"))
    r.check("get_reminders(list) returns all 3 seeds", {od, td, fut} <= in_list, f"got {len(in_list)} ids")
    r.check(
        "get_overdue_reminders includes overdue seed",
        od in _ids(await c.call_value("get_overdue_reminders", {}, label="get_overdue_reminders")),
    )
    r.check(
        "get_today_reminders includes today seed",
        td in _ids(await c.call_value("get_today_reminders", {}, label="get_today_reminders")),
    )
    r.check(
        "search_reminders finds seeds",
        {od, td, fut} <= _ids(await c.call_value("search_reminders", {"query": "IT reads"}, label="search_reminders")),
    )
    await c.call_value("get_next_reminder", {}, label="get_next_reminder")

    await c.call_ok("complete_reminder", {"reminder_id": fut}, label="complete future seed")
    rng = _ids(
        await c.call_value(
            "get_completed_in_range",
            {"start": (now - timedelta(days=1)).isoformat(), "end": (now + timedelta(days=1)).isoformat()},
            label="get_completed_in_range",
        )
    )
    r.check("get_completed_in_range includes just-completed", fut in rng)

    # --- resources ---
    list_res = await c.read_json(f"reminders://list/{lid}")
    r.check("resource reminders://list/{id} reflects seeds", {od, td} <= _ids((list_res or {}).get("reminders")))
    r.check(
        "resource reminders://today includes today seed",
        td in _ids((await c.read_json("reminders://today") or {}).get("reminders")),
    )
    r.check(
        "resource reminders://overdue includes overdue seed",
        od in _ids((await c.read_json("reminders://overdue") or {}).get("reminders")),
    )
    r.check(
        "resource reminders://tags includes our tag (polled)",
        await _poll_tag(c, TAG),
        "tag not visible in SQLite hashtag join within poll window",
    )
    default_res = await c.read_json("reminders://default")
    r.check("resource reminders://default parses", isinstance(default_res, dict) and "reminders" in default_res)
    appearance_res = await c.read_json("reminders://appearance")
    r.check("resource reminders://appearance parses", isinstance(appearance_res, dict) and bool(appearance_res))

    # --- delete -> recently-deleted round-trip ---
    await c.call_ok("delete_reminder", {"reminder_id": od}, label="delete overdue seed")
    if od in store.reminder_ids:
        store.reminder_ids.remove(od)
    r.check(
        "get_recently_deleted includes deleted seed",
        od in _ids(await c.call_value("get_recently_deleted", {}, label="get_recently_deleted")),
    )
    r.check(
        "resource reminders://recently-deleted includes deleted seed",
        od in _ids((await c.read_json("reminders://recently-deleted") or {}).get("reminders")),
    )
