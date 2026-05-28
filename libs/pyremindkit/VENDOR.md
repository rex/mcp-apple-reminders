# Vendored pyremindkit

This directory contains a vendored fork of `pyremindkit` — a Python wrapper
around Apple's EventKit framework for reading and writing Apple Reminders.

## Provenance

- **Upstream**: <https://github.com/namuan/pyremindkit>
- **Vendored at commit**: `d960eaa` ("feat: Allow updating reminder due date
  and improve example usage")
- **Vendored on**: 2026-05-28

## Why vendored, not pip-installed

- The upstream package is not published on PyPI.
- The MCP server (`src/mcp_apple_reminders/server.py`) inserts
  `libs/pyremindkit/src/` into `sys.path` at import time so the package is
  always loaded from this tree.
- Treat this as an **integrated local dependency**, not a third-party
  package. Server code may depend on internal library behavior; library
  changes should be reviewed against server expectations.

## Local modifications relative to upstream

The single original file `src/pyremindkit/core.py` (504 lines) was refactored
into four modules to satisfy the repo's 400-line file-size policy. Public
surface (`RemindKit`, `Reminder`, `Priority`, `Calendar`, `CalendarManager`)
is unchanged.

- `src/pyremindkit/core.py` — `RemindKit` orchestrator only.
- `src/pyremindkit/calendars.py` — `Calendar` dataclass + `CalendarManager`.
- `src/pyremindkit/models.py` — `Priority` enum + `Reminder` NamedTuple
  (dependency-free).
- `src/pyremindkit/_internal.py` — EventKit/Foundation glue
  (`_grant_permission`, `_convert_ek_reminder_to_reminder`, `_save_ek_reminder`).
- `src/pyremindkit/__init__.py` — re-exports the public surface.

## Known issues (preserved verbatim from upstream)

- `Calendar.is_default` uses `EKCalendar.isImmutable()` as the proxy
  (`calendars.py::CalendarManager.list()`). Wrong semantics — should compare
  against `event_store.defaultCalendarForNewReminders()`. Tracked as P0.
- `on_reminder_created` and `on_reminder_completed` callbacks register into
  internal lists that are never fired anywhere. Dead code.
- EventKit `error` out-parameters in `_save_ek_reminder` and
  `RemindKit.delete_reminder` are passed as Python `None`; actual EventKit
  errors never propagate.

## Re-syncing with upstream

When upstream lands a meaningful change worth pulling in:

1. Clone upstream fresh: `git clone https://github.com/namuan/pyremindkit /tmp/upstream-pyremindkit`
2. Diff against the vendored tree: `diff -ru libs/pyremindkit /tmp/upstream-pyremindkit`
3. Cherry-pick changes by hand into the refactored module layout — the file
   structure has diverged from upstream, so direct overlay won't work.
4. Update this file's "Vendored at commit" line with the new upstream sha.
