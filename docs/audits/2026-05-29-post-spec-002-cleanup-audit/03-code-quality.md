# 03 — Code-quality review (`src/mcp_apple_reminders/`)

**Agent**: feature-dev:code-reviewer / Opus.
**Prompt**: "High-confidence code-quality review (≥70% confidence). Find what I broke or did sloppily during the 31-slice sprint."

## Findings (verbatim)

### CRITICAL

#### 1. `tool_name` mismatch: `move_reminder_blocked` decorates a Claude-Waiting move
- **Location**: `src/mcp_apple_reminders/tools/workflow.py:131,138,144`
- **Why**: The tool is registered as `move_reminder_blocked` but moves to the list `Claude-Waiting`. The function is `move_reminder_blocked`. Pierce's own server-instructions string (`server.py:24-29`) and module docstring say the four sugar moves are "on_deck / active / done / blocked" — but the *implementation* targets `Claude-Waiting`. Either the public tool name should be `move_reminder_waiting` (matching what it actually does) or the target list should be `Claude-Blocked`. As-is, an LLM picking the tool whose name says "blocked" will silently route to the "waiting" list.
- **Fix**: Rename the target list literal to `"Claude-Blocked"` (and create/rename the list in Reminders.app), OR rename the tool to `move_reminder_waiting` for symmetry with the list. Update CHANGELOG + agent-instructions string in `server.py:24-29` either way.

#### 2. Four `test_workflow_*.py` modules are un-collectable — no fixtures defined anywhere
- **Location**: `test_workflow_convenience.py:13`, `test_workflow_discovery.py:10`, `test_workflow_errors.py:11`, `test_workflow_moves.py:16,71`
- **Why**: These define `def test_X(rk, workflow_lists, results):` but there is **no `conftest.py` anywhere in the repo** and **no `@pytest.fixture` declaration for `rk`, `workflow_lists`, or `results` in any test file**. Under pytest these collect with `ERROR: fixture not found`. `test_workflow_tools.py:18-21` imports them as plain functions for use by a custom orchestrator harness — but the §3 mandatory command `pytest test_workflow_tools.py` will still collect the imported modules and error on every test in them. This is the "pre-existing fixture bug" you flagged — still broken.
- **Fix**: Remove the `test_` prefix on these four files (rename to `workflow_convenience.py`, `workflow_discovery.py`, `workflow_errors.py`, `workflow_moves.py`) since they are not pytest tests but harness building blocks; update the imports in `test_workflow_tools.py` accordingly.

### HIGH

#### 3. `format_reminder` is dead code
- **Location**: `src/mcp_apple_reminders/formatting.py:18-54`
- **Why**: Grep of `src/` shows zero callers post-FastMCP migration — every handler now returns Pydantic `Reminder` directly and FastMCP serializes. Only the doc files (`README.md`, `MAP.md`, `PROJECT_SUMMARY.md`, `DONE_BLOCKED_FEATURES.md`) reference it, all describing the *pre-migration* design.
- **Fix**: Delete `format_reminder` from `formatting.py`; the file becomes "parsers". Strip the four doc references to it.

#### 4. `_unused = native_reminder_to_pydantic` is a deliberate lint-suppression hack
- **Location**: `src/mcp_apple_reminders/tools/bulk.py:23, 160-161`
- **Why**: The converter is genuinely unused in `bulk.py` — `bulk_complete`/`bulk_move`/`bulk_delete_completed` all return `dict`, not `Reminder`. The `_unused = native_reminder_to_pydantic  # noqa: F841` keeps an import alive purely to dodge F841. `test_bulk_ops.py:61-66` then *tests for* the presence of `_unused` to prove "the deferred import resolved" — locking in technical debt with a test.
- **Fix**: Drop the import on line 23 and remove the `_unused` declaration; delete `test_valid_routes_unused_import_silenced` from `test_bulk_ops.py`.

#### 5. `tools/__init__.py` re-exports only 5 of 9 tool modules
- **Location**: `src/mcp_apple_reminders/tools/__init__.py:21-23`
- **Why**: Re-exports `calendars, queries, reminders, sections, workflow` but the actual tool modules also include `agents, alarms, bulk, sampling`. Worse, the docstring (lines 3-15) still says "22 tools" with 4-category layout — but `server.py:41-49` imports 9 tool modules covering 37 tools. Introspection callers using `from mcp_apple_reminders import tools; tools.__all__` get a wrong picture. Registration still works only because `server.py` imports the missing four directly.
- **Fix**: Update `tools/__init__.py` to import all 9 modules (`agents, alarms, bulk, calendars, queries, reminders, sampling, sections, workflow`) and refresh the docstring's tool count + layout block to match spec 002 reality.

