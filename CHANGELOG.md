# Changelog

All notable changes to this project are documented here. This project
follows [Semantic Versioning](https://semver.org/) and
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/).


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
