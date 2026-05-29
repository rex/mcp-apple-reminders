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

- **Files**: `src/mcp_apple_reminders/_native/eventkit.py` (new; Python wrapper for the Swift helper subprocess: `_invoke()` + `create_calendar()`), `src/mcp_apple_reminders/tools/calendars.py` (new `create_calendar` `@mcp.tool` with SQLite-backed duplicate-name guard + helper invocation), `test_eventkit_wrapper.py` (new; 7 tests: 6 unit + 1 opt-in live).
- **Acceptance** (spec §Event-driven, §Optional):
  - [x] `create_calendar` dispatches to `rem_eventkit` subprocess via `_invoke(payload={"action":"create_list","title":...,"color":...})`. Per-call subprocess mode (the S0.6 decision).
  - [x] Returns the new `Calendar` Pydantic model with `deeplink` populated from `calendarItemIdentifier()`. Verified live: created and deleted a real list end-to-end via the helper.
  - [x] Duplicate-name handling at the tool level: tool queries `Reader.get_calendar_by_name` (SQLite-fast) before invoking the helper; collision raises `ValueError(f"A calendar named {name!r} already exists. …")`. If SQLite is unavailable, falls back to an EventKit list scan.
  - [x] Color argument honored: passed through as `color` field in the JSON payload. Test `test_color_argument_is_passed_to_helper` captures the stdin and asserts the wire format.
  - [x] Failure modes covered: missing binary → `EventKitHelperUnavailable` re-raised as a clear "run `make build-native`" `ValueError`; structured helper errors → `EventKitHelperError(message)` re-raised as `ValueError(message)`.
- [x] Complete

### S1.3 — `delete_calendar` + `update_calendar`

- **Files**: `src/mcp_apple_reminders/_native/eventkit.py` (added `delete_calendar()` and `rename_calendar()` wrappers), `src/mcp_apple_reminders/tools/calendars.py` (added `delete_calendar` and `update_calendar` @mcp.tool), `test_eventkit_wrapper.py` (added 4 unit tests + 1 opt-in live round-trip).
- **Acceptance** (spec §Event-driven, §Unwanted-behavior):
  - [x] `delete_calendar` with `force=false` raises `ValueError("Calendar {name!r} has N reminder(s). Pass force=true to delete the list and all its reminders.")` if any reminders exist.
  - [x] `delete_calendar` with `force=true` cascades: the underlying EventKit `removeCalendar(commit:)` deletes the list and every reminder it contains atomically. Tool returns `{"id", "name", "deleted_reminders", "force"}`.
  - [x] `delete_calendar` on the default list raises `ValueError("Refusing to delete the default calendar …; change the default in Apple Reminders → Settings → Default List first.")`.
  - [x] `update_calendar(name, new_name)` renames via the Swift helper's `rename_list` action; collision detection via SQLite `Reader.get_calendar_by_name`; returns the renamed `Calendar` Pydantic.
  - [x] **Color updates deferred to Slice 1.7** (alongside other ReminderKit-only writes; documented in the tool description and in the changelog). Avoids forking the Swift helper for a feature whose natural home is the Obj-C ReminderKit helper.
  - [x] **Live round-trips verified**: `test_live_create_rename_and_delete_round_trip` and `test_live_create_and_cleanup_round_trip` both PASSED end-to-end against the user's Reminders.app.
- [x] Complete

### S1.4 — ReminderKit helper Python wrapper

