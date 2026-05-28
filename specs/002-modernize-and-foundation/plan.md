# Plan — 002-modernize-and-foundation

> Phased implementation plan. Derives from spec + design.
> Implementer subagent executes one slice at a time (Pierce's `interactive` autonomy).

## Phases

### Phase 0 — Modernize the platform (substrate)

**Exit criteria**: FastMCP, MCP 1.27+, lifespan-managed bridge, Pydantic models, Context logging. All 22 existing tools still work end-to-end with no surface changes. `make lint && make check-architecture && pytest` green.

Slices:
- [ ] **S0.1** — Bump `mcp>=1.27` in pyproject.toml; pin compatible PyObjC versions; resolve any deprecation warnings. (~30 LOC)
- [ ] **S0.2** — Rename `libs/pyremindkit/` → `src/mcp_apple_reminders/_native/`. Update imports throughout. Delete `libs/`, `VENDOR.md`, `README.upstream.md` — the vendored-dep narrative ends. (~80 LOC of moves + import updates)
- [ ] **S0.3** — Create `src/mcp_apple_reminders/models.py` with Pydantic `Calendar` + `Reminder` (full field set from design.md). Add converter helpers. (~120 LOC)
- [ ] **S0.4** — Migrate `server.py` from low-level `Server` to `FastMCP` + lifespan. The 22 tools become 22 decorated functions. Output formats become structured. (~250 LOC modified, ~150 LOC removed)
- [ ] **S0.5** — Replace every `print(..., file=sys.stderr)` in tool code with `Context` logging. (~30 LOC)

### Phase 1 — P0 capabilities (calendar lifecycle + ReminderKit primitives)

**Exit criteria**: `create_calendar`, `delete_calendar`, `update_calendar` shipped. ReminderKit bound. `set_flagged`, `set_tags`, `get_subtasks`, `set_parent` shipped. `create_reminder(parent_reminder_id=...)` works.

Slices:
- [x] **S1.1** — Fix `is_default` in `CalendarManager.list()`. **DONE** in commit `117cc8a` (pre-spec-rewrite).
- [ ] **S1.2** — `CalendarManager.create()` + `@mcp.tool() create_calendar`. (~120 LOC)
- [ ] **S1.3** — `CalendarManager.delete()` + `CalendarManager.update()` + tools. (~140 LOC)
- [ ] **S1.4** — `_native/reminderkit.py` bridge: load private framework, bind to `REMReminder`, expose subtasks/flagged/tags read paths. **Includes the load-failure degradation path.** (~180 LOC)
- [ ] **S1.5** — Subtasks write paths: `create_reminder(parent_reminder_id)`, `set_parent`, `get_subtasks`. (~140 LOC)
- [ ] **S1.6** — `set_flagged` tool + read-flagged in `Reminder` already from S0.3. (~50 LOC)
- [ ] **S1.7** — `set_tags` tool + `tags` filter on `get_reminders`. (~80 LOC)

### Phase 2 — MCP protocol primitives (Resources, Prompts, Sampling, Elicitation)

**Exit criteria**: Resources surface live views. Four canned prompts. Progress reporting on bulk ops. Elicitation guards destructive ops. Sampling pattern proven on one tool.

Slices:
- [ ] **S2.1** — Resources: `reminders://list/{id}`, `reminders://default`, `reminders://overdue`, `reminders://today`. (~120 LOC)
- [ ] **S2.2** — Prompts: `daily_review`, `weekly_retro`, `brain_dump_triage`, `agent_visibility_sync`. (~150 LOC)
- [ ] **S2.3** — Progress reporting wired into bulk-op skeleton (helpers `_native/bulk.py`); cancellation check between items. (~80 LOC)
- [ ] **S2.4** — Elicitation: `delete_calendar` (non-empty) and `bulk_delete_completed` (any) prompt for confirmation via `ctx.elicit`. (~60 LOC)
- [ ] **S2.5** — Sampling: `triage_brain_dump` tool calls `ctx.session.create_message` to sort items by domain. (~100 LOC)

### Phase 3 — Feature parity (alarms, recurrence, bulk, multi-cal)

**Exit criteria**: Match `FradSer/apple-events` on alarms (time + location), recurrence (4 frequencies), bulk ops. Plus multi-calendar query and completed-in-range.

Slices:
- [ ] **S3.1** — Time-based alarms: `EKAlarm.alarmWithRelativeOffset:` + `alarmWithAbsoluteDate:`. Tool: `set_alarm`. (~120 LOC)
- [ ] **S3.2** — Location-based alarms: `EKAlarm.structuredLocation`, proximity enter/leave. Tool: `set_location_alarm`. (~140 LOC)
- [ ] **S3.3** — Recurrence rules: `EKRecurrenceRule` with daily/weekly/monthly/yearly + end conditions. Tool: `set_recurrence`. (~150 LOC)
- [ ] **S3.4** — Bulk ops: `bulk_complete`, `bulk_delete_completed`, `bulk_move`. Uses S2.3 progress helpers + S2.4 elicitation. (~120 LOC)
- [ ] **S3.5** — Multi-calendar query: `get_reminders(calendar_ids=[...])`. (~50 LOC)
- [ ] **S3.6** — `get_completed_in_range` query. (~60 LOC)

### Phase 4 — Visibility-plane pilot + cross-cutting

**Exit criteria**: `Agents-<project>` lists auto-bootstrap. Optional streamable-HTTP. Security review done. Documentation refreshed.

Slices:
- [ ] **S4.1** — `bootstrap_agent_list` tool + `agents://current` resource. AGENTS.md global rule for session-start auto-bootstrap. (~120 LOC + docs)
- [ ] **S4.2** — `TodoWrite` mirror — the agent's internal todos sync into the Reminders list within 5s of any change. (~150 LOC — stretch)
- [ ] **S4.3** — Streamable HTTP transport opt-in (`VIBE.yaml::server.transport: streamable_http`). (~80 LOC)
- [ ] **S4.4** — `docs/SECURITY-REVIEW.md` per OWASP MCP guide. Per-tool kill-switch flag map. (~docs + ~60 LOC)
- [ ] **S4.5** — README + MAP.md + AGENTS.md sweep. Tool catalog page generated from the registered tools list. (~docs)

## Slice discipline

- Each slice ≤150 LOC diff. (S0.4 exceeds — call out for review; may split.)
- Each slice independently revertable.
- Each slice has tests at minimum smoke-level. Pytest migration of the test suite is a separate effort (deferred).
- `make lint && make check-architecture` green at slice close.
- Trunk strategy: commit directly to `main`. Signed. Version-bumped. Pushed.

## Risks

| Risk | Probability | Impact | Mitigation |
|---|---|---|---|
| ReminderKit binding breaks on a future macOS update | Medium (long-term) | High (subtasks regress) | Degraded mode (spec §Unwanted-behavior). Re-bind on each macOS release. AppleScript fallback is a P1 if it bites. |
| FastMCP API changes between 1.27 and 2.x | Medium | Medium | Pin to 1.27.x in pyproject; upgrade with eyes open. |
| Pydantic model migration breaks an existing tool's output shape | Medium | Medium | Phase 0.4 is the biggest slice; explicit pytest pass at end before merge. |
| Sampling latency / cost surprises | Low | Low | Sampling is one tool (`triage_brain_dump`); user-opt-in. Logs token count. |
| ReminderKit + EventKit both touching same reminder triggers EventKit observer storm | Low | Medium | Use ReminderKit for set-only flows; do reads via EventKit conversion where possible. |

## Dependencies

- macOS 26+ for current ReminderKit signatures. (Pierce on 26.1 — fine.)
- PyObjC 10+. Pinned.
- `mcp>=1.27` (PyPI). Pin range.
- No external services. No other team blocking.

## Estimated effort

- Phase 0: 5 slices, ~2 days.
- Phase 1: 6 remaining slices (1.1 done), ~3 days.
- Phase 2: 5 slices, ~2 days.
- Phase 3: 6 slices, ~3 days.
- Phase 4: 5 slices, ~2 days.
- **Total**: ~22 slices, ~12 days of focused capacity. Realistic clock-time given context-switching: 2–3 weeks.

## Frozen decisions (do not re-plan)

Once Phase 0 lands, these are locked:

- **Substrate**: FastMCP, `mcp>=1.27`, `_native/` package layout.
- **Models**: Pydantic field order in `models.py::Reminder` and `Calendar` (additions at tail only; reorders need ADR).
- **Subtask backend**: ReminderKit private API via PyObjC. Degraded-mode is the fallback, not a parallel path.
- **Tool naming**: snake_case action-first (existing pattern). New tools follow.
- **Color encoding**: 8 named palette + custom hex.
- **Trunk strategy**: no feature branches. (Already locked at retrofit time.)

Changes require ADR + spec amendment + plan amendment.
