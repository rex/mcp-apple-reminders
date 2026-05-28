# Tasks — 002-modernize-and-foundation

> Concrete task list, one per slice. Implementer executes from here.
> TASK_STATE.md tracks the ACTIVE slice; this file is the full catalog.

## How to use

- Each acceptance bullet is EARS-notation from `spec.md`.
- Check the box as each lands.
- Add `(agent: <name>)` when claimed.
- Add `(blocked: <reason>)` if blocked.

## Phase 0 — Modernize the platform

### S0.1 — Upgrade mcp + pyobjc

- **Files**: `pyproject.toml`, `requirements.txt`, `verify_setup.py`
- **Acceptance**:
  - [x] `mcp>=1.27,<2` pinned (mcp 1.27.1 installed).
  - [x] `verify_setup.py` confirms `mcp version >= 1.27` (via `importlib.metadata.version`).
  - [x] `./venv/bin/python3 -m mcp_apple_reminders` starts cleanly (waits on stdio as expected).
  - [x] No PyObjC deprecation warnings on macOS 26.1 (pyobjc 12.1; verify_setup.py treats DeprecationWarning as error during import).
- [x] Complete

### S0.2 — Rename libs/pyremindkit → src/mcp_apple_reminders/_native

- **Files**: moved files via `git mv`; deleted `libs/pyremindkit/{VENDOR.md, README.upstream.md, LICENSE, MANIFEST.in, Makefile, README.md, examples/, requirements/, setup.py, pyproject.toml, .gitignore, .pre-commit-config.yaml}`. Updated all imports (server, formatting, tools/queries, all test_*.py, verify_setup, Makefile, AGENTS.md, MAP.md).
- **Acceptance**:
  - [x] `libs/` directory removed.
  - [x] `from mcp_apple_reminders._native import RemindKit, Reminder, Priority, Calendar, CalendarManager` works (transitional aliases — internal module names unchanged until S0.3+0.4 reshape further).
  - [x] `server.py` no longer mutates `sys.path` (also removed from all test_*.py).
  - [x] All tests still pass (test_mcp_tools + test_e2e: 5 passed); `make lint && make check-architecture` green.
- [x] Complete

### S0.3 — Pydantic models (+ deeplink verification)

- **Files**: `src/mcp_apple_reminders/models.py` (new), `test_models.py` (new). Converters live alongside the models rather than in `_native/_internal.py` to keep the EventKit dependency out of the model module's import graph (gated via `TYPE_CHECKING`).
- **Acceptance**:
  - [x] `models.py` defines Pydantic `Calendar` (6 fields including `deeplink`) and `Reminder` (18 fields including `deeplink`, `section_name`, `parent_reminder_id`, `subtasks`, `tags`). Both `frozen=True` + `extra="forbid"`.
  - [x] Helper `reminder_deeplink(uuid)` and `calendar_deeplink(uuid)` exist; opt-in `open` round-trip test guards them (skipped unless `REM_DEEPLINK_SMOKE=1`).
  - [x] Converter `eventkit_reminder_to_pydantic(ek_reminder) -> Reminder` exists and exercises against a real EKReminder; `calendarItemIdentifier()` populates `id` and `deeplink` correctly. `eventkit_calendar_to_pydantic` also added.
  - [x] Field order locked at end of this slice; **CONTRACT FREEZE** guarded by two regression tests (`test_calendar_field_order_is_canonical`, `test_reminder_field_order_is_canonical`).
- [x] Complete

### S0.4 — FastMCP migration

