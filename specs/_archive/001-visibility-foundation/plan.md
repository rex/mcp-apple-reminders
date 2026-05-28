# Plan — 001-visibility-foundation

> Phased implementation. Derives from `spec.md` + `design.md`.

## Phases

### Phase 1 — P0 capabilities (foundation)

**Exit criteria**: `is_default` reports correctly; `create_calendar` MCP tool ships; subtasks work end-to-end (parent on create, get_subtasks, set_parent). All MCP smoke tests green.

Slices:
- [ ] **S1.1** — Fix `is_default` bug in `CalendarManager.list()`. (~30 LOC including tests.)
- [ ] **S1.2** — `CalendarManager.create()` + `create_calendar` MCP tool. (~120 LOC.)
- [ ] **S1.3** — Extend `Reminder` NamedTuple + `_convert_ek_reminder_to_reminder` to populate `parent_reminder_id` and `subtasks`. Verify PyObjC binding presence; pick canonical-vs-fallback path. (~80 LOC.)
- [ ] **S1.4** — Extend `create_reminder` to accept `parent_reminder_id`; add `get_subtasks` + `set_parent` MCP tools and underlying `RemindKit` methods. (~140 LOC.)

### Phase 2 — P1 capabilities (high-leverage)

**Exit criteria**: Calendar lifecycle complete; flagged is settable + filterable; bulk ops and completed-in-date-range queries available.

Slices:
- [ ] **S2.1** — `delete_calendar` + `update_calendar` (rename / color change).
- [ ] **S2.2** — `flagged` setter on `create_reminder`/`update_reminder`; flagged filter on `get_reminders`.
- [ ] **S2.3** — `get_completed_in_range` query tool.
- [ ] **S2.4** — Bulk ops: `bulk_delete_completed`, `bulk_complete`, `bulk_move`.
- [ ] **S2.5** — Multi-calendar query (pass `calendar_ids: [str]` to `get_reminders`).

### Phase 3 — P2 capabilities (notifications)

**Exit criteria**: Recurrence rules work; time-based alarms work; location-based alarms work.

Slices:
- [ ] **S3.1** — `EKRecurrenceRule` support: daily / weekly / monthly / yearly with end conditions.
- [ ] **S3.2** — `EKAlarm` time-based: relative offset and absolute date.
- [ ] **S3.3** — `EKAlarm` location-based: `structuredLocation` with proximity.
- [ ] **S3.4** — `startDate` field on Reminder + start-date filter on queries.

### Phase 4 — P3 capabilities (observability + integration)

**Exit criteria**: Real-time change notifications + visibility-plane pilot wired to the new primitives.

Slices:
- [ ] **S4.1** — `EKEventStoreChangedNotification` observer — surface as MCP resource (not tool).
- [ ] **S4.2** — Visibility-plane pilot: AGENTS.md rule for `Agents-<project>` lists; auto-create on session start; agent writes Phase/Slice reminders.
- [ ] **S4.3** — `refreshSourcesIfNecessary` MCP tool for force-sync.

## Slice discipline

- Each slice ≤150 LOC diff. (S1.4 is at the upper bound — review carefully if it grows.)
- Each slice independently revertable.
- Each slice has tests in the imperative-script style (`test_crud_*.py` / `test_workflow_*.py` modules using `test_support/harness`). Pytest migration is out of scope.
- Every slice runs `make check-architecture` green before merge.

## Risks

| Risk | Probability | Impact | Mitigation |
|---|---|---|---|
| PyObjC binding for `setParentReminder_` / `parentReminder` not exposed | Medium | High (subtasks become a notes-encoded fallback) | Verify in S1.3 before contracts freeze; document fallback in code. |
| `saveCalendar:commit:error:` rejection on non-iCloud source | Low | Medium (some users have only Exchange or Local) | Inspect sources in S1.2; pick first reminder-supporting source; raise with clear message if none. |
| `Reminder` NamedTuple positional change breaks unknown callers | Low | Medium | New fields appended at tail; the first 11 fields' positions are unchanged. Document in `models.py` docstring. |
| Test files exceed 250-line soft limit as suites grow | Medium | Low | Soft limit is warning-only; if a test file approaches 400, split by sub-domain. |

## Dependencies

- macOS 14+ for canonical subtask APIs (Pierce's machine: macOS 15 / Sequoia — fine).
- PyObjC `pyobjc-framework-EventKit>=10.0` (already pinned in `pyproject.toml`).
- No external services; no other team blocking.

## Estimated effort

- Phase 1: ~4 slices, 2–3 days of focused work.
- Phase 2: ~5 slices, 3–5 days.
- Phase 3: ~4 slices, 4–6 days (alarms are fiddlier than they look).
- Phase 4: ~3 slices, 2–4 days plus pilot-driven iteration.
- **Total**: ~16 slices, ~2 weeks of focused capacity (pessimistic).

## Frozen decisions (do not re-plan)

Once Phase 1 lands, these are fixed:

- `Reminder` field order — additions go at the tail only.
- MCP tool names: `create_calendar`, `get_subtasks`, `set_parent`. No renames.
- `create_reminder` accepts `parent_reminder_id` (not `parent_id`, not `parent`).
- Color encoding: 8-named-color palette + custom hex string. No other formats.
- Parent / calendar mismatch is a ValueError, NOT a silent override.

Changes to frozen decisions require an ADR + spec update + plan update.
