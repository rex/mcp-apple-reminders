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

- **Files**: `pyproject.toml`, `requirements.txt`, `verify_setup.py` (version pins)
- **Acceptance**:
  - [ ] `mcp>=1.27,<2` pinned.
  - [ ] `verify_setup.py` confirms `mcp.__version__ >= 1.27`.
  - [ ] `./venv/bin/python3 -m mcp_apple_reminders` starts cleanly on the new mcp version.
  - [ ] No PyObjC deprecation warnings on macOS 26.1.
- [ ] Complete

### S0.2 — Rename libs/pyremindkit → src/mcp_apple_reminders/_native

- **Files**: move libs/pyremindkit/src/pyremindkit/{core,calendars,models,_internal,__init__}.py → src/mcp_apple_reminders/_native/{eventkit,calendars,models,_internal,__init__}.py (rename `core.py` → `eventkit.py`). Delete `libs/pyremindkit/*` (VENDOR.md, LICENSE, etc.). Update all imports.
- **Acceptance**:
  - [ ] `libs/` directory removed.
  - [ ] `from mcp_apple_reminders._native import RemindKit, Reminder, Priority, Calendar, CalendarManager` works.
  - [ ] `server.py` no longer mutates `sys.path` (the vendored-dep import dance is unnecessary).
  - [ ] All tests still pass.
  - [ ] `make check-architecture` green.
- [ ] Complete

### S0.3 — Pydantic models

- **Files**: `src/mcp_apple_reminders/models.py` (new), `_native/_internal.py` (add converters)
- **Acceptance**:
  - [ ] `models.py` defines Pydantic `Calendar`, `Reminder` with the full field set from `design.md::API surface`.
  - [ ] `Reminder.parent_reminder_id`, `subtasks`, `tags`, `completion_date`, `start_date` fields present (populated lazily — `None`/`[]` until later slices wire them up).
  - [ ] Converter `eventkit_reminder_to_pydantic(ek_reminder) -> Reminder` exists.
  - [ ] Field order is locked at end of this slice.
- [ ] Complete

### S0.4 — FastMCP migration

- **Files**: `src/mcp_apple_reminders/server.py` (substantial rewrite), every `tools/*.py` (decorator migration), new `lifespan.py`.
- **Acceptance** (spec §Ubiquitous):
  - [ ] Server is built on `FastMCP("mcp-apple-reminders", lifespan=app_lifespan)`.
  - [ ] All 22 existing tools registered via `@mcp.tool()` decorator.
  - [ ] Lifespan owns the single `RemindKit` (later renamed to `Bridge`) instance.
  - [ ] Every tool signature: `(arg1, ..., ctx: Context) -> SomePydanticModel`.
  - [ ] Bit-for-bit tool name + inputSchema preservation. (Smoke-test: snapshot before/after, diff = empty.)
  - [ ] `make lint && make check-architecture && pytest test_mcp_tools.py test_e2e.py` green.
- [ ] Complete

### S0.5 — Context-based logging

- **Files**: every `tools/*.py` handler; `server.py` startup
- **Acceptance**:
  - [ ] Zero `print(..., file=sys.stderr)` calls in `src/mcp_apple_reminders/tools/`.
  - [ ] Tool handlers use `await ctx.info()` / `warning()` / `error()` / `debug()`.
  - [ ] Server startup retains its `sys.stderr` permission-error path (cannot route through Context — no session yet).
- [ ] Complete

## Phase 1 — P0 capabilities

### S1.1 — is_default fix (DONE in commit 117cc8a)

- **Acceptance**:
  - [x] The `is_default` field is `True` for exactly one calendar in `list_calendars` output.
  - [x] Test 6 in `test_crud_calendars.py` enforces this.

### S1.2 — `CalendarManager.create()` + `create_calendar` tool

- **Files**: `_native/calendars.py` (add `.create()`), `tools/calendars.py` (add tool), `test_crud_calendars.py`
- **Acceptance** (spec §Event-driven, §Optional):
  - [ ] When `create_calendar` is invoked with a unique name, a new reminder calendar is created in the user's primary source and returned.
  - [ ] When invoked with a duplicate name, an error is returned without creating a second calendar.
  - [ ] If the user's only source doesn't support reminders, an error is returned (vs silently picking a wrong source).
  - [ ] Where `color` is provided, the named palette OR hex is honored.
  - [ ] Test: create → assert in `list_calendars` → delete (manual cleanup via direct EventKit call until S1.3).
- [ ] Complete

### S1.3 — `delete_calendar` + `update_calendar`

- **Files**: `_native/calendars.py` (add `.delete()`, `.update()`), `tools/calendars.py`, `test_crud_calendars.py`
- **Acceptance** (spec §Event-driven, §Unwanted-behavior):
  - [ ] `delete_calendar` with `force=false` errors if reminders exist, listing the count.
  - [ ] `delete_calendar` with `force=true` deletes everything inside.
  - [ ] `delete_calendar` on the default calendar rejects.
  - [ ] `update_calendar` accepts `name` and/or `color`; returns the updated calendar.
  - [ ] Test: create → update name → update color → delete with force=true → confirm gone.
