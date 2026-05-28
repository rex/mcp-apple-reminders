# pyremindkit (vendored)

> **📌 Vendored dependency — agents: do not refactor without consulting `VENDOR.md`. Upstream is at https://github.com/namuan/pyremindkit. Significant divergence from upstream is intentional (refactored into 4 modules for line-limit compliance). Original upstream README preserved as `README.upstream.md`.**

Python wrapper around macOS EventKit for reading and writing Apple Reminders.

## Status

🟡 Vendored fork · Upstream commit `d960eaa` · Local-mods record: `VENDOR.md`

## Why this exists

The upstream `pyremindkit` is not on PyPI, so it's vendored. The MCP server
needs a Python surface for EventKit's reminder/calendar operations; this is it.

See `VENDOR.md` for the full upstream-provenance + local-mods narrative.

## Public API

Re-exported from `src/pyremindkit/__init__.py`:

- `RemindKit` — the top-level client. Construct once; pass to handlers.
- `Reminder` — immutable NamedTuple snapshot of an EventKit reminder.
- `Priority` — named priority enum (NONE/LOW/MEDIUM/HIGH).
- `Calendar` — dataclass mirror of an EKCalendar with reminder ops bound to it.
- `CalendarManager` — accessor surface for the set of calendars.

Do NOT reach into `_internal`, `calendars`, `models`, or `core` directly. Use
the re-exports.

## Architecture

```
mcp_apple_reminders.server
    ↓ (sys.path.insert → import)
pyremindkit/__init__.py  ←──── re-exports public surface
    ↓
core.py::RemindKit  (orchestrator)
    ↓                ↓
calendars.py   _internal.py
(Calendar +    (EventKit glue,
 Manager)       conversion helpers)
    ↓                ↓
models.py (pure value types)
    ↓
EventKit / Foundation (PyObjC)
```

- Depends on: `pyobjc-core`, `pyobjc-framework-EventKit`, stdlib.
- Depended on by: `mcp_apple_reminders.server`, test scripts at repo root.

## Files

- `VENDOR.md` — upstream provenance, local-mods record, re-sync procedure.
- `README.upstream.md` — upstream's original README, preserved verbatim.
- `src/pyremindkit/__init__.py` — public surface re-exports.
- `src/pyremindkit/core.py` — `RemindKit` orchestrator. ~230 lines.
- `src/pyremindkit/calendars.py` — `Calendar` + `CalendarManager`. ~240 lines.
- `src/pyremindkit/models.py` — `Priority` enum + `Reminder` NamedTuple. ~55 lines, dependency-free.
- `src/pyremindkit/_internal.py` — EventKit/Foundation glue. ~125 lines. NOT public.
- `LICENSE`, `setup.py`, `pyproject.toml` — upstream's own packaging metadata. Not used; preserved for diff-ability against upstream.
- `examples/` — upstream's example scripts. Not exercised; preserved.

## Invariants

- **Public surface is stable.** `__init__.py` exports are a contract; don't remove or rename without coordinating with `mcp_apple_reminders.server` and tests.
- **`models.py` stays dependency-free.** No EventKit / Foundation imports. Other modules import FROM models, never the reverse.
- **Permission request happens exactly once per process.** `RemindKit.__init__` calls `_grant_permission`; don't add a second instantiation path.
- **EventKit values cross the bridge via `_internal`.** Conversions live in `_convert_ek_reminder_to_reminder` and `_save_ek_reminder`. Don't duplicate them in `core.py` or `calendars.py`.

## Common tasks

- **Re-sync with upstream** — follow the procedure in `VENDOR.md`. The flat-file structure has diverged; manual cherry-pick is required.
- **Add a new EventKit-backed operation** — add a method to `RemindKit` (top-level) or to `Calendar` (calendar-scoped). Use `_save_ek_reminder` for writes; use `_convert_ek_reminder_to_reminder` to surface results.
- **Fix the `is_default` bug** — `calendars.py::CalendarManager.list()`. Replace `is_default=calendar.isImmutable()` with a comparison against `self._event_store.defaultCalendarForNewReminders().calendarIdentifier()`.

## Gotchas

- The known bugs are *preserved verbatim* in this refactor. Fixing them is intentional follow-up work, not refactor scope. See `VENDOR.md` + `AGENTS.md §9`.
- The upstream's `pyproject.toml` and `setup.py` are DEAD METADATA — this fork is not pip-installable. The repo-level `pyproject.toml` (one directory up of `libs/`) drives actual installation.
- `Reminder` is a `NamedTuple` — fields are positional. Callers that unpack rely on field order; do not reorder.

## Related

- `VENDOR.md` — upstream sha + local-mods record.
- `README.upstream.md` — what upstream says.
- `../../AGENTS.md §9` — the known bugs list.
- `../../MAP.md` — where this module sits in the larger picture.