#### 6. `RemindKit.on_reminder_created` / `on_reminder_completed` are documented dead callbacks
- **Location**: `src/mcp_apple_reminders/_native/core.py:44,53-54,67,214-229`
- **Why**: `CLAUDE.md §9` itself flags these as "register but never fire" — and the code is still there. Listing them in the public class API invites misuse; the `__init__` allocates two callback lists that no event source ever invokes (line 67 iterates `_on_reminder_created_callbacks` but is never called by anything because `create_reminder` short-circuits before reaching it under current flows).
- **Fix**: Delete `on_reminder_created`, `on_reminder_completed`, the two `_on_*_callbacks` lists in `__init__`, and the line-67 iteration; keep `RemindKit` API surface honest.

#### 7. `update_reminder` docstring missing `flagged` and `add_tags` args
- **Location**: `src/mcp_apple_reminders/tools/reminders.py:184-194`
- **Why**: The function signature accepts `flagged` and `add_tags` (lines 181-182), and the function body handles them (lines 217-238), but the docstring `Args:` block stops at `is_completed`. FastMCP-derived tool descriptions use these docstrings for argument hints — the LLM caller gets no guidance for the two ReminderKit-side fields.
- **Fix**: Append `flagged:` and `add_tags:` rows to the docstring's `Args:` block at line 193-194.

### MEDIUM

#### 8. `_app_context` is duplicated verbatim across 7 tool modules; `_bridge_from_ctx` across 2
- **Location**: `tools/calendars.py:40`, `queries.py:31`, `sampling.py:30`, `agents.py:34`, `reminders.py:35,39`, `bulk.py:27`, `sections.py:27`, `workflow.py:25`
- **Why**: Eight identical 2-line helpers, one per tool file, returning `ctx.request_context.lifespan_context[.bridge]`. The pattern that hides in plain sight is **not a decorator** — it's a single helper in `lifespan.py` (or a new `tools/_ctx.py`) that everyone imports. Diff hygiene cost: 8 places to change if the lifespan attribute name changes (was `bridge`, could become `remind` per the older README).
- **Fix**: Add `def app_context(ctx) -> AppContext` and `def bridge(ctx) -> RemindKit` to `lifespan.py`; replace the per-module dupes with `from ..lifespan import app_context, bridge`.

#### 9. `delete_calendar` imports `BaseModel` mid-function under a try/except
- **Location**: `src/mcp_apple_reminders/tools/calendars.py:249-263`
- **Why**: `from pydantic import BaseModel` lives inside the elicitation `try:` block at line 249, and `_ConfirmCascade` is declared as a local class inside the function body. `bulk.py:83` already declares its own `_ConfirmBulkDelete(BaseModel)` at module scope as the clean pattern. This is the same scenario, done two different ways in two adjacent files. The mid-function import dodges the unused-import warning if elicitation is skipped, but it costs readability and re-runs class construction every call.
- **Fix**: Hoist `_ConfirmCascade(BaseModel)` to module scope in `calendars.py` next to the imports (mirror `bulk.py:83`), and remove the function-local `from pydantic import BaseModel`.

#### 10. `get_completed_in_range` silently returns `[]` when SQLite is unavailable
- **Location**: `src/mcp_apple_reminders/tools/queries.py:260-262`
- **Why**: Every other read tool in `queries.py` falls back to EventKit on `RemindersDBUnavailable`. This one logs and returns empty — the caller has no idea whether the window genuinely contained nothing or whether the store was unreachable. Worst case: an agent uses this to drive bulk_delete and gets a false negative.
- **Fix**: Raise `ValueError(f"SQLite read path unavailable ({e}); EventKit fallback not yet implemented for get_completed_in_range")` instead of returning `[]`, matching `bulk_delete_completed`'s pattern at `bulk.py:119-121`.

---

**Not flagged** (verified clean): Reminder/Calendar field order matches `test_models.py` exactly; SQLite-fallback policy is uniform across all read tools except finding #10; the three `_native` layers (`core.py` RemindKit / `sqlite.py` Reader / `eventkit.py`+`reminderkit.py` helper wrappers) have non-overlapping responsibilities (EventKit write path / SQLite read path / Swift+Obj-C helpers); `native_reminder_to_pydantic` is still needed in workflow/reminders/queries fallback paths.

**Files most worth opening**: `tools/workflow.py:131-144`, `tools/bulk.py:23,160-161`, `tools/__init__.py:21-23`, `_native/core.py:44-229`, `tools/reminders.py:172-246`, `formatting.py:18-54`, the four `test_workflow_*.py` modules.
