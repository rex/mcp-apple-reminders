"""CL-2.9 read-back: recurrence / alarms / early-reminders over the wire (ADR 0002).

Writes a recurrence rule, a time alarm, a location alarm, an early reminder, and
the urgent flag, then `get_reminder` to confirm the EventKit-summarized read-back
fields populate. NOTE: the helpers write via subprocess EKEventStores while the
read-back enriches via the server's long-lived store — if EventKit caching hides
the fresh writes within one process, that surfaces here as a real finding.
"""

from __future__ import annotations

from .fixtures import TestStore
from .harness import Reporter, WireClient


async def run(c: WireClient, store: TestStore, r: Reporter) -> None:
    lid = store.list_id
    created = await c.call_ok(
        "create_reminder",
        {"title": "IT alarms beta", "due_date": "2026-10-05T08:00:00", "calendar_id": lid},
        label="create_reminder(alarm target)",
    )
    rid = store.track_reminder(created)
    if not rid:
        r.check("alarms: have a target reminder", False)
        return

    rec = await c.call_ok(
        "set_recurrence", {"reminder_id": rid, "frequency": "weekly", "interval": 1}, label="set_recurrence(weekly)"
    )
    if rec is not None:
        r.check("set_recurrence -> status", bool(rec.get("status")), str(rec))
    await c.call_ok("set_alarm", {"reminder_id": rid, "when": "1h"}, label="set_alarm(relative 1h)")
    await c.call_ok(
        "set_location_alarm",
        {
            "reminder_id": rid,
            "latitude": 37.3349,
            "longitude": -122.009,
            "location_title": "Apple Park",
            "radius_m": 150.0,
            "proximity": "enter",
        },
        label="set_location_alarm(Apple Park)",
    )
    await c.call_ok(
        "set_early_reminder", {"reminder_id": rid, "unit": 2, "count": 1}, label="set_early_reminder(1 day)"
    )
    # set_urgent now uses REMReminder.setPrefersUrgentPresentationStyleForDateAlarms: — the
    # old urgentAlarmContext selector was removed on current macOS (fixed v0.1.93).
    urgent = await c.call_ok("set_urgent", {"reminder_id": rid, "urgent": True}, label="set_urgent(true)")
    r.check("set_urgent -> urgent=True echoed", bool(urgent) and urgent.get("urgent") is True, str(urgent))
    await c.call_ok("set_urgent", {"reminder_id": rid, "urgent": False}, label="set_urgent(false)")

    got = await c.call_ok("get_reminder", {"reminder_id": rid}, label="get_reminder(read-back)")
    if got:
        rec_sum = got.get("recurrence")
        r.check("read-back: recurrence summary present", bool(rec_sum), f"recurrence={rec_sum!r}")
        if isinstance(rec_sum, str):
            r.check("read-back: recurrence mentions 'week'", "week" in rec_sum.lower(), rec_sum)
        alarms = got.get("alarms") or []
        r.check("read-back: >=1 alarm summary", len(alarms) >= 1, f"alarms={alarms!r}")
        early = got.get("early_reminders") or []
        r.check("read-back: >=1 early-reminder summary", len(early) >= 1, f"early={early!r}")

    # exercise the clear paths (idempotent teardown of the alerts) — skipped under --keep
    # so the reminder keeps its alarm + early reminder on display for inspection.
    if not store.keep:
        await c.call_ok("set_alarm", {"reminder_id": rid, "clear": True}, label="set_alarm(clear)")
        await c.call_ok("set_early_reminder", {"reminder_id": rid, "clear": True}, label="set_early_reminder(clear)")
