# PROGRESS

- **Project**: mcp-apple-reminders (python-mcp; macOS-only EventKit + ReminderKit MCP server)
- **Active branch**: `main` (trunk strategy — Pierce explicit 2026-05-28: no feature-branch dance, commits land on main directly)
- **Active feature spec**: `specs/002-modernize-and-foundation/` (replaces archived `001-visibility-foundation`)
- **Active TASK_STATE**: `TASK_STATE.md` (Phase 0 / Slice 0.1 ← NEXT)
- **Last session**: 2026-05-28 (Claude, retrofit → research → re-plan; spec 001 archived, spec 002 written and committed)

## Last three decisions

- 2026-05-28 — Spec 002 supersedes spec 001. After research vs gold-standard, scope expanded to four phases (modernize → P0 → MCP primitives → feature parity + visibility-plane). ReminderKit (private) used for subtasks/flagged/tags. Pierce-explicit on all scope decisions.
- 2026-05-28 — ALL subagents run on Opus (Pierce-explicit global preference; recorded in `mem:global/agent_model_policy`).
- 2026-05-28 — Adopted trunk-strategy: `VIBE.yaml::project.branch_strategy: trunk`.

## Open blockers

- None active. Three known open questions tracked in `TASK_STATE.md §3`: ReminderKit binding ergonomics (S1.4), REMReminder field signatures (S1.5), `triage_brain_dump` UX (S2.5).

## How to resume (for a fresh agent)

1. Read `AGENTS.md` (project contract, gotchas).
2. Read `TASK_STATE.md` §0 and the current Slice (0.1 next).
3. Skim `specs/002-modernize-and-foundation/spec.md` for the EARS-notation requirements, then `design.md` for the approach.
4. Do NOT re-plan — spec/design/plan are frozen post-research. Plan changes require an ADR (the first one will create `docs/adr/`).
5. Run `./venv/bin/python3 verify_setup.py` to confirm the environment is intact before touching code.
6. ALL agent spawns: pass `model: "opus"` explicitly (global policy).

## Do NOT

- Edit `src/mcp_apple_reminders/models.py` after Slice 0.3 lands — the field order is the contract freeze point for the rest of the spec.
- Add new exclude_globs to `VIBE.yaml::architecture` without explicit user approval. The policy is opt-OUT and stays that way.
- Touch the `Claude-*` workflow lists (Pierce's pre-existing ADHD task system). The new visibility-plane lives under `Agents-<project>` after Phase 4 wires the pilot.
- Bypass commit signing (`-S` is mandatory) or skip the per-commit VERSION bump.
- Re-do Slice 1.1 (`is_default` fix) — already landed in `117cc8a`.
- Reach for AppleScript bridging — Pierce chose ReminderKit. The AppleScript fallback in spec §Unwanted-behavior is degraded-mode only, not a parallel path.