- [ ] Complete

### S1.4 — ReminderKit bindings

- **Files**: `_native/reminderkit.py` (new), `_native/bridge.py` (new — facade), `verify_setup.py` (probe for ReminderKit load)
- **Acceptance** (spec §Unwanted-behavior, §State-driven):
  - [ ] `objc.loadBundle` succeeds on macOS 26.1, exposing `REMReminder` to Python.
  - [ ] If load fails, `_native.reminderkit.REMINDERKIT_AVAILABLE` flips false; bridge methods that need it raise `ReminderKitUnavailable` exception.
  - [ ] `bridge.py` exposes unified API: `get_subtasks(reminder_id)`, `get_flagged(reminder_id)`, `get_tags(reminder_id)` — read-only in this slice.
  - [ ] Converters populate the new `Reminder` fields (`parent_reminder_id`, `subtasks`, `tags`) when ReminderKit is available.
  - [ ] Test: `verify_setup.py` reports ReminderKit availability. New `test_reminderkit_smoke.py` exercises the load + a read.
- [ ] Complete

### S1.5 — Subtask write paths

- **Files**: `_native/reminderkit.py` (add write methods), `_native/bridge.py`, `tools/reminders.py`, `tools/queries.py`, new `test_subtasks.py`
- **Acceptance** (spec §Event-driven, §Unwanted-behavior):
  - [ ] `create_reminder(parent_reminder_id=...)` creates the new reminder as a subtask in the parent's calendar.
  - [ ] If `parent_reminder_id` + `calendar_id` mismatch, the call rejects with `ValueError`.
  - [ ] `set_parent(reminder_id, parent_reminder_id)` reassigns; `parent_reminder_id=null` detaches.
  - [ ] `get_subtasks(reminder_id)` returns ordered subtask `Reminder` list.
  - [ ] Test: create parent → create 3 subtasks → get_subtasks → reparent one → detach another → assert state → cleanup.
- [ ] Complete

### S1.6 — `set_flagged` tool

- **Files**: `tools/reminders.py` (add `set_flagged`), or extend `update_reminder` to accept `flagged`.
- **Acceptance**:
  - [ ] `create_reminder(flagged=true)` and `update_reminder(reminder_id, flagged=...)` set the flag via ReminderKit.
  - [ ] Reminder.flagged field surfaces correctly.
  - [ ] Test: create + flag + get + assert + unflag + assert + cleanup.
- [ ] Complete

### S1.7 — `set_tags` tool + tag filter

- **Files**: `tools/reminders.py`, `tools/queries.py`, `_native/bridge.py`, `test_crud_reminders.py`
- **Acceptance**:
  - [ ] `update_reminder(reminder_id, tags=["a","b"])` replaces the tag set.
  - [ ] `get_reminders(tags=["x"])` filters by tag.
  - [ ] Test: create + tag + filter + retag + filter + cleanup.
- [ ] Complete

## Phase 2 — MCP protocol primitives

### S2.1 — Resources (4 read views)

- **Files**: `src/mcp_apple_reminders/resources/__init__.py`, `resources/reminders.py`, registration in `server.py`
- **Acceptance** (spec §Ubiquitous re Resources):
  - [ ] `reminders://list/{id}` returns the full reminder set as structured Pydantic JSON.
  - [ ] `reminders://default`, `reminders://overdue`, `reminders://today` each work.
  - [ ] Resources are listed by `mcp__apple-reminders__list_resources` (or whatever the client API is).
- [ ] Complete

### S2.2 — Prompts (4 canned workflows)

- **Files**: `src/mcp_apple_reminders/prompts/__init__.py`, `prompts/*.py`
- **Acceptance**:
  - [ ] `daily_review`, `weekly_retro`, `brain_dump_triage`, `agent_visibility_sync` registered.
  - [ ] Each accepts arguments documented in `design.md::API surface::New prompts`.
  - [ ] Each renders to MCP `Prompt` messages the client can surface.
- [ ] Complete

### S2.3 — Progress reporting skeleton

- **Files**: `_native/bulk.py` (new — bulk-op helpers)
- **Acceptance**:
  - [ ] `bulk_iter(items, ctx)` yields each item with progress reporting + cancellation check.
  - [ ] Smoke test against a fake list of 25 items: progress emits at item 10, 20, 25.
- [ ] Complete

### S2.4 — Elicitation guards

- **Files**: `tools/calendars.py::delete_calendar` (Phase 1.3 augmented), `tools/reminders.py::bulk_delete_completed` (Phase 3.4 augmented)
- **Acceptance** (spec §Event-driven):
  - [ ] `delete_calendar(force=true)` with N≥1 reminders prompts via `ctx.elicit` with a confirmation schema before executing.
  - [ ] `bulk_delete_completed` prompts via `ctx.elicit`.
- [ ] Complete

### S2.5 — Sampling: `triage_brain_dump`

