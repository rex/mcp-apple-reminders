# Core

`mcp-apple-reminders` — macOS-only MCP server exposing Apple Reminders to Claude/Codex/Claude Desktop. Python 3.10+, currently EventKit via PyObjC + vendored `pyremindkit`. Pivoting to **RemCTL three-tier architecture** per spec 002 (SQLite reads + Swift EventKit helper subprocess + Obj-C ReminderKit helper subprocess). See `mem:session_pivot_2026_05_28` for the pivot narrative.

## Source map (current — pre-S0.2 rename)

- `src/mcp_apple_reminders/server.py` — MCP server orchestrator (95 lines). Bootstraps `pyremindkit` sys.path, instantiates `RemindKit` (triggers Reminders permission), wires `@app.list_tools()` and `@app.call_tool()` to dispatch into `tools/`.
- `src/mcp_apple_reminders/formatting.py` — `format_reminder`, `parse_datetime`, `parse_priority`.
- `src/mcp_apple_reminders/tools/{calendars,reminders,queries,workflow,__init__}.py` — 22 tools registered across 4 categories.
- `libs/pyremindkit/src/pyremindkit/{core,calendars,models,_internal,__init__}.py` — EventKit wrapper. To be renamed to `src/mcp_apple_reminders/_native/` in S0.2 (drops the vendored-dep theater).
- `scripts/*.py` — skeleton-owned gate scripts (`bump_version`, `check_architecture`, `check_module_rules`, `check_docs`, `check_version_bumped`, `sync_skeleton`). Do not hand-edit.
- `test_*.py` + `test_support/` — per-domain test scripts. Root-level (not pytest-discoverable from `tests/`).
- `specs/002-modernize-and-foundation/` — canonical spec/design/plan/tasks for current work. Spec 001 archived at `specs/_archive/`.

## Source map (post-S0.2 target)

- `src/mcp_apple_reminders/server.py` — FastMCP instance + lifespan + transport.
- `src/mcp_apple_reminders/{tools,resources,prompts}/` — `@mcp.tool()` / `@mcp.resource()` / `@mcp.prompt()` decorators.
- `src/mcp_apple_reminders/models.py` — Pydantic schemas with `deeplink` field on Reminder + Calendar.
- `src/mcp_apple_reminders/_native/`:
  - `sqlite.py` — direct SQLite reader (replaces slow EventKit iteration for reads).
  - `eventkit.py` — Python wrapper for the Swift helper subprocess.
  - `reminderkit.py` — Python wrapper for the Obj-C helper subprocess.
  - `bridge.py` — unified facade; tools talk to this.
  - `bin/rem_eventkit` (compiled from `src/rem_eventkit.swift`, borrowed from `viticci/remctl::remctl-bridge.swift`, MIT).
  - `bin/rem_reminderkit` (compiled from `src/rem_reminderkit.m`, borrowed from `viticci/remctl::remctl-private.m`, MIT).
  - `THIRD_PARTY_NOTICES.md` — attribution.

## Invariants

- MCP server speaks JSON-RPC over stdio. **Never write to stdout from server code.** Logs/diagnostics go to stderr (current) or `Context` logging (post-S0.5). `print(..., file=sys.stderr)` is the current pattern.
- macOS Reminders permission is per-binary. Conda Python at `./venv/bin/python3` (→ `/opt/homebrew/Caskroom/miniconda/base/bin/python3.13`) is what gets approved.
- macOS 26.1 verified as dev box. `/System/Library/PrivateFrameworks/ReminderKit.framework` exists. Pierce explicitly accepted private-API risk.
- Architecture gate is opt-OUT (every Python source file scanned, hard cap 400 lines / soft 250). No grandfather glob exclusions — the 4 pre-retrofit oversized files were refactored. Native helper sources (`*.swift`, `*.m`) under `_native/` are outside the gate's scope.
- VERSION file is source of truth for bump gate; `pyproject.toml`'s version separate (known divergence).
- Trunk strategy: commits land on `main`. Signed (`git commit -S`). Each commit bumps VERSION.
- All subagent spawns pass `model: "opus"` explicitly. Global policy in `mem:global/agent_model_policy`.

## Known bugs (tracked; do NOT fix accidentally)

- `core.py` `on_reminder_created` / `on_reminder_completed` callbacks are DEAD CODE — registered but never fired.
- EventKit save/delete error out-params: `error = None` passed; actual errors never propagate. `RuntimeError(f"...: {error}")` always says `None`.
- **`is_default` bug FIXED** in commit `117cc8a` (S1.1, 2026-05-28). `CalendarManager.list()` now compares against `defaultCalendarForNewReminders()`.

## Capability roadmap (spec 002 — locked)

**Phase 0** (modernize substrate, ~3 days):
- S0.1 bump mcp>=1.27 + PyObjC
- S0.2 rename libs/pyremindkit → _native/
- S0.3 Pydantic models with deeplinks (CONTRACT FREEZE)
- S0.4 FastMCP migration (22 tools → decorators)
- S0.5 Context logging (replace stderr prints)
- S0.6 native build pipeline (borrow Swift + Obj-C helpers from RemCTL)

**Phase 1** (P0 capabilities, ~4 days):
- S1.1 is_default fix ✅ done (117cc8a)
- S1.0 SQLite reader
- S1.2 create_calendar
- S1.3 delete_calendar + update_calendar
- S1.4 ReminderKit helper Python wrapper
- S1.5 subtask write paths (create_reminder(parent_reminder_id), set_parent, get_subtasks)
- S1.6 set_flagged
- S1.7 set_tags + tag filter
- S1.8 assign_section

**Phase 2** (MCP primitives, ~2 days):
- S2.1 Resources (4 SQLite-served views)
- S2.2 Prompts (4 canned workflows)
- S2.3 progress reporting skeleton
- S2.4 elicitation guards on destructive ops
- S2.5 sampling: triage_brain_dump

**Phase 3** (feature parity, ~3 days):
- S3.1 time-based alarms
- S3.2 location-based alarms
- S3.3 recurrence rules
- S3.4 bulk ops
- S3.5 multi-calendar query
- S3.6 get_completed_in_range

**Phase 4** (visibility-plane + cross-cutting, ~2 days):
- S4.1 bootstrap_agent_list + agents://current resource
- S4.2 TodoWrite mirror (stretch)
- S4.3 Streamable HTTP transport (opt-in)
- S4.4 security review + per-tool kill switches
- S4.5 docs sweep

**Total: 25 slices, ~13-14 days focused (~2-3 weeks realistic).**

See `mem:tech_stack`, `mem:suggested_commands`, `mem:conventions`, `mem:task_completion`, `mem:session_pivot_2026_05_28` for specifics.