- **Files**: `src/mcp_apple_reminders/server.py` (full rewrite, 85 LOC → 50 LOC), every `tools/*.py` (decorator migration), new `lifespan.py`, `tools/__init__.py` simplified, `__init__.py` re-export update.
- **Acceptance** (spec §Ubiquitous):
  - [x] Server is built on `FastMCP("mcp-apple-reminders", lifespan=app_lifespan)`.
  - [x] All 22 existing tools registered via `@mcp.tool()` decorator (verified via `await mcp.list_tools()` enumeration).
  - [x] Lifespan owns the single `RemindKit` instance via `AppContext` dataclass; accessed through `ctx.request_context.lifespan_context.bridge`.
  - [x] Every tool signature: `(arg1, ..., ctx: Context) -> SomePydanticModel` (list/Optional variants where appropriate).
  - [x] Tool **names** + **semantic** input schemas preserved: identical parameter sets and required lists across all 22 tools. FastMCP normalizes optional params to `anyOf [type, null]` (vs the old `properties` + missing-from-`required` style) — semantic equivalence; the diff is syntactic. Verified against the originals in `MCP_TOOLS_SNAPSHOT.md`.
  - [x] `make lint && make check-architecture && pytest test_mcp_tools.py test_e2e.py test_models.py`: 15 passed, 1 skipped, 0 failures.
- [x] Complete

### S0.5 — Context-based logging

- **Files**: `tools/reminders.py`, `tools/queries.py`, `tools/workflow.py`. (`tools/calendars.py` stays read-only; nothing to log.) `lifespan.py` keeps its pre-session `sys.stderr` permission-error path.
- **Acceptance**:
  - [x] Zero `print(..., file=sys.stderr)` calls in `src/mcp_apple_reminders/tools/`.
  - [x] Tool handlers use `await ctx.info()` (state changes), `ctx.warning()` (empty results, destructive ops about to fire), `ctx.error()` (failed ops), `ctx.debug()` (read counts, filter shape).
  - [x] Server startup retains its `sys.stderr` permission-error path in `lifespan.py` (no MCP session yet to log through).
- [x] Complete

### S0.6 — Native build pipeline (Swift + Obj-C helpers from RemCTL)

- **Files**: `src/mcp_apple_reminders/_native/src/rem_eventkit.swift` (borrowed from `viticci/remctl::remctl-bridge.swift`, 512 LOC with header), `src/mcp_apple_reminders/_native/src/rem_reminderkit.m` (borrowed from `remctl-private.m`, 1456 LOC with header), `src/mcp_apple_reminders/_native/THIRD_PARTY_NOTICES.md` (MIT attribution + upstream pin), `Makefile` (`build-native`, `clean-native`), `install.sh` (invokes `make build-native` after the pip install), `verify_setup.py` (binary probe + `--ping`), `VIBE.yaml::architecture.exclude_globs` (vendored upstream sources, documented Pierce-approved exception), `.gitignore` (ignores compiled `_native/bin/*`).
- **Acceptance** (spec §Ubiquitous re borrowed code):
  - [x] `_native/src/rem_eventkit.swift` and `_native/src/rem_reminderkit.m` present with attribution headers (upstream URL, commit SHA `baaa57b…`, RemCTL 1.0.3, license + local-modification list).
  - [x] `_native/THIRD_PARTY_NOTICES.md` contains the verbatim MIT license + file-by-file mapping + upstream commit SHA.
  - [x] `make build-native` compiles both binaries (≈50–200 ms each on M-series); deposits them in `_native/bin/rem_eventkit` and `_native/bin/rem_reminderkit`; runs `--ping` on each to confirm.
  - [x] `install.sh` invokes `make build-native` after the pip install (gracefully degrades if swiftc/clang missing).
  - [x] `verify_setup.py` confirms both binaries exist and exit 0 on `--ping` invocation, asserting the `{"status":"ok"}` payload.
  - [x] **Helper-process lifetime mode decision**: **per-call subprocess** for now (simpler; ~50–100 ms per call which is fine for user-scale interactive ops). Long-lived mode can be retrofitted in `_native/bridge.py` (S1.4) without changing the JSON protocol if profiling shows it matters. Decision recorded here and re-visited in S1.4.
- [x] Complete

## Phase 1 — P0 capabilities

### S1.1 — is_default fix (DONE in commit 117cc8a)

- **Acceptance**:
  - [x] `is_default` is `True` for exactly one calendar in `list_calendars`.
  - [x] Test 6 in `test_crud_calendars.py` enforces this.

### S1.0 — Direct SQLite reader

