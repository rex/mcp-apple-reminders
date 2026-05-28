# PROGRESS

- **Project**: mcp-apple-reminders (python-mcp; macOS-only EventKit MCP server)
- **Active branch**: `main` (trunk strategy — Pierce explicit 2026-05-28: no feature-branch dance, commits land on main directly)
- **Active feature spec**: `specs/001-visibility-foundation/`
- **Active TASK_STATE**: `TASK_STATE.md` (Phase 1 / Slice 1.2 ← NEXT)
- **Last session**: 2026-05-28 (Claude Sonnet 4.6 — S1.1 done: is_default bug fixed, VERSION 0.1.9)

## Last three decisions

- 2026-05-28 — Subtasks (parent-reminder) scoped into Phase 1 of the visibility-foundation spec (Pierce-explicit: "absolute must").
- 2026-05-28 — No architecture-gate grandfathering. Pre-retrofit oversized files refactored to compliance (server.py 961→95; pyremindkit/core.py 504→229+240+125+56; two test files split). VIBE.yaml `exclude_globs` carries only skeleton defaults.
- 2026-05-28 — `libs/` (plural, vendored) un-gitignored; `libs/pyremindkit/` flattened from embedded git repo to flat-tracked content; upstream provenance captured in `libs/pyremindkit/VENDOR.md`.

## Open blockers

- None active. One open question for S1.3: verify PyObjC `setParentReminder_` binding presence before contracts freeze. Recorded in `TASK_STATE.md §3`.

## How to resume (for a fresh agent)

1. Read `AGENTS.md` (project contract, gotchas).
2. Read `TASK_STATE.md` §0 and the current Slice (1.1 next).
3. Skim `specs/001-visibility-foundation/spec.md` for the requirements, then `design.md` for the approach.
4. Do NOT re-plan — Phase 1 is locked. Plan changes require an ADR (none in this repo yet; first one will create `docs/adr/`).
5. Run `./venv/bin/python3 verify_setup.py` to confirm the environment is intact before touching code.

## Do NOT

- Edit `libs/pyremindkit/src/pyremindkit/models.py` until **Slice 1.3** is the active slice — the field order is the contract freeze point.
- Add new exclude_globs to `VIBE.yaml::architecture` without explicit user approval. The policy is opt-OUT and stays that way.
- Touch the `Claude-*` workflow lists (Pierce's pre-existing ADHD task system). The new visibility-plane lives under `Agents-<project>` after Phase 4 wires the pilot.
- Bypass commit signing (`-S` is mandatory) or skip the per-commit VERSION bump.
