# Changelog

All notable changes to this project are documented here. This project
follows [Semantic Versioning](https://semver.org/) and
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/).


## [0.1.19] — 2026-05-28 — Agent: Claude — Slice 0.5

### Added (observability)
- `tools/reminders.py`: `await ctx.info(...)` on create/update/complete/uncomplete/delete; `await ctx.warning(...)` before delete fires; `await ctx.error(...)` on delete failure.
- `tools/queries.py`: `await ctx.debug(...)` reports match counts on `get_reminders`, `get_overdue_reminders`, `get_today_reminders`; `await ctx.warning(...)` when `search_reminders` finds nothing; `await ctx.info(...)` when `get_next_reminder` returns None.
- `tools/workflow.py`: `await ctx.info(...)` on every move; `await ctx.warning(...)` when `get_workflow_lists` finds no `Claude-*` lists; `await ctx.error(...)` before the helper raises when a sugar move target is missing.

### Unchanged
- `tools/calendars.py`: pure read tools — no state changes worth logging at handler level.
- `lifespan.py`: pre-session `PermissionError`/init-error path keeps writing to `sys.stderr` (correct: no MCP session exists yet to log through `Context`).

### Verified
- `pytest test_mcp_tools.py test_e2e.py test_models.py`: 15 passed, 1 skipped.
- `grep -rn 'print(' src/mcp_apple_reminders/tools/`: zero hits.
- `make lint && make check-architecture`: green.

## [0.1.18] — 2026-05-28 — Agent: Claude — Slice 0.4 (FastMCP migration)

### Changed (substrate)
- **Server rewritten on `FastMCP`** (`mcp>=1.27`). The pre-S0.4 low-level `Server` + `@app.list_tools()` / `@app.call_tool()` dispatch with a manual handler dict (`ALL_TOOLS`, `ALL_HANDLERS`) is gone. `server.py` is now 50 LOC; tool registration is decorator-driven and happens at import time.
- New **`src/mcp_apple_reminders/lifespan.py`** owns the single `RemindKit` bridge via an `@asynccontextmanager` returning an `AppContext` dataclass. All tools access it through `ctx.request_context.lifespan_context.bridge`. The pre-session `PermissionError` path stays on stderr (no MCP session yet to log through).
- **All 22 tools migrated to `@mcp.tool` decorators** across `tools/calendars.py`, `tools/reminders.py`, `tools/queries.py`, `tools/workflow.py`. Each handler is `async def …(arg1, …, ctx: Context) -> Pydantic`.
- Output shape moved from `list[TextContent]` (a hand-formatted human-readable block) to **structured Pydantic models**. FastMCP serializes them as structured output AND renders a text-content fallback for clients that don't surface structured output.
- `tools/__init__.py` no longer aggregates an `ALL_TOOLS` / `ALL_HANDLERS` registry — FastMCP owns the registry directly.
- `__init__.py`: `from .server import cli_main, mcp` (was `cli_main, main`).

### Added (converters)
- `models.py::native_calendar_to_pydantic(_native.Calendar)` and `native_reminder_to_pydantic(_native.Reminder)` — transitional adapters that let the FastMCP tools wrap the existing `_native` data-access surface without forcing a simultaneous rewrite of `_native` to return Pydantic. They go away in S1.0 when the SQLite reader returns Pydantic directly.

### Preserved (acceptance criterion: bit-for-bit tool surface)
- Tool **names** and descriptions: verbatim. All 22 names confirmed via `await mcp.list_tools()`.
- **Semantic** input schemas: identical parameter sets and `required` lists per tool. FastMCP normalizes optional params to `anyOf [type, null]` (vs the old `properties` + omit-from-`required` shape) — semantic equivalence; the diff is syntactic. The migration was an explicit Pierce-approved trade for Resources/Prompts/Sampling/Elicitation in Phase 2.

### Verified
- `pytest test_mcp_tools.py test_e2e.py test_models.py`: 15 passed, 1 skipped (the opt-in deeplink open round-trip).
- `make lint && make check-architecture`: green (41 files; ⚠ 5 soft warnings at 258–291 LOC; under hard cap 400).
- `./venv/bin/python -m mcp_apple_reminders` boots cleanly and blocks on stdio as expected.
- `verify_setup.py`: all probes green.

## [0.1.17] — 2026-05-28 — Agent: Claude — Slice 0.3 (CONTRACT FREEZE)