- **Files**: `src/mcp_apple_reminders/_native/sqlite.py` (new, 290 LOC; module-shape gate green via the single `Reader` facade class), `src/mcp_apple_reminders/lifespan.py` (resolves store path at startup, exposes `app_context.open_sqlite()`), `src/mcp_apple_reminders/tools/{calendars,reminders,queries}.py` (read-path tools route through SQLite + EventKit fallback), `test_sqlite_reader.py` (new, 10 tests).
- **Acceptance** (spec §Ubiquitous re reads):
  - [x] `_native/sqlite.py::connect()` opens the largest `Data-*.sqlite` in the store dir with `file:...?mode=ro&immutable=1`.
  - [x] `Reader.schema_summary()` captures the table list at module load; `required_present` flag and `missing` list let callers diagnose drift.
  - [x] `Reader.iter_reminders`, `Reader.list_calendars`, `Reader.search_calendars`, `Reader.search_reminders`, `Reader.get_calendar_by_id`, `Reader.get_calendar_by_name`, `Reader.get_reminder_by_id` cover the read-tool surface. ReminderKit-only fields (`subtasks`, `tags`, `section_name`, `parent_reminder_id`) ride along on the model with sane defaults — fully populated in slices 1.5–1.8.
  - [x] All read tools (`list_calendars`, `get_calendar`, `get_calendar_by_id`, `search_calendars`, `get_reminders`, `search_reminders`, `get_next_reminder`, `get_overdue_reminders`, `get_today_reminders`, `get_reminder`) switched to SQLite-first path with EventKit fallback. `get_default_calendar` stays on EventKit (source-of-truth for default-list selection).
  - [x] `RemindersDBUnavailable` exception raised on missing/broken store; each tool catches it, logs `ctx.warning("SQLite read path unavailable …; falling back to EventKit.")`, and serves from `app.bridge`.
  - [x] Tests: `test_sqlite_reader.py` 10 passed (find_db_path, schema, list_calendars, latency<100ms, iter+deeplinks, completed filter, search, get_by_id round-trip, missing UUID → None, bogus path → exception). `test_list_calendars_under_100ms_latency` measured ~0.6 ms on a 27-calendar / 2200-reminder store.
  - [x] **Deeplink UUID equivalence verified end-to-end** (closes the S0.3 open question): `EKReminder.calendarItemIdentifier()` and SQLite `ZCKIDENTIFIER` produce the same UUID for the same reminder; same for calendars. Verified live on 2026-05-28.
- [x] Complete

### S1.2 — `create_calendar`

- **Files**: `_native/eventkit.py` (Python wrapper for the Swift helper), `tools/calendars.py`
- **Acceptance** (spec §Event-driven, §Optional):
  - [ ] `create_calendar` dispatches to `rem_eventkit` subprocess with a JSON request.
  - [ ] Returns the new `Calendar` (with `deeplink`).
  - [ ] Duplicate-name handling: helper returns structured error; Python wrapper raises `ValueError`.
  - [ ] Color argument honored (named palette or hex).
- [ ] Complete

### S1.3 — `delete_calendar` + `update_calendar`

- **Files**: `_native/eventkit.py` (extend Python wrapper), `tools/calendars.py`
- **Acceptance** (spec §Event-driven, §Unwanted-behavior):
  - [ ] `delete_calendar` with `force=false` errors if any reminders exist.
  - [ ] `delete_calendar` with `force=true` deletes all + the calendar.
  - [ ] `delete_calendar` on default calendar rejects.
  - [ ] `update_calendar` updates `name`/`color`; returns updated.
- [ ] Complete

### S1.4 — ReminderKit helper Python wrapper

- **Files**: `_native/reminderkit.py` (new)
- **Acceptance** (spec §State-driven, §Unwanted-behavior):
  - [ ] Long-lived (or per-call, per S0.6 decision) subprocess management of `rem_reminderkit`.
  - [ ] JSON-over-stdio protocol: send `{"action": "...", ...}` on stdin; read response from stdout.
  - [ ] If binary missing or fails to start: module sets `REMINDERKIT_HELPER_AVAILABLE = False`; calls raise `ReminderKitHelperUnavailable`.
  - [ ] `verify_setup.py` reports helper availability.
  - [ ] Smoke test (`test_reminderkit_smoke.py`): ping the helper, set/clear a tag on a test reminder, assert round-trip.
