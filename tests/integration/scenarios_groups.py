"""Groups (sidebar folders): list + a 2nd-group create → move list → move back → delete."""

from __future__ import annotations

from .fixtures import TestStore
from .harness import Reporter, WireClient


async def run(c: WireClient, store: TestStore, r: Reporter) -> None:
    groups = await c.call_value("list_groups", {}, label="list_groups")
    r.check("list_groups includes fixture group", store.group_id in {x.get("id") for x in groups or []})

    g2 = await c.call_ok("create_group", {"name": f"IT-grp2-{store.marker}"}, label="create 2nd group")
    g2id = str(g2.get("id")) if g2 else ""
    r.check("create_group -> id", bool(g2id))
    if not (g2id and store.list_id):
        return

    mv = await c.call_ok(
        "move_list_to_group", {"list_id": store.list_id, "group_id": g2id}, label="move fixture list -> 2nd group"
    )
    r.check("move_list_to_group -> status", bool(mv) and bool(mv.get("status")))

    # move the list back under the fixture group so teardown stays simple
    await c.call_ok(
        "move_list_to_group",
        {"list_id": store.list_id, "group_id": store.group_id},
        label="move list back to fixture group",
    )

    deleted = await c.call_ok("delete_group", {"group_id": g2id}, label="delete 2nd group")
    r.check("delete_group -> deleted=True", bool(deleted) and deleted.get("deleted") is True)
