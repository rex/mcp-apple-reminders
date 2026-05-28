# Plan — 002-modernize-and-foundation

> Phased implementation plan. Derives from spec + design.
> Implementer subagent executes one slice at a time (Pierce's `interactive` autonomy).

## Phases

### Phase 0 — Modernize the platform (substrate)

**Exit criteria**: FastMCP, MCP 1.27+, lifespan-managed bridge, Pydantic models with deeplinks, Context logging, **native build pipeline producing `_native/bin/rem_eventkit` and `_native/bin/rem_reminderkit`**. All 22 existing tools still work end-to-end with no surface changes.

Slices:
- [ ] **S0.1** — Bump `mcp>=1.27` in pyproject.toml; pin compatible PyObjC versions; resolve any deprecation warnings. (~30 LOC)
- [ ] **S0.2** — Rename `libs/pyremindkit/` → `src/mcp_apple_reminders/_native/`. Delete vendored-dep narrative (VENDOR.md, README.upstream.md, libs/). Update imports throughout. (~80 LOC of moves + import updates)
- [ ] **S0.3** — Create `src/mcp_apple_reminders/models.py` with Pydantic `Calendar` + `Reminder` (full field set from design.md, including `deeplink`). Add converter helpers. **Verify `EKReminder.calendarItemIdentifier()` matches SQLite `ZIDENTIFIER` so deeplinks work from both paths.** (~140 LOC)
- [ ] **S0.4** — Migrate `server.py` from low-level `Server` to `FastMCP` + lifespan. The 22 tools become 22 decorated functions. Output formats become structured. (~250 LOC modified, ~150 LOC removed) — biggest slice; may split.
- [ ] **S0.5** — Replace every `print(..., file=sys.stderr)` in tool code with `Context` logging. (~30 LOC)
- [ ] **S0.6** — **NEW** — Native build pipeline. Borrow `remctl-bridge.swift` → `_native/src/rem_eventkit.swift` and `remctl-private.m` → `_native/src/rem_reminderkit.m` with MIT attribution. Add `Makefile` targets: `make build-native` compiles both into `_native/bin/`. Create `_native/THIRD_PARTY_NOTICES.md`. Update `install.sh` to invoke `make build-native`. (~200 LOC of native + ~50 LOC of build tooling)

### Phase 1 — P0 capabilities (calendar lifecycle + SQLite reads + ReminderKit writes)

**Exit criteria**: SQLite read path live (replaces slow EventKit iteration for `list_calendars` / `search_reminders` / `get_reminders`). Calendar lifecycle complete. ReminderKit helper integrated. Subtasks / flagged / tags / sections work end-to-end.

Slices:
- [x] **S1.1** — Fix `is_default` in `CalendarManager.list()`. **DONE** in commit `117cc8a`.
- [ ] **S1.0** — **NEW** — Direct SQLite reader (`_native/sqlite.py`). Open Reminders.app DB read-only. Expose iterators for calendars, reminders, sections, tags, subtasks. Schema introspection at module load. Existing read tools (`list_calendars`, `get_reminders`, `search_reminders`, etc.) switched to SQLite path. EventKit reads kept as fallback. **Will replace the long-tail of S1.x work because many features come free from SQLite reads.** (~250 LOC)
- [ ] **S1.2** — `CalendarManager.create()` via Swift EventKit helper + `@mcp.tool() create_calendar`. (~100 LOC)
- [ ] **S1.3** — `CalendarManager.delete()` + `CalendarManager.update()` via helper + tools. (~120 LOC)
- [ ] **S1.4** — `_native/reminderkit.py` Python wrapper for the Obj-C helper subprocess. Smoke-tests against the borrowed `rem_reminderkit` binary built in S0.6. (~100 LOC of Python wrapping)
- [ ] **S1.5** — Subtask write paths: `create_reminder(parent_reminder_id)`, `set_parent`, `get_subtasks` (read from SQLite). (~120 LOC)
- [ ] **S1.6** — `set_flagged` tool. (~50 LOC — small because reads come from SQLite)
- [ ] **S1.7** — `set_tags` tool + tag filter on `get_reminders` (filter applied in SQLite query). (~80 LOC)
- [ ] **S1.8** — **NEW** — `assign_section` tool (private API). (~80 LOC)

### Phase 2 — MCP protocol primitives (Resources, Prompts, Sampling, Elicitation)

**Exit criteria**: Resources surface live SQLite-served views. Four canned prompts. Progress reporting on bulk ops. Elicitation guards destructive ops. Sampling pattern proven.

Slices:
- [ ] **S2.1** — Resources: `reminders://list/{id}`, `reminders://default`, `reminders://overdue`, `reminders://today`. All served from SQLite. (~120 LOC)
- [ ] **S2.2** — Prompts: `daily_review`, `weekly_retro`, `brain_dump_triage`, `agent_visibility_sync`. (~150 LOC)
- [ ] **S2.3** — Progress reporting wired into bulk-op skeleton (helpers `_native/bulk.py`); cancellation check between items. (~80 LOC)
- [ ] **S2.4** — Elicitation: `delete_calendar` (non-empty) and `bulk_delete_completed` prompt for confirmation via `ctx.elicit`. (~60 LOC)
- [ ] **S2.5** — Sampling: `triage_brain_dump` tool calls `ctx.session.create_message` to sort items by domain. (~100 LOC)

### Phase 3 — Feature parity (alarms, recurrence, bulk, multi-cal)

**Exit criteria**: Match `FradSer/apple-events` AND `viticci/remctl` on alarms, recurrence, bulk, multi-cal, completed-in-range.

Slices:
- [ ] **S3.1** — Time-based alarms via Swift EventKit helper. Tool: `set_alarm`. **Read path already covered by S1.0 SQLite reader** — alarms surface in `Reminder.alarms`. (~100 LOC)
- [ ] **S3.2** — Location-based alarms (structuredLocation, proximity). Tool: `set_location_alarm`. (~120 LOC)
- [ ] **S3.3** — Recurrence rules. Tool: `set_recurrence`. (~140 LOC)
- [ ] **S3.4** — Bulk ops: `bulk_complete`, `bulk_delete_completed`, `bulk_move`. Uses S2.3 + S2.4. (~120 LOC)
- [ ] **S3.5** — Multi-calendar query (SQLite WHERE list_id IN (...)). (~40 LOC — trivial in SQL)
- [ ] **S3.6** — `get_completed_in_range` query (SQLite). (~50 LOC)

### Phase 4 — Visibility-plane pilot + cross-cutting

**Exit criteria**: `Agents-<project>` lists auto-bootstrap. Optional streamable-HTTP. Security review done. Docs refreshed.

Slices:
- [ ] **S4.1** — `bootstrap_agent_list` tool + `agents://current` resource. AGENTS.md global rule for session-start auto-bootstrap. (~120 LOC + docs)
- [ ] **S4.2** — `TodoWrite` mirror — agent's internal todos sync into Reminders within 5s. (~150 LOC — stretch)
- [ ] **S4.3** — Streamable HTTP transport opt-in. (~80 LOC)
- [ ] **S4.4** — `docs/SECURITY-REVIEW.md` per OWASP MCP guide. Per-tool kill-switch flag map. (~60 LOC + docs)
- [ ] **S4.5** — README + MAP.md + AGENTS.md sweep. Tool catalog auto-generated. (~docs)

## Slice discipline

- Each slice ≤150 LOC diff. S0.4, S0.6, S1.0 are the upper bound — call out for review; may split.
- Each slice independently revertable.
- Each slice has tests at minimum smoke-level.
- `make lint && make check-architecture` green at slice close.
- Trunk strategy: commit directly to `main`. Signed. Version-bumped. Pushed.

## Risks

| Risk | Probability | Impact | Mitigation |
|---|---|---|---|
| SQLite schema changes between macOS releases | Low (historically stable) | High (reads break) | Schema introspection + warning + EventKit fallback. RemCTL faces same risk and survives. |
| ReminderKit private API breaks | Medium (long-term) | Medium (sections/subtasks/tags regress) | Helper is small (~100 LOC); rebuild against new headers. Degraded mode lets EventKit-backed tools continue. |
| Obj-C helper subprocess overhead surprises | Low | Low | Long-lived subprocess mode (S0.6 decision). Per-call mode is ~5-50ms which is fine for user ops. |
| FastMCP API churns | Medium | Medium | Pin to 1.27.x. Upgrade with intention. |
| Borrowed RemCTL code diverges from RemCTL's mainline | Medium | Low | Track upstream SHAs in `_native/THIRD_PARTY_NOTICES.md`. Re-sync deliberately. |
| Pydantic model changes break a tool's output shape | Medium | Medium | S0.4 explicit pytest pass at end. |
| Sampling latency / cost surprises | Low | Low | One tool; user-opt-in; logs token count. |

## Dependencies

- macOS 26+ for current ReminderKit signatures + SQLite schema. Pierce on 26.1 — fine.
- Xcode CLI tools (Swift + Obj-C compilers). Pierce has them.
- `mcp>=1.27` (PyPI). Pin range.
- PyObjC 10+. Already pinned for EventKit-fallback reads.
- No external services. No other team blocking.

## Estimated effort

- Phase 0: 6 slices, ~3 days (added S0.6 build pipeline).
- Phase 1: 8 slices (1.1 done; +1.0 SQLite reader; +1.8 sections), ~4 days.
- Phase 2: 5 slices, ~2 days.
- Phase 3: 6 slices (lighter than before — SQLite reader gave us much for free), ~2-3 days.
- Phase 4: 5 slices, ~2 days.
- **Total**: ~25 slices, ~13-14 days focused. Realistic clock-time: ~2-3 weeks.

## Frozen decisions (do not re-plan)

Once Phase 0 lands, these are locked:

- **Three-tier architecture**: SQLite reads + Swift EventKit helper + Obj-C ReminderKit helper.
- **Substrate**: FastMCP, `mcp>=1.27`, `_native/` package layout.
- **Models**: Pydantic field order in `models.py::Reminder` and `Calendar` (deeplink at tail; additions after Phase 0 require ADR).
- **Borrowed code**: `viticci/remctl::remctl-bridge.swift` and `remctl-private.m`. MIT attribution in `_native/THIRD_PARTY_NOTICES.md` and inline file headers.
- **Deeplink scheme**: `x-apple-reminderkit://REMCDReminder/{id}` / `x-apple-reminderkit://REMCDList/{id}`. Surfaced on every Reminder + Calendar response.
- **Tool naming**: snake_case action-first. New tools follow.
- **Color encoding**: 8 named palette + custom hex.
- **Trunk strategy**: no feature branches.
- **Opus everywhere**: all subagent spawns pass `model: "opus"`.

Changes require ADR + spec amendment + plan amendment.