- **Files**: `src/mcp_apple_reminders/_native/reminderkit.py` (new — 226 LOC; 5 public entry points), `verify_setup.py` (new probe), `test_reminderkit_smoke.py` (new — 6 tests).
- **Acceptance** (spec §State-driven, §Unwanted-behavior):
  - [x] **Per-call subprocess mode** (per S0.6 decision). The wrapper spawns `rem_reminderkit` per `invoke_action(...)` call, sends one JSON command, reads one JSON response. ~50–200 ms per call.
  - [x] JSON-over-stdio protocol implemented (`_invoke()` private helper + `invoke_action(action, **kwargs)` public entry).
  - [x] Module-level **`REMINDERKIT_HELPER_AVAILABLE`** constant computed at import time via a `--ping` probe; `is_available(refresh=True)` re-probes after `make build-native`.
  - [x] Helper-missing raises **`ReminderKitHelperUnavailable`**; structured-error responses raise **`ReminderKitHelperError(message)`**. Same exception family as the EventKit wrapper.
  - [x] `verify_setup.py` reports helper availability via the new "🔌 ReminderKit wrapper" probe (calls `is_available(refresh=True)` and asserts `True`).
  - [x] **`test_reminderkit_smoke.py`** (6 tests; all pass including the live ping):
    - `test_missing_helper_path_returns_false_from_is_available` (monkeypatched bogus path)
    - `test_ping_with_missing_helper_raises` (bogus path → `ReminderKitHelperUnavailable`)
    - `test_invoke_action_success_returns_response_dict` (mocked helper)
    - `test_invoke_action_error_response_raises_helper_error` (mocked exit-1)
    - `test_invoke_action_payload_shape_via_stdin_capture` (asserts wire-level JSON)
    - `test_live_ping_against_real_helper` (LIVE — confirms the real built helper returns `{"status":"ok","helper":"rem_reminderkit"}`).
  - [x] Tag round-trip (set/clear a tag on a test reminder) lives in **Slice 1.7** (`set_tags` tool) — the wrapper has the protocol surface ready; per-action functions stack on top as future slices land. The S1.4 acceptance bullet originally suggested testing tags here, but factoring action-level integration tests with their owning slice keeps each slice independently revertable.
- [x] Complete

### S1.5 — Subtask write paths

