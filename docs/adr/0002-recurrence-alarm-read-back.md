# ADR 0002 — Recurrence / alarm read-back via EventKit summaries

- **Status:** Accepted (2026-05-30)
- **Slice:** CL-2.9
- **Relates to:** ADR 0001 (list-group tail-append precedent), S0.3 (contract freeze)

## Context

Reminders can carry recurrence rules, time/location alarms, and "early reminder"
offsets. The *write* side shipped in spec 002 (`set_recurrence`, `set_alarm`,
`set_location_alarm`, `set_early_reminder`) but these were **write-only** — the
`Reminder` model surfaced none of them on read.

A CL-2.9 investigation against the live store (seeded with one of every alarm
type) established where each datum actually lives:

| Datum | Storage | Readable? |
|---|---|---|
| Recurrence | EventKit `EKRecurrenceRule` | Yes — EventKit only |
| Time / location alarms | EventKit `EKAlarm` (proximity + structured location) | Yes — EventKit only |
| Early-reminder offsets | SQLite `ZDUEDATEDELTAALERTSDATA` (JSON) | Yes — SQLite-native |
| "When messaging <person>" trigger | CloudKit blob only | **No** |
| `urgent` flag | CloudKit blob only | **No** |

Crucially, `ZREMCDRECURRENCERULE` / `ZREMCDALARM` **do not exist** — recurrence
and alarms are NOT in any readable SQLite column; they live in the opaque
`ZCKSERVERRECORDDATA` CloudKit blob (NSKeyedArchiver). The only way to read them
is EventKit, which is the slow per-item path (the server's reads are SQLite-first
for speed).

## Decision

Tail-append three read-back fields to the frozen `Reminder` model (S0.3 permits
tail additions with defaults; precedent ADR 0001):

- `recurrence: str | None` — human summary, e.g. `"Monthly until 2026-08-30"`.
- `alarms: list[str]` — human summaries, e.g. `"Arriving: <place> (within 100 m)"`.
- `early_reminders: list[str]` — human summaries, e.g. `"1 month before due"`.

Population:

- `early_reminders` is decoded from SQLite (`ZDUEDATEDELTAALERTSDATA`) and
  populated **everywhere** (cheap).
- `recurrence` + `alarms` are EventKit-sourced summaries, populated **only in
  `get_reminder(id)`** (one `calendarItemWithIdentifier_` call). Bulk list queries
  leave them `null` / `[]` so the fast SQLite path stays fast.

We expose **human summary strings**, not structured objects — bounded model
surface, agent-readable, and tail-safe. A structured representation can be a
future tail-append if it's ever needed.

`urgent` and the "when messaging" trigger are **dropped from read-back** — neither
is retrievable without parsing the CloudKit blob (fragile / out of scope).

## Consequences

- `Reminder` gains three tail fields; the field-order lock test is updated to
  match. Existing callers are unaffected (defaults).
- `get_reminder(id)` makes one extra EventKit call for enrichment; bulk queries
  are unchanged.
- Recurrence/alarm summaries are lossy display strings — clients needing the
  exact rule should treat them as hints, not a structured contract.
