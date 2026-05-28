# Changelog

All notable changes to this project are documented here. This project
follows [Semantic Versioning](https://semver.org/) and
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/).


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