- [ ] Complete

### S1.5 — Subtask write paths

- **Files**: `_native/reminderkit.py` (subtask write methods), `_native/bridge.py`, `tools/reminders.py`, `tools/queries.py`, `test_subtasks.py`
- **Acceptance** (spec §Event-driven, §Unwanted-behavior):
  - [ ] `create_reminder(parent_reminder_id=...)` routes to ReminderKit helper; sets parent in the parent's calendar.
  - [ ] Parent/calendar mismatch → `ValueError`.
  - [ ] `set_parent` reassigns/detaches.
  - [ ] `get_subtasks` reads from SQLite (fast).
  - [ ] Test: parent + 3 subtasks + reparent + detach + cleanup.
- [ ] Complete

### S1.6 — `set_flagged`

- **Files**: `tools/reminders.py`, `_native/reminderkit.py`
- **Acceptance**:
  - [ ] `create_reminder(flagged=true)` and `update_reminder(... flagged=...)` set the flag via the helper.
  - [ ] `Reminder.flagged` field surfaces correctly (from SQLite read).
- [ ] Complete

### S1.7 — `set_tags`

- **Files**: `tools/reminders.py`, `tools/queries.py`, `_native/reminderkit.py`
- **Acceptance**:
  - [ ] `update_reminder(tags=[...])` replaces the tag set via the helper.
  - [ ] `get_reminders(tags=[...])` filter applied as a SQL WHERE clause.
- [ ] Complete

### S1.8 — `assign_section`

- **Files**: `tools/reminders.py`, `_native/reminderkit.py`
- **Acceptance**:
  - [ ] `assign_section(reminder_id, section_name)` moves the reminder via helper.
  - [ ] `Reminder.section_name` surfaces correctly (from SQLite read).
  - [ ] If section doesn't exist in the calendar, error message lists existing sections.
- [ ] Complete

## Phase 2 — MCP protocol primitives

### S2.1 — Resources (4 SQLite-served views)

- **Files**: `src/mcp_apple_reminders/resources/__init__.py`, `resources/reminders.py`, registration in `server.py`
- **Acceptance**:
  - [ ] `reminders://list/{id}`, `reminders://default`, `reminders://overdue`, `reminders://today` registered, all served from SQLite (~10ms each).
  - [ ] Resources are discoverable via the client's resource-listing call.
- [ ] Complete

### S2.2 — Prompts (4 canned workflows)

- **Files**: `src/mcp_apple_reminders/prompts/__init__.py`, `prompts/*.py`
- **Acceptance**:
  - [ ] `daily_review`, `weekly_retro`, `brain_dump_triage`, `agent_visibility_sync` registered.
  - [ ] Each renders to MCP `Prompt` messages with documented arguments.
- [ ] Complete

### S2.3 — Progress reporting skeleton

- **Files**: `_native/bulk.py`
- **Acceptance**:
  - [ ] `bulk_iter(items, ctx)` yields each item with progress reporting + cancellation check.
  - [ ] Smoke test against a fake list of 25 items.
- [ ] Complete

### S2.4 — Elicitation guards

- **Files**: `tools/calendars.py::delete_calendar`, `tools/reminders.py::bulk_delete_completed`
- **Acceptance** (spec §Event-driven re destructive ops):
  - [ ] `delete_calendar(force=true)` with N≥1 reminders prompts via `ctx.elicit` first.
  - [ ] `bulk_delete_completed` prompts via `ctx.elicit`.
- [ ] Complete

### S2.5 — Sampling: `triage_brain_dump`

- **Files**: `tools/sampling.py` (new), test
- **Acceptance**:
  - [ ] Given `from_list` (default Claude-Brain-Dump), the tool calls `ctx.session.create_message` to classify each item by domain.
  - [ ] Routes accordingly (with elicitation if confidence < threshold).
  - [ ] Test mocks the sampling call.