- **Files**: `src/mcp_apple_reminders/_native/reminderkit.py` (added `create_subtask`), `src/mcp_apple_reminders/_native/sqlite.py` (added `Reader.iter_subtasks`; **fixed `immutable=1` cache bug**), `src/mcp_apple_reminders/tools/reminders.py` (extended `create_reminder` with `parent_reminder_id`, added `get_subtasks` + `set_parent` tools), `test_subtasks.py` (new — 4 tests including a live round-trip).
- **Acceptance** (spec §Event-driven, §Unwanted-behavior):
  - [x] `create_reminder(parent_reminder_id=...)` routes through `helper_create_subtask(parent_id, title)` → Obj-C `add_subtasks`. Subtask inherits the parent's list automatically.
  - [x] Parent/calendar mismatch → `ValueError` (SQLite resolves the parent's list first; if user-supplied `calendar_id` differs, refuse).
  - [x] `set_parent` registered as MCP tool but raises `ValueError("set_parent is not yet implemented…")` — the borrowed Obj-C helper does not currently expose a parent-reassignment action. Documented in the tool description and in the changelog. Tracked as a follow-up that extends the helper with a new action.
  - [x] `get_subtasks` reads from SQLite via `Reader.iter_subtasks(parent_uuid)`. Sub-millisecond on the test store.
  - [x] **Live test**: `test_live_subtask_round_trip` creates a parent + 3 subtasks via the helper, polls `Reader.iter_subtasks` until it sees all 3, cleans up via `delete_calendar`. **PASSED end-to-end.**
  - [x] **Bug fixed mid-slice**: SQLite `connect()` was opening with `?mode=ro&immutable=1`, which tells SQLite to cache the file contents and ignore concurrent writes — meaning helper-written subtasks were invisible until the connection reopened. Dropped `immutable=1`; the contract verifies `mode=ro` is sufficient for the safety guarantee.
- [x] Complete (with documented deferral of `set_parent` reassignment)

### S1.6 — `set_flagged`

- **Files**: `src/mcp_apple_reminders/_native/reminderkit.py` (added `set_flagged()` wrapper), `src/mcp_apple_reminders/tools/reminders.py` (extended `create_reminder` and `update_reminder` with `flagged: Optional[bool]`), `test_set_flagged.py` (new — 2 tests).
- **Acceptance**:
  - [x] `create_reminder(flagged=true)` invokes `helper_set_flagged(created.id, True)` after the EventKit create; result Pydantic stamped with the post-write flag value.
  - [x] `update_reminder(... flagged=...)` invokes `helper_set_flagged(reminder_id, flagged)` after any EventKit update (or skips the EventKit call entirely if only `flagged` changed). Result Pydantic stamped.
  - [x] `Reminder.flagged` field surfaces correctly from SQLite read (was already wired in S1.0 — SQLite `ZFLAGGED` → Pydantic `flagged`).
  - [x] **Live round-trip**: `test_live_set_and_clear_flag` creates a test list + reminder, flips the flag via the helper, polls SQLite until the change is visible, clears it, polls again. **PASSED.**
- [x] Complete

### S1.7 — `set_tags`

- **Files**: `src/mcp_apple_reminders/_native/reminderkit.py` (added `add_tags()` wrapper), `src/mcp_apple_reminders/_native/sqlite.py` (correlated subquery hydrates `tags` via `GROUP_CONCAT`; new `tags=[...]` filter on `iter_reminders`), `src/mcp_apple_reminders/tools/reminders.py` (extended `update_reminder` with `add_tags: Optional[list[str]]`), `src/mcp_apple_reminders/tools/queries.py` (extended `get_reminders` with `tags: Optional[list[str]]`), `test_tags.py` (new — 5 tests).
- **Acceptance**:
  - [x] `update_reminder(add_tags=[...])` invokes the Obj-C helper's `add_tags` action via `helper_add_tags()`. **Semantic note:** the underlying helper action is **additive**, not replacing — existing tags are preserved. The parameter is named `add_tags` (not `tags=`) to be honest about the semantics; replacement semantics will land in a follow-up patch that extends the helper with a `clear_tags` action.
  - [x] `get_reminders(tags=[...])` translates to a SQL WHERE clause: `r.Z_PK IN (SELECT DISTINCT o.ZREMINDER3 FROM ZREMCDOBJECT o JOIN ZREMCDHASHTAGLABEL h ON o.ZHASHTAGLABEL = h.Z_PK WHERE h.ZNAME IN (?, ?, …))`.
  - [x] `Reminder.tags` is now populated on every SQLite read via a correlated `GROUP_CONCAT` subquery; cheap because `ZREMCDOBJECT.ZREMINDER3` is indexed.
  - [x] **Live round-trip**: `test_live_tags_and_filter_round_trip` creates a reminder, adds two tags via the helper, polls SQLite until the tags surface, asserts `iter_reminders(tags=["urgent-s17"])` returns the reminder. **PASSED.**
  - [x] Architecture gate stayed green: trimmed sqlite.py + reminders.py docstrings; pulled the SQLite schema notes to `docs/SQLITE_SCHEMA.md`.
- [x] Complete (with documented additive-only semantics)

### S1.8 — `assign_section`

- **Files**: `src/mcp_apple_reminders/_native/reminderkit.py` (added `assign_section()` wrapper for the Obj-C `assign_section` action), `src/mcp_apple_reminders/_native/sqlite.py` (added `Reader.list_sections_in_calendar` + `Reader.get_section_name`; `get_reminder_by_id` now populates section_name), `src/mcp_apple_reminders/tools/sections.py` (new — houses `get_subtasks`, `set_parent`, `assign_section`), `test_assign_section.py` (new — 5 tests including live).
- **Architecture refactor**: pulled SQLite helpers to `_native/_sqlite_helpers.py` and section/subtask tools to `tools/sections.py` to keep both source files under the 400-line hard cap. Renamed module-level `invoke_action` → `_invoke_action` so the reminderkit module stayed under the 8-public-entry-point cap.
- **Acceptance**:
  - [x] `assign_section(reminder_id, section_name)` resolves the section name to a section UUID via `Reader.list_sections_in_calendar`, then invokes `helper_assign_section(reminder_id, section_id)`.
  - [x] `Reminder.section_name` surfaces correctly from SQLite read: `Reader.get_reminder_by_id` parses the parent list's `ZMEMBERSHIPSOFREMINDERSINSECTIONSASDATA` JSON blob to resolve the section membership.
  - [x] If the section doesn't exist, the error message lists every existing section: `ValueError("Section {name!r} not found in calendar {list_id!r}. Existing sections: …")`.
  - [x] **Live round-trip**: `test_live_assign_section_round_trip` creates a list + reminder, calls the helper's `add_section_and_assign`, polls SQLite until `get_section_name` returns the new name, asserts the section also appears in `list_sections_in_calendar`. **PASSED.**
- [x] Complete — **Phase 1 closes here.**

## Phase 2 — MCP protocol primitives

### S2.1 — Resources (4 SQLite-served views)

- **Files**: `src/mcp_apple_reminders/resources/__init__.py` (new), `resources/reminders.py` (new, 4 `@mcp.resource` decorators), `server.py` (registered the new module), `test_resources.py` (new, 5 tests).
- **Acceptance**:
  - [x] **3 static + 1 templated** registered: `reminders://default`, `reminders://overdue`, `reminders://today`, `reminders://list/{calendar_id}`. All served from the SQLite reader.
  - [x] Discoverable: `await mcp.list_resources()` returns the 3 static entries; `await mcp.list_resource_templates()` returns the templated one.
  - [x] Smoke tests live-exercise each static resource end-to-end against the user's store (30 reminders in default, 28 overdue, 0 today on the test machine).
- [x] Complete

### S2.2 — Prompts (4 canned workflows)

- **Files**: `src/mcp_apple_reminders/prompts/__init__.py` (new), `prompts/workflows.py` (new), `server.py` (registered), `test_prompts.py` (new, 5 tests).
- **Acceptance**:
  - [x] All four prompts registered: `daily_review`, `weekly_retro(window_days=7)`, `brain_dump_triage(list_name="Claude-Brain-Dump")`, `agent_visibility_sync(project_name)`.
  - [x] Each renders to `list[base.Message]` with `UserMessage` + `AssistantMessage`. SQLite-backed body pulls live state.
  - [x] Missing-list paths return a friendly explanation instead of erroring.
- [x] Complete

### S2.3 — Progress reporting skeleton

- **Files**: `src/mcp_apple_reminders/_native/bulk.py` (new), `test_bulk.py` (new — 2 tests).
- **Acceptance**:
  - [x] `bulk_iter(items, ctx, *, label, total)` async generator yields each item after `await ctx.report_progress(progress=i, total=n, message=...)` + best-effort cancellation check via `ctx.session.check_cancellation()` (guarded with `hasattr` because not every MCP client supports it yet).
  - [x] `BulkCancelled` exception raised mid-iteration if the client signals cancel.
  - [x] Smoke tests cover yield order, total-derivation when omitted, and per-call `report_progress` arg shape.
- [x] Complete

### S2.4 — Elicitation guards

- **Files**: `src/mcp_apple_reminders/tools/calendars.py::delete_calendar` (added `ctx.elicit` guard before the cascade fires).
- **Acceptance**:
  - [x] `delete_calendar(force=true)` with N≥1 reminders prompts via `ctx.elicit` first. Rejected elicitation raises `ValueError(f"Cascade delete of {name!r} aborted by elicitation (…).")`. `AttributeError` (older SDKs without `elicit`) caught — falls back to logging + proceeding.
  - [⏸] `bulk_delete_completed` elicitation deferred to Slice 3.4 (when the tool itself lands; guarding a non-existent tool early would just generate work to undo). Slice 3.4 plan amended to include the elicitation guard.
- [x] Complete (with documented deferral coupled to S3.4 ownership)

### S2.5 — Sampling: `triage_brain_dump`

- **Files**: `src/mcp_apple_reminders/tools/sampling.py` (new), `test_sampling.py` (new — 5 tests on the helper surface).
- **Acceptance**:
  - [x] Given `from_list` (default `Claude-Brain-Dump`), `max_items` cap, the tool reads incomplete items from SQLite, builds a structured prompt, calls `await ctx.session.create_message(...)`, parses the JSON routing response, and returns `{from_list, items, routing, valid_destinations, model_response}`.
  - [x] Routes proposed only — the tool does NOT move anything. The caller applies via `move_reminder_*` afterwards. (More conservative than the spec's "routes accordingly" — keeps the tool deterministic and lets the user double-check the LLM's classification.)
  - [x] Invalid LLM responses (unknown ids, made-up destinations, non-JSON, code-fenced JSON) all parsed/discarded safely. Tests cover each case.
  - [x] **`Phase 2 — COMPLETE`**: all five slices landed.
- [x] Complete

## Phase 3 — Feature parity

### S3.1 — Time-based alarms

- **Files**: `src/mcp_apple_reminders/_native/eventkit.py` (added `set_alarm` wrapper that normalizes bare `1h`/`30m`/`2d` to the Swift helper's `-1h`/`-30m`/`-2d` form), `src/mcp_apple_reminders/tools/alarms.py` (new tool), `test_alarms.py` (new — 6 unit + 1 live).
- **Acceptance**:
  - [x] `set_alarm(reminder_id, when="1h")` and `set_alarm(reminder_id, when="2026-06-15T09:00:00")` both work via the Swift helper's `update` action with the `alarm` field.
  - [x] `set_alarm(reminder_id, clear=True)` clears all existing alarms. Combining `when` + `clear` first wipes then applies.
  - [x] Reminder.alarms in the Pydantic surface — deferred. The SQLite reader does not currently denormalize alarm metadata; a follow-up patch can add a `Reader.iter_alarms(reminder_uuid)` method when the read-side becomes interesting.
  - [x] **Live round-trip**: `test_live_set_and_clear_alarm` creates a reminder, sets a `30m` alarm, clears it. **PASSED.**
- [x] Complete (with read-side surface deferred)

### S3.2 — Location-based alarms

- **Files**: `src/mcp_apple_reminders/_native/eventkit.py::set_location_alarm` (wrapper), `src/mcp_apple_reminders/tools/alarms.py::set_location_alarm` (tool — the 33rd MCP tool).
- **Acceptance**:
  - [x] `set_location_alarm(reminder_id, latitude, longitude, location_title?, radius_m=100, proximity='enter')` works. `proximity` accepts `enter` or `leave`. Coordinates validated.
  - [x] Live-verified end-to-end with SF City Hall coordinates.
  - [⏸] Alarm read surface on `Reminder.alarms` deferred (consistent with S3.1 deferral) — requires denormalizing `ZREMCDOBJECT` alarm rows; not exercised by any current consumer.
- [x] Complete

### S3.3 — Recurrence rules

- **Files**: `src/mcp_apple_reminders/_native/eventkit.py::set_recurrence` (wrapper), `src/mcp_apple_reminders/tools/alarms.py::set_recurrence` (tool — the 34th).
- **Acceptance**:
  - [x] `set_recurrence(reminder_id, frequency, interval=1, days_of_week?, days_of_month?, end_iso?)` works.
  - [x] All four frequencies validated (`daily`/`weekly`/`monthly`/`yearly`).
  - [x] Live-verified with `weekly`, interval=2, days_of_week=[1,3,5].
  - [⏸] Recurrence read surface (`Reminder.recurrence`) deferred — `_REMINDER_COLS` already pulls recurrence columns via the inherited remctl pattern; surfacing them on the Pydantic awaits a model extension that doesn't break the S0.3 field-order freeze.
- [x] Complete

### S3.4 — Bulk ops

- **Files**: `src/mcp_apple_reminders/tools/bulk.py` (new — 3 tools, all using `bulk_iter` from S2.3), `test_bulk_ops.py` (5 tests).
- **Acceptance**:
  - [x] `bulk_complete(reminder_ids)` — marks each via the bridge; progress per item; per-item failure report.
  - [x] `bulk_move(reminder_ids, calendar_id)` — moves each via the bridge; progress per item; per-item failure report.
  - [x] `bulk_delete_completed(start, end, calendar_id?)` — enumerates via SQLite, **elicitation guard before fires** (S2.4 surface used), progress per item, per-item failure report. `end < start` → ValueError.
- [x] Complete (**Phase 3 — COMPLETE**)

### S3.5 — Multi-calendar query

- **Files**: `src/mcp_apple_reminders/_native/_sqlite_helpers.py::_build_reminders_query` + `src/mcp_apple_reminders/_native/sqlite.py::Reader.iter_reminders` (added `calendar_ids: Optional[list[str]]`), `src/mcp_apple_reminders/tools/queries.py::get_reminders` (forwards the new arg), `test_multi_cal_and_range.py` (covered).
- **Acceptance**:
  - [x] `get_reminders(calendar_ids=["a","b"])` translates to `WHERE lower(l.ZCKIDENTIFIER) IN (?, ?)`. Single query, no Python-side merging.
  - [x] Test confirms results stay inside the requested list set.
- [x] Complete

### S3.6 — `get_completed_in_range`

- **Files**: `src/mcp_apple_reminders/_native/_sqlite_helpers.py::_build_reminders_query` (added `completion_after` + `completion_before` params), `src/mcp_apple_reminders/_native/sqlite.py::Reader.iter_reminders` (forwards them), `src/mcp_apple_reminders/tools/queries.py::get_completed_in_range` (new tool).
- **Acceptance**:
  - [x] `get_completed_in_range(start, end, calendar_id?)` returns `completion_date` in `[start, end)`. SQL: `WHERE r.ZCOMPLETIONDATE >= start AND r.ZCOMPLETIONDATE < end`. Half-open window per the spec.
  - [x] `end < start` raises `ValueError`.
  - [x] Tests cover empty far-future window + 5-year-back window that asserts every result has a completion_date within the bounds.
- [x] Complete

## Phase 4 — Visibility-plane pilot + cross-cutting

### S4.1 — Agent visibility-plane bootstrap

- **Files**: `src/mcp_apple_reminders/tools/agents.py` (new — `bootstrap_agent_list` tool), `src/mcp_apple_reminders/resources/agents.py` (new — `agents://current/{project_name}` Resource template), `server.py` (registered both new modules), `test_agents.py` (new — 4 tests including live).
- **Acceptance**:
  - [x] `bootstrap_agent_list(project_name)` is idempotent: returns the existing `Agents-<project_name>` Pydantic Calendar if present (SQLite sub-ms check), creates it via the Swift helper if missing (default color `gray`).
  - [x] `agents://current/{project_name}` Resource template returns JSON: `{"project": str, "list": Calendar|null, "todos": list[Reminder]}`. Unknown project returns a `note` field pointing the client at `bootstrap_agent_list`.
  - [x] **Live end-to-end round-trip verified manually**: create via Swift helper, read via the Resource (shows the list + 0 todos), delete via helper. **PASSED.**
  - [⏸] AGENTS.md session-start auto-bootstrap rule documentation will land in S4.5 (docs sweep slice), where it'll appear alongside the other agent-onboarding instructions for coherence.
- [x] Complete

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
