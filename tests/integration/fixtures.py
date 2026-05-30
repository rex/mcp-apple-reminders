"""Isolated, self-cleaning test fixture for the integration suite.

`TestStore.setup()` creates a `MCP-IntegTest` group and a run-unique
`IntegTest-<marker>` list inside it; scenarios create reminders / smart lists /
templates and register their ids here so `TestStore.cleanup()` can remove
everything on exit (the list delete cascades its reminders). Cleanup is
tolerant — it reports each teardown step as a check but never raises, so a
half-built fixture still gets torn down.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from .harness import WireClient

GROUP_NAME = "MCP-IntegTest"


@dataclass
class TestStore:
    client: WireClient
    marker: str
    keep: bool = False
    group_id: Optional[str] = None
    list_id: Optional[str] = None
    list_name: str = ""
    reminder_ids: list[str] = field(default_factory=list)
    smart_list_ids: list[str] = field(default_factory=list)
    template_ids: list[str] = field(default_factory=list)

    async def setup(self) -> bool:
        c = self.client
        self.list_name = f"IntegTest-{self.marker}"
        group = await c.call_ok("create_group", {"name": GROUP_NAME}, label="fixture: create group")
        if group:
            self.group_id = str(group.get("id") or "")
        cal = await c.call_ok("create_calendar", {"name": self.list_name}, label="fixture: create list")
        if cal:
            self.list_id = str(cal.get("id") or "")
        if self.list_id and self.group_id:
            await c.call_ok(
                "move_list_to_group",
                {"list_id": self.list_id, "group_id": self.group_id},
                label="fixture: list -> group",
            )
        ok = bool(self.list_id and self.group_id)
        c.r.check("fixture ready (group + list created)", ok)
        return ok

    def track_reminder(self, structured: Optional[dict]) -> Optional[str]:
        rid = str((structured or {}).get("id") or "")
        if rid:
            self.reminder_ids.append(rid)
        return rid or None

    async def cleanup(self) -> None:
        c = self.client
        for sid in self.smart_list_ids:
            await c.call_raw("delete_smart_list", {"smart_list_id": sid})
        for tid in self.template_ids:
            await c.call_raw("delete_template", {"template_id": tid})
        if self.list_name:
            res = await c.call_raw("delete_calendar", {"name": self.list_name, "force": True})
            c.r.check("fixture teardown: list deleted", not res.isError)
        if self.group_id:
            res = await c.call_raw("delete_group", {"group_id": self.group_id})
            c.r.check("fixture teardown: group deleted", not res.isError)