- [ ] Complete

## Phase 3 — Feature parity

### S3.1 — Time-based alarms

- **Files**: `tools/alarms.py` (new), `_native/eventkit.py` (extend Python wrapper)
- **Acceptance**:
  - [ ] `set_alarm(reminder_id, relative_offset=...)` or `set_alarm(reminder_id, absolute_date=...)` works.
  - [ ] Reminder.alarms surfaces from SQLite read.
- [ ] Complete

### S3.2 — Location-based alarms

- **Files**: `tools/alarms.py`, `models.py` (Alarm with location/proximity)
- **Acceptance**:
  - [ ] `set_location_alarm(reminder_id, location, proximity)` works for enter/leave.
- [ ] Complete

### S3.3 — Recurrence rules

- **Files**: `tools/recurrence.py`, `models.py` (RecurrenceRule)
- **Acceptance**:
  - [ ] `set_recurrence(reminder_id, frequency, interval, end_*)` works.
  - [ ] All four frequencies + end conditions.
- [ ] Complete

### S3.4 — Bulk ops

- **Files**: `tools/bulk.py`. Uses S2.3 + S2.4.
- **Acceptance**:
  - [ ] `bulk_complete`, `bulk_delete_completed`, `bulk_move`. Progress + elicitation as required.
- [ ] Complete

### S3.5 — Multi-calendar query

- **Files**: `_native/sqlite.py::get_reminders` (accept `calendar_ids`)
- **Acceptance**:
  - [ ] `get_reminders(calendar_ids=["a","b"])` returns merged results from one SQL query.
- [ ] Complete

### S3.6 — `get_completed_in_range`

- **Files**: `tools/queries.py`, `_native/sqlite.py`
- **Acceptance**:
  - [ ] `get_completed_in_range(start, end, calendar_id?)` returns matches with `completion_date` in `[start, end)`.
- [ ] Complete

## Phase 4 — Visibility-plane pilot + cross-cutting

### S4.1 — Agent visibility-plane bootstrap

- **Files**: `tools/agents.py`, `resources/agents.py`, AGENTS.md sweep
- **Acceptance**:
  - [ ] `bootstrap_agent_list(project_name)` creates `Agents-<project_name>` if missing.
  - [ ] `agents://current` resource exposes the current project's list.
  - [ ] AGENTS.md documents the session-start auto-bootstrap rule.
- [ ] Complete

### S4.2 — TodoWrite mirror (STRETCH)

- **Files**: `tools/agents.py::sync_todos`
- **Acceptance**:
  - [ ] TodoWrite payload mirrors into `Agents-<project>` reminders within 5s.
- [ ] Complete

### S4.3 — Streamable HTTP transport (opt-in)

- **Files**: `server.py`, `VIBE.yaml`
- **Acceptance**:
  - [ ] `VIBE.yaml::server.transport: streamable_http` boots on HTTP.
- [ ] Complete

### S4.4 — Security review + kill switches

- **Files**: `docs/SECURITY-REVIEW.md`, `tools/_kill_switch.py`
- **Acceptance**:
  - [ ] SECURITY-REVIEW.md per OWASP guide.
  - [ ] Per-tool kill switch consults `VIBE.yaml::agents.tool_flags`.
- [ ] Complete

### S4.5 — Docs sweep

- **Files**: README.md, MAP.md, AGENTS.md, `docs/TOOLS.md` (auto-generated)
- **Acceptance**:
  - [ ] Capability matrix in README current.
  - [ ] Tool catalog auto-generates.
- [ ] Complete

## Done when

- [ ] All Phase 0–4 acceptance bullets checked.
- [ ] `make check-if-the-agent-can-consider-this-task-completed` green.
- [ ] No open blockers in `TASK_STATE.md §3`.
- [ ] `mem:core` reflects three-tier layout + SQLite read path + helper subprocesses.
- [ ] AGENTS.md §9 gotchas re-audited.
- [ ] `_native/THIRD_PARTY_NOTICES.md` reviewed against current RemCTL SHAs.