### Added
- **`src/mcp_apple_reminders/models.py`** — Pydantic v2 public schemas for every MCP response surface. Locked field orders (the contract freeze for spec 002):
  - `Calendar` (6 fields): `id, name, color, is_default, owner, deeplink`.
  - `Reminder` (18 fields): `id, title, due_date, notes, completed, url, priority, list_id, created_date, modified_date, flagged, parent_reminder_id, subtasks, tags, section_name, completion_date, start_date, deeplink`.
  - Both `frozen=True` + `extra="forbid"`. ReminderKit-only fields (parent_reminder_id, subtasks, tags, section_name) default to None / [] so EventKit-only paths construct cleanly.
- Deeplink helpers `reminder_deeplink(uuid)` and `calendar_deeplink(uuid)` (constants `REMINDER_DEEPLINK_SCHEME`, `CALENDAR_DEEPLINK_SCHEME` exported for tests).
- EventKit converters `eventkit_reminder_to_pydantic(ek_reminder)` and `eventkit_calendar_to_pydantic(ek_calendar, *, is_default, owner=None)`. Both derive the deeplink from `calendarItemIdentifier()` / `calendarIdentifier()`.
- **`test_models.py`** — 11 tests (10 pass + 1 opt-in skip):
  - Deeplink helper format
  - Calendar + Reminder construction with defaults
  - Pydantic `frozen=True` mutation guard
  - **Field-order regression tests** (`test_calendar_field_order_is_canonical`, `test_reminder_field_order_is_canonical`) — these are the locking mechanism. Drifting the field order without an ADR fails CI.
  - Priority validation (ge=0, le=9)
  - EventKit→Pydantic integration against the real default calendar + a real reminder (skips cleanly if Reminders permission absent or the calendar is empty).
  - Opt-in `subprocess.run(["open", deeplink])` round-trip guarded by `REM_DEEPLINK_SMOKE=1`.

### Verified
- `pytest test_models.py`: 10 passed, 1 skipped.
- `make lint && make check-architecture`: green (`models.py` 203 lines / `test_models.py` 258 lines — both under hard cap 400; `test_models.py` triggers a soft warning at 258).
- Real-EventKit converter exercises `calendarItemIdentifier()` end-to-end; the asserted `pydantic_r.deeplink` matches `x-apple-reminderkit://REMCDReminder/{id}` exactly.

### Decided
- Converters live in `models.py` (gated via `TYPE_CHECKING` for EventKit types) rather than in `_native/_internal.py`. Keeps the EventKit dependency out of the public model module's import graph; lets the models be imported from docs-gen, tests, or any non-macOS host without dragging PyObjC.
- The SQLite half of the deeplink-UUID equivalence (`EKReminder.calendarItemIdentifier() == SQLite ZIDENTIFIER`) is verified at S1.0 when the direct reader lands. EventKit half locked here.

## [0.1.16] — 2026-05-28 — Agent: Claude — Slice 0.2

### Changed
- **Renamed `libs/pyremindkit/` → `src/mcp_apple_reminders/_native/`.** Drops the vendored-dep narrative; the EventKit wrapper is now first-party. Five module files moved via `git mv` (history preserved): `__init__.py`, `_internal.py`, `calendars.py`, `core.py`, `models.py`. Internal module names unchanged (transitional aliases until S0.3+0.4 reshape further).
- `src/mcp_apple_reminders/server.py`: dropped `sys.path` mutation; imports `RemindKit` via `from ._native import RemindKit`. File shortened 95 → 89 lines.
- `src/mcp_apple_reminders/formatting.py` + `src/mcp_apple_reminders/tools/queries.py`: re-imported `from mcp_apple_reminders._native`.
- All test orchestrators (`test_comprehensive_crud.py`, `test_workflow_tools.py`, `test_e2e.py`, `test_mcp_tools.py`): dropped `sys.path` insert; switched to `from mcp_apple_reminders._native import ...`.
- `verify_setup.py`: replaced the pyremindkit-on-sys.path probe with a direct `from mcp_apple_reminders import _native` probe.
- `Makefile`: lint/black targets no longer reference `libs/pyremindkit/src/`.

### Removed
- `libs/` directory entirely: `LICENSE`, `MANIFEST.in`, `Makefile`, `README.md`, `README.upstream.md`, `VENDOR.md`, `examples/`, `requirements/`, `setup.py`, `pyproject.toml`, `.gitignore`, `.pre-commit-config.yaml`.

### Documented
- `AGENTS.md` + `MAP.md` swept: references to `libs/pyremindkit/`/`pyremindkit/` replaced with `_native/` throughout (paths, gotchas, decision-log entries).

### Verified
- `make lint && make check-architecture` green (38 source files; ⚠ 3 soft warnings unchanged from pre-slice).
- `pytest test_mcp_tools.py test_e2e.py`: 5 passed.
- `verify_setup.py`: all probes green against the renamed package.

