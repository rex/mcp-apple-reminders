# Post-spec-002 cleanup audit (2026-05-29)

After spec 002 shipped (31 slices, 37 tools, all four phases ✅, ADR 0001
spec'd Phase 5 / S5.1), Pierce opened the repo in an editor and got an
unpleasant surprise: test sprawl at repo root, stale markdown debris, and
"the list goes on." This audit dispatched four parallel Opus subagents,
each reviewing a distinct dimension of the mess, and synthesized the
findings into one place so nothing is lost when cleanup work begins.

**Scope**: read-only review. No files modified during the audit.
**Date**: 2026-05-29 (session that immediately followed the spec 002 ship).
**Sequel**: cleanup will be tracked as one slice or split into themed sub-slices
(decision pending). Phase 5 / S5.1 implementation comes first.

## What was found, at a glance

- **5 CRITICAL** findings — actual functional bugs (silent routing bug,
  un-collectable tests, broken README imports, stale `testpaths` config).
- **~18 HIGH** findings — docs lying about reality (README claims 22 tools,
  AGENTS.md §9 lists shipped features as "NO X" gaps, `tools/__init__.py`
  re-exports 5 of 9 modules), source-level dead code, skeleton drift on
  3 hooks.
- **~14 MEDIUM** findings — polish, refactor consistency, attribution
  visibility, `.claude/` spillover.
- **Total**: ~37 distinct findings beyond what was already known before
  the audit.

## Sub-reports (one per agent)

1. [`01-file-organization.md`](./01-file-organization.md) — repo-layout audit (17 distinct findings beyond the 3 already on the table).
2. [`02-documentation.md`](./02-documentation.md) — markdown audit (README, AGENTS.md §9, MAP.md, TASK_STATE.md, src-tree READMEs, CHANGELOG holes).
3. [`03-code-quality.md`](./03-code-quality.md) — Python source review (10 findings: 2 CRITICAL bugs, 5 HIGH dead-code / stale-decorator-registry, 3 MEDIUM consistency).
4. [`04-build-config.md`](./04-build-config.md) — build / config / skeleton drift (6 HIGH, 8 MEDIUM, 1 LOW).

## The synthesized list — by severity

### CRITICAL — actual bugs, not polish

1. **`move_reminder_blocked` routes to `Claude-Waiting`**
   `tools/workflow.py:131-144`. Tool name says "blocked", body targets "Waiting". Silent semantic bug — an LLM picking the name-matched tool gets the wrong destination. Either rename the tool to `move_reminder_waiting` or rename the list literal.
2. **`CHANGELOG.md` 0.1.9 + 0.1.11 still say `_(fill in)_`**
   0.1.10 *claimed* to backfill 0.1.9 but never edited the body. 0.1.11 was never followed up.
3. **4 `test_workflow_*.py` modules un-collectable**
   No `conftest.py` defines `rk` / `workflow_lists` / `results`. Bare `pytest` errors on every test in those four files. The side-task spawned during the slice run never landed; they're STILL broken.
4. **`README.md` import snippet doesn't work**
   Line 84: `from mcp_apple_reminders import main` → `ImportError`. Only `cli_main` and `mcp` are exported.
5. **`pyproject.toml::testpaths = ["tests"]`**
   Points at a directory that doesn't exist. Bare `pytest` discovers zero tests; only the §3 explicit-paths invocation works.

### HIGH

**Docs that lie about reality**
- `README.md` claims "22 tools", refs `libs/pyremindkit/` (renamed S0.2), no mention of FastMCP / Resources / Prompts / Sampling / alarms / recurrence / bulk / visibility-plane / streamable HTTP.
- `AGENTS.md §9` falsely lists shipped features as `NO create_calendar` / `NO flagged` / `NO recurrence` / `NO alarms` / `NO subtasks` capability gaps.
- `src/mcp_apple_reminders/README.md` pre-FastMCP. Refs the old `libs/pyremindkit/` import path, low-level `Server` class, module-level `remind = RemindKit()`.
- `src/mcp_apple_reminders/tools/README.md` pre-FastMCP. Documents defunct `TOOLS: list[Tool]` / `HANDLERS: dict` pattern; lists 4 modules; current `tools/` has 9.
- `MAP.md` no mention of `resources/`, `prompts/`, `_native/sqlite.py`, `_native/eventkit.py`, `_native/reminderkit.py`, or new tool modules.
- `TASK_STATE.md §0` "Next action: pick up Slice 0.1" — stale by 31 slices.
- `.claude/session-context.md` stack line still says "vendored pyremindkit".

**Source mess**
- `format_reminder` in `formatting.py` dead post-FastMCP.
- `_unused = native_reminder_to_pydantic` in `tools/bulk.py:160-161` lint-suppression hack; `test_bulk_ops.py:61-66` tests for its presence, locking the debt in.
- `tools/__init__.py` re-exports 5 of 9 tool modules; docstring claims "22 tools" with 4-category layout.
- `RemindKit.on_reminder_created` / `on_reminder_completed` (`_native/core.py:44-229`) — dead public API surface, documented as such in `CLAUDE.md §9`.
- `update_reminder` docstring missing `flagged` and `add_tags` args (signature has them, doc doesn't — LLM gets no hint).

**Skeleton drift**
- 3 hooks drifted from agentic-skeleton v0.37.0: `.claude/hooks/{auto-commit,changelog-append,stop-gate}.sh`.

**Repo hygiene**
- 4 `.DS_Store` files tracked.
- `mcp-server-apple-reminders.log` — 1.6 K stale Dec 17 2025 log.
- `requirements.txt` redundant with `pyproject.toml::dependencies`.
- `AGENTS.md.pre-retrofit` — git history already preserves; dead weight.

### MEDIUM

- `_app_context(ctx)` duplicated verbatim across 7 tool modules + `_bridge_from_ctx` across 2. Single export from `lifespan.py` instead.
- `delete_calendar` mid-function `from pydantic import BaseModel` + local `_ConfirmCascade` class; `bulk.py:83` does it the clean module-scope way. Two patterns in adjacent files.
- `get_completed_in_range` silent `[]` on `RemindersDBUnavailable` — every other read tool falls back to EventKit. False-negative risk.
- `tools/sections.py` houses `get_subtasks` + `set_parent` + `assign_section`; subtasks aren't sections. Rename or split.
- `_native/` flat: 7 Python + binaries + Swift/Obj-C sources at one depth. The legacy four (`core.py`, `calendars.py`, `models.py`, `_internal.py`) may be partially dead post-S1.0 — needs a grep audit before delete-or-organize.
- `_native/THIRD_PARTY_NOTICES.md` buried under an underscore-package.
- `GEMINI.md` may be a duplicate file vs symlink.
- `PROGRESS.md` and `TASK_STATE.md` overlap.
- `MAP.md` belongs in `docs/`.
- `specs/002-modernize-and-foundation/` missing a `README.md`.
- `.claude/{commands/scaffold.md, commands/retrofit.md, agents/terraform-reviewer.md, rules/terraform.md, rules/ansible.md}` — dead skeleton spillover.
- `pyproject.toml::authors = pierce@example.com` + `[project.urls]` `github.com/yourusername` placeholders.
- `claude_desktop_config.example.json` uses bare `python3` (README warns against this).
- `pyremindkit` ghost in `_native/{__init__,_internal,models}.py` module docstrings.
- `test_support/` should move under `tests/` when tests relocate.

## Already-known (not re-listed in the audit)

- 28 `test_*.py` files at repo root → move to `tests/`.
- 10 stale root markdowns from Dec 2025 / March 2026 to delete.
- Duplicate `TOOLS.md` at root + `docs/TOOLS.md` (delete root, keep auto-gen).

## Cleanup-shape decision (pending)

Pierce to choose between:

- **Single slice (`CL-1`)** — "post-spec-002 cleanup pass" tracked as one slice with one ADR.
- **Split sub-slices** (`CL-1a` docs, `CL-1b` source, `CL-1c` tests relocate, `CL-1d` skeleton drift).

Either way, cleanup follows S5.1 (list-group support) since spec 002 + ADR 0001 already prioritized that work.