- **Files**: `tools/sampling.py` (new), test
- **Acceptance**:
  - [ ] Given a `from_list` (default: Claude-Brain-Dump), the tool calls `ctx.session.create_message` with the items and a structured-output request to classify each by domain.
  - [ ] The tool then moves each item to the suggested list (or asks user via elicitation if confidence < threshold).
  - [ ] Test mock the sampling call; assert routing.
- [ ] Complete

## Phase 3 — Feature parity

### S3.1 — Time-based alarms (relative + absolute)

- **Files**: `tools/alarms.py` (new), `_native/eventkit.py` add alarm helpers
- **Acceptance**:
  - [ ] `set_alarm(reminder_id, relative_offset=...)` or `set_alarm(reminder_id, absolute_date=...)` attaches an EKAlarm.
  - [ ] Reminder model exposes alarms list.
- [ ] Complete

### S3.2 — Location-based alarms

- **Files**: `tools/alarms.py`, models.py (add Alarm with location/proximity)
- **Acceptance**:
  - [ ] `set_location_alarm(reminder_id, location, proximity)` works for enter/leave.
  - [ ] Test mocks `structuredLocation`.
- [ ] Complete

### S3.3 — Recurrence rules

- **Files**: `tools/recurrence.py` (new), models.py (RecurrenceRule)
- **Acceptance**:
  - [ ] `set_recurrence(reminder_id, frequency, interval, end_*)` attaches `EKRecurrenceRule`.
  - [ ] Daily / weekly / monthly / yearly all work.
  - [ ] End conditions: never / on date / after N occurrences.
- [ ] Complete

### S3.4 — Bulk ops

- **Files**: `tools/bulk.py` (new). Uses S2.3 helpers + S2.4 elicitation.
- **Acceptance**:
  - [ ] `bulk_complete(reminder_ids=[...])` completes each, reports progress.
  - [ ] `bulk_delete_completed(calendar_id?)` deletes (after elicitation).
  - [ ] `bulk_move(reminder_ids, target_calendar_id)` moves all.
- [ ] Complete

### S3.5 — Multi-calendar query

- **Files**: `tools/queries.py::get_reminders` — accept `calendar_ids: list[str]`
- **Acceptance**:
  - [ ] `get_reminders(calendar_ids=["a","b"])` returns merged results.
- [ ] Complete

### S3.6 — `get_completed_in_range`

- **Files**: `tools/queries.py` (new tool)
- **Acceptance**:
  - [ ] `get_completed_in_range(start, end, calendar_id?)` returns reminders with `completion_date` in [start, end).
- [ ] Complete

## Phase 4 — Visibility-plane pilot + cross-cutting

### S4.1 — Agent visibility-plane bootstrap

- **Files**: `tools/agents.py` (new), `resources/agents.py`, AGENTS.md sweep, global rule snippet for CLAUDE.md
- **Acceptance**:
  - [ ] `bootstrap_agent_list(project_name)` creates `Agents-<project_name>` if missing; returns the calendar.
  - [ ] `agents://current` resource exposes the current project's list.
  - [ ] AGENTS.md documents the session-start auto-bootstrap rule.
- [ ] Complete

### S4.2 — TodoWrite mirror (STRETCH)

- **Files**: `tools/agents.py::sync_todos`, polling helper
- **Acceptance**:
  - [ ] Given a TodoWrite-shaped payload, mirror state into `Agents-<project>` reminders within 5s.
  - [ ] Status mapping: todos.status → reminder.completed / flagged.
- [ ] Complete

### S4.3 — Streamable HTTP transport (opt-in)

- **Files**: `server.py` (transport selection), `VIBE.yaml` (server.transport)
- **Acceptance**:
  - [ ] `VIBE.yaml::server.transport: streamable_http` boots the server on HTTP instead of stdio.
  - [ ] CORS configured for localhost.
- [ ] Complete

### S4.4 — Security review + kill switches

- **Files**: `docs/SECURITY-REVIEW.md`, `tools/_kill_switch.py` (helper), `VIBE.yaml::agents.tool_flags`
- **Acceptance**:
  - [ ] SECURITY-REVIEW.md done against OWASP MCP guide.
  - [ ] Every `@mcp.tool()` consults the kill-switch flag; disabled tools return immediate error.
- [ ] Complete

### S4.5 — Docs sweep

- **Files**: README.md, MAP.md, AGENTS.md, `docs/TOOLS.md` (auto-generated from registered tools)
- **Acceptance**:
  - [ ] README reflects the new capability matrix.
  - [ ] Tool catalog auto-generates from FastMCP registry.
- [ ] Complete

## Done when

- [ ] All Phase 0–4 acceptance bullets checked.
- [ ] `make check-if-the-agent-can-consider-this-task-completed` green.
- [ ] No open blockers in `TASK_STATE.md §3`.
- [ ] `mem:core` reflects the new module layout and ReminderKit availability.
- [ ] AGENTS.md §9 gotchas re-audited against final state.