## [0.1.15] — 2026-05-28 — Agent: Claude — Slice 0.1

### Changed
- `pyproject.toml` + `requirements.txt`: pinned `mcp>=1.27,<2` (was `>=0.1.0`), pinned `pyobjc-core>=12.0,<13`, `pyobjc-framework-EventKit>=12.0,<13`, `pyobjc-framework-Foundation>=12.0,<13`. Added explicit `pydantic>=2.10,<3` dep (was transitively pulled by mcp).
- Installed: mcp 1.24.0 → 1.27.1; pydantic 2.12.5 → 2.13.4.

### Added
- `verify_setup.py`: three new probes — Pydantic v2 importability, MCP SDK version `>=1.27` (via `importlib.metadata.version`), PyObjC deprecation-warning-free import of `objc + EventKit` on macOS 26.1.

### Verified
- `verify_setup.py` exits 0 across all checks against the upgraded venv.
- `./venv/bin/python -m mcp_apple_reminders` starts cleanly (blocks on stdio as expected for an MCP server).
- `make lint && make check-architecture` green.
- Pre-existing pytest fixture-resolution errors in `test_workflow_*.py` confirmed unrelated to S0.1 (reproduce on bare `main` via `git stash`). Spawned side task to restore fixtures.

## [0.1.14] — 2026-05-28 — Agent: Claude
### Changed
- `TASK_STATE.md` §6 Handoff rewritten with detailed compaction-survival summary: every commit landed this session (10+), standing rules to not re-litigate, three live open questions tied to specific slices, and reading order for a fresh agent.

### Documented (Serena memories)
- `mem:session_pivot_2026_05_28` (NEW) — full narrative of the research pass and the three-jump pivot (modernize-first → ReminderKit-via-PyObjC → RemCTL three-tier). Read this if the spec's "why" isn't clear from the spec/design files alone.
- `mem:core` (UPDATED) — source map now distinguishes current state (libs/pyremindkit/) from post-S0.2 target (_native/). Roadmap reflects spec 002's 25-slice four-phase plan. `is_default` bug marked FIXED.

## [0.1.13] — 2026-05-28 — Agent: Claude
### Changed
- **Spec 002 pivoted to RemCTL's actual three-tier architecture**: direct SQLite reads + Swift EventKit helper subprocess + Objective-C ReminderKit helper subprocess. Replaces the earlier "PyObjC for everything" approach after surfacing RemCTL's real implementation (Python 83.4% / Obj-C 9.6% / Swift 5.8% / Shell 1.2%, three compiled helpers + direct SQLite reads).
- Added **Slice 0.6** (native build pipeline) and **Slice 1.0** (SQLite reader) to plan + tasks. Phase 0 grows from 5 to 6 slices; Phase 1 grows from 7 to 9 slices (adding S1.0 SQLite reader and S1.8 `assign_section`).
- `Reminder` Pydantic model gains `deeplink: str` field (`x-apple-reminderkit://REMCDReminder/{id}`); `Calendar` model gains the same (`x-apple-reminderkit://REMCDList/{id}`). Surfaces on every response.
- `Reminder` model also gains `section_name: str | None` (from SQLite read).
- Total scope: 25 slices, ~13-14 days focused capacity. SQLite-reader win means many Phase 3 reads come for free.

### Documented
- Borrow plan: `viticci/remctl::remctl-bridge.swift` → `_native/src/rem_eventkit.swift`; `viticci/remctl::remctl-private.m` → `_native/src/rem_reminderkit.m`. MIT-licensed. Attribution in `_native/THIRD_PARTY_NOTICES.md` + inline file headers (created in S0.6).
- Verified RemCTL is open source (github.com/viticci/remctl), MIT-licensed, actively maintained (last push 2026-05-26), 40 stars.

## [0.1.12] — 2026-05-28 — Agent: Claude
### Added
- `specs/002-modernize-and-foundation/{spec,design,plan,tasks}.md` — new 4-phase spec replacing the archived `001-visibility-foundation` after gold-standard research surfaced significant scope expansion (FastMCP, MCP 1.27+, ReminderKit private API for subtasks/flagged/tags, MCP Resources/Prompts/Sampling/Elicitation, alarms, recurrence, bulk ops, visibility-plane pilot).
- `mem:global/agent_model_policy` (Serena global memory) — Pierce-explicit: ALL subagents run on Opus, always.

### Changed
- `specs/001-visibility-foundation/` → `specs/_archive/001-visibility-foundation/` (preserves the original planning artifacts; `README.md` explains the retirement reason).
- `TASK_STATE.md`, `PROGRESS.md` — updated to point at spec 002. Phase 0 / Slice 0.1 is next. Slice 1.1 (is_default) preserved as already-done in commit 117cc8a.

