"""Calendar (list) lifecycle: list / get / search / default + create→rename→delete."""

from __future__ import annotations

from .fixtures import TestStore
from .harness import Reporter, WireClient


async def run(c: WireClient, store: TestStore, r: Reporter) -> None:
    lid, lname = store.list_id, store.list_name

    cals = await c.call_value("list_calendars", {}, label="list_calendars")
    r.check("list_calendars includes fixture list", lid in {x.get("id") for x in cals or []})

    # ZCOLOR is an archived REMColor blob — it must decode to hex/name, never a raw b'...' repr.
    colors = [str(x.get("color") or "") for x in cals or []]
    r.check("no list color is a raw blob repr", not any(col.startswith("b'") for col in colors))
    r.check("colored lists decode to hex/name", any(col.startswith("#") or col.isalpha() for col in colors))

    grouped = await c.call_value("list_calendars", {"include_groups": True}, label="list_calendars(include_groups)")
    r.check("list_calendars(include_groups) surfaces a group", any(x.get("is_group") for x in grouped or []))

    by_name = await c.call_ok("get_calendar", {"name": lname}, label="get_calendar(name)")
    r.check("get_calendar(name) -> fixture id", bool(by_name) and by_name.get("id") == lid)

    by_id = await c.call_ok("get_calendar_by_id", {"calendar_id": lid}, label="get_calendar_by_id")
    r.check("get_calendar_by_id -> fixture name", bool(by_id) and by_id.get("name") == lname)

    found = await c.call_value("search_calendars", {"query": "IntegTest"}, label="search_calendars")
    r.check("search_calendars finds fixture list", lid in {x.get("id") for x in found or []})

    dft = await c.call_ok("get_default_calendar", {}, label="get_default_calendar")
    r.check("get_default_calendar -> is_default", bool(dft) and dft.get("is_default") is True)

    tmp_name = f"IT-cal-{store.marker}"
    tmp = await c.call_ok("create_calendar", {"name": tmp_name, "color": "blue"}, label="create_calendar(throwaway)")
    if tmp and tmp.get("id"):
        new_name = f"IT-cal2-{store.marker}"
        renamed = await c.call_ok(
            "update_calendar", {"name": tmp_name, "new_name": new_name}, label="update_calendar(rename)"
        )
        r.check("update_calendar renamed", bool(renamed) and renamed.get("name") == new_name)
        deleted = await c.call_ok("delete_calendar", {"name": new_name, "force": True}, label="delete_calendar(force)")
        r.check("delete_calendar -> deleted=True", bool(deleted) and deleted.get("deleted") is True)

    await c.call_expect_error("get_calendar", {"name": "NoSuchList-IT-zzz"}, label="get_calendar(missing) -> isError")
