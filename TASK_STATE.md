# TASK_STATE — 001-visibility-foundation

> Source of truth for in-flight work. Humans and agents both write here.
> Committed to the repo. Survives sessions, machines, context compactions.
>
> Spec: `specs/001-visibility-foundation/spec.md` ·
> Plan: `specs/001-visibility-foundation/plan.md`
> Branch: `main` (trunk-strategy — all work commits directly to main, no feature branches) ·
> Owner (human): @pierce · Last update: 2026-05-28 by Claude (retrofit /retrofit session)

## 0. TL;DR for a fresh agent session

The repo just finished its brownfield retrofit (PRs 1-5). The first feature
spec, `001-visibility-foundation`, captures the P0 capability work needed to
pilot the agent-visibility-plane protocol: fix the `is_default` bug, add
`create_calendar`, add subtasks (parent-reminder + `get_subtasks` + `set_parent`).
**Next action: pick up Slice 1.1** — fix `is_default` in
`libs/pyremindkit/src/pyremindkit/calendars.py::CalendarManager.list()`. Do
NOT touch `models.py` until S1.3 (it's the contract-freeze slice).

## Standing user directives

- Subtasks must land in Phase 1 (Pierce-explicit, 2026-05-28). Already scoped that way.
- No grandfathering ever — bring files into compliance via refactor, not exclude_globs.
- Interactive autonomy mode — stop and ask between meaningful steps.

## 1. Phases

| # | Phase | Status | Exit criteria |
|---|---|---|---|
| 1 | P0 capabilities (is_default + create_calendar + subtasks) | ⏸ pending | All 4 slices below acceptance-bullet-checked; integration smoke test green |
| 2 | P1 capabilities (delete/update calendar, flagged, bulk ops, multi-cal query) | ⏸ pending | Tasks expanded at Phase 1 close |
| 3 | P2 capabilities (recurrence, alarms — time + location) | ⏸ pending | — |
| 4 | P3 + visibility-plane pilot | ⏸ pending | — |

Statuses: `⏸ pending` · `🟡 in-prog` · `✅ done` · `🔴 blocked`

## 2. Slices

### Slice 1.1 — Fix `is_default` in `CalendarManager.list()`  ← NEXT

- Status: ⏸ pending
- Owner: unassigned (next agent claims it)
- Files (planned edits): `libs/pyremindkit/src/pyremindkit/calendars.py`, `test_crud_calendars.py`, `AGENTS.md` (§9 update), `mem:core` (remove bug note)
- Files (do NOT edit): `models.py`, `_internal.py` (out of scope for S1.1; S1.3 owns model changes)
- Depends on: (none)
- Acceptance (EARS):
  - [ ] The `is_default` field shall be `True` for exactly one calendar in `list_calendars` output — the one returned by `EKEventStore.defaultCalendarForNewReminders()`. (spec §Ubiquitous)
  - [ ] Test: extend `test_calendar_operations` to assert exactly one `is_default == True` and matches `get_default().id`.
  - [ ] `make check-architecture` green.
  - [ ] AGENTS.md §9 gotcha bullet removed; `mem:core` updated.

### Slice 1.2 — `CalendarManager.create()` + `create_calendar` MCP tool

- Status: ⏸ pending
- Files (planned edits): `libs/pyremindkit/src/pyremindkit/calendars.py`, `src/mcp_apple_reminders/tools/calendars.py`, `test_crud_calendars.py`
- Files (do NOT edit): `models.py`
- Depends on: S1.1
- Acceptance: see `specs/001-visibility-foundation/tasks.md::S1.2`.

### Slice 1.3 — `Reminder` parent / subtasks fields + converter wiring

- Status: ⏸ pending
- Files (planned edits): `libs/pyremindkit/src/pyremindkit/models.py` (CONTRACT FREEZE), `libs/pyremindkit/src/pyremindkit/_internal.py`, `src/mcp_apple_reminders/formatting.py`, `test_crud_reminders.py`
- Files (do NOT edit): `calendars.py`, `core.py` (S1.4 extends them)
- Depends on: S1.2
- Acceptance: see `specs/001-visibility-foundation/tasks.md::S1.3`. Verify PyObjC binding presence FIRST; if missing, switch to notes-prefix fallback and update the spec's "Decided in design.md" line.

### Slice 1.4 — `create_reminder(parent_reminder_id)` + `get_subtasks` + `set_parent`

- Status: ⏸ pending
- Files (planned edits): `libs/pyremindkit/src/pyremindkit/core.py`, `libs/pyremindkit/src/pyremindkit/calendars.py`, `src/mcp_apple_reminders/tools/reminders.py`, `src/mcp_apple_reminders/tools/queries.py`, new `test_subtasks.py`
- Files (do NOT edit): `models.py` (FROZEN after S1.3)
- Depends on: S1.3
- Acceptance: see `specs/001-visibility-foundation/tasks.md::S1.4`.

## 3. Blockers / open questions

- PyObjC binding presence for `setParentReminder_` / `parentReminder` / `subtasks` — must be verified in S1.3 before contracts freeze. If missing, the notes-prefix fallback becomes the primary path and the warning is removed.

## 4. Recent decisions (append-only, newest first)

- 2026-05-28 — Subtasks scoped into Phase 1 (Pierce explicit, "absolute must"). Decided in /retrofit session.
- 2026-05-28 — Phase 1 contracts freeze at S1.3 (models.py field order). After that, `models.py` is touch-only-with-ADR.
- 2026-05-28 — Slug `001-visibility-foundation` chosen (vs `001-vp-foundation` or `001-p0-capabilities`). More legible to future agents.
- 2026-05-28 — Color encoding picked: 8-named-palette + custom hex string. EventKit takes NSColor; conversion happens at the EventKit boundary.

## 5. Next actions (ordered)

1. Pick up **Slice 1.1** (`is_default` fix) — single-file change in `calendars.py`, ~30 LOC including test extension.
2. After S1.1 lands and pushes, pick up **Slice 1.2** (`create_calendar`).
3. Before starting **Slice 1.3**, verify PyObjC `setParentReminder_` binding presence with a 5-line REPL probe. Update the spec's "Decided in design.md" open-question line based on the result.
4. After **Slice 1.3** contracts freeze, pick up **Slice 1.4** (the meaty subtask wiring).
5. When Phase 1 is done, expand Phase 2 tasks in `tasks.md`.

## 6. Handoff note (fill when ending a session)

2026-05-28 (Claude, retrofit /retrofit session): Repo retrofit complete (PRs 1-5 landed on `chore/seed-agents-md`). Spec written, no implementation started. Next agent: read `AGENTS.md`, then this file's §0 and Slice 1.1, then `specs/001-visibility-foundation/spec.md` for the requirements + `design.md` for the approach. Run `./venv/bin/python3 verify_setup.py` first to confirm the environment is intact, then start S1.1.