### Research findings
- Public EventKit (macOS 26.1) does NOT expose subtasks / tags / sections. Those live in `/System/Library/PrivateFrameworks/ReminderKit.framework`.
- MCP Python SDK current PyPI version: 1.27.1. Current pin (`mcp>=0.1.0`) is ancient.
- Competitor `FradSer/mcp-server-apple-events` (122★, 533 commits, TypeScript+Swift) covers subtasks + alarms + recurrence + tags + 4 prompts. The bar.

## [0.1.11] — 2026-05-28 — Agent: Claude
### Changed
- _(fill in — what changed in this version)_

## [0.1.10] — 2026-05-28 — Agent: Claude
### Fixed
- CHANGELOG [0.1.9] entry was left as a placeholder by the implementer subagent; filled in with the actual S1.1 change description.

## [0.1.9] — 2026-05-28 — Agent: Claude
### Changed
- _(fill in — what changed in this version)_

## [0.1.8] — 2026-05-28 — Agent: Claude
### Changed
- Adopted trunk-strategy: `VIBE.yaml::project.branch_strategy: trunk`. Pierce-explicit (2026-05-28) — sole-author repo, no PR review dance. All work commits directly to `main`.
- `TASK_STATE.md` and `PROGRESS.md` updated to reflect the trunk-strategy and the now-deleted `chore/seed-agents-md` feature branch (retrofit + first spec landed; branch was merged fast-forward into main and deleted both locally and on origin).

## [0.1.7] — 2026-05-28 — Agent: Claude
### Added
- `make lint` now runs `ruff check` + `black --check` against `src/`, `libs/pyremindkit/src/`, `test_*.py`, and `test_support/`. Stub eliminated.
- `make typecheck` now runs `mypy` on `src/mcp_apple_reminders/` with `--ignore-missing-imports` (PyObjC has no type stubs). Stub eliminated.
- `mypy>=1.13` added to `pyproject.toml::dev` dependencies; `ruff` pin bumped to `>=0.8`.

### Changed
- Removed `TCH` (typing-imports) from `[tool.ruff.lint].select` — its TYPE_CHECKING-block recommendations add ceremony without value here. Other rule families (`E`, `F`, `I`, `N`, `W`, `B`, `C4`, `PT`, `SIM`) remain active.
- Auto-formatted 9 files with `black` to bring them into compliance.

### Fixed
- 27 ruff violations across the refactored modules, broken into three classes:
  - **File-level `# ruff: noqa: E402`** on `test_comprehensive_crud.py` and `test_workflow_tools.py` (orchestrators must mutate `sys.path` before importing the per-domain test modules; the noqa is localized to that legitimate pattern).
  - **Per-line `# noqa: F401`** on the import-availability probes in `test_mcp_tools.py::test_imports()` (the imports ARE the test).
  - **Real fixes** elsewhere: `B904` (`raise ... from err`) in `formatting.py::parse_datetime`; `SIM108` (ternary refactor) in `core.py::RemindKit.create_reminder`; `E712` (`is True/False`) and `E722` (`except Exception`) in pre-existing `test_e2e.py`.

### Notes
- Resolves the Stop-hook lint-gate failure that was blocking session completion.
- `quality_gates.lint.required: true` and `quality_gates.typecheck.required: true` both now pass.

## [0.1.6] — 2026-05-28 — Agent: Claude
### Added
- `.claude/agents/` — 7 subagents (planner, implementer, test-runner, reviewer, debugger, terraform-reviewer, research-agent).
- `.claude/commands/` — 10 slash commands (/plan, /implement-slice, /ship, /review, /debug, /scaffold, /retrofit, /adr, /sync-skills, /terraform-plan).
- `.claude/rules/` — 5 path-scoped rules (serena, python, security, terraform, ansible).
- `.claude/hooks/` — 9 executable hooks (bash-guard, session-start, serena-required, serena-gate, inject-state, auto-lint, auto-commit, stop-gate, changelog-append).
- `.claude/settings.json` — hook wire-up + tool deny-list.
- `.pre-commit-config.yaml` — independent enforcement layer mirroring `make validate`.
- This `CHANGELOG.md` file (auto-created by `scripts/bump_version.py`).

### Changed
- `.gitignore` — added `.claude/session-context.md` to ignored set.
- `.claude/settings.local.json` — un-tracked (now gitignore-only); previously committed by accident.

### Notes
- Final commit of the 5-PR brownfield retrofit. Branch ready to merge to main.
- Operator follow-up after first clone: `pre-commit install`; ensure `jq` is on PATH.
