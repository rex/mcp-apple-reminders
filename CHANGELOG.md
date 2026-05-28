# Changelog

All notable changes to this project are documented here. This project
follows [Semantic Versioning](https://semver.org/) and
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/).


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
