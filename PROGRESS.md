# PROGRESS

- **Project**: mcp-apple-reminders (python-mcp; macOS-only EventKit + ReminderKit MCP server)
- **Active branch**: `main` (trunk strategy)
- **Active feature spec**: `specs/002-modernize-and-foundation/`
- **Active TASK_STATE**: `TASK_STATE.md` (Phase 3 / Slice 3.1 ← NEXT)
- **Last session**: 2026-05-28 (Claude — autonomous slice run; 20 slices shipped; Phase 0 + 1 + 2 complete)

## Where things stand

🎯 **Phase 0 (substrate) COMPLETE** — S0.1 → S0.6.
🎯 **Phase 1 (P0 capabilities) COMPLETE** — S1.0 → S1.8. Calendar lifecycle, subtasks, flagged, tags, sections all live-verified end-to-end.
🎯 **Phase 2 (MCP primitives) COMPLETE** — S2.1 (Resources), S2.2 (Prompts), S2.3 (progress), S2.4 (elicitation), S2.5 (sampling).
⏳ **Phase 3 (feature parity)** — S3.1 NEXT (time-based alarms).
⏳ **Phase 4 (visibility-plane pilot)** — pending.

## Quick stats

- **29 MCP tools** registered.
- **4 MCP Resources** (3 static + 1 templated).
- **4 MCP Prompts** (daily_review, weekly_retro, brain_dump_triage, agent_visibility_sync).
- **63 source files** scanned by the architecture gate, all under the 400-LOC hard cap.
- **`make lint && make check-architecture`** green.
- **5 live round-trips** PASSED this session: `create_calendar`, `create+rename+delete`, `subtasks`, `set_flagged`, `tags+filter`, `assign_section`.

## Last three decisions

- 2026-05-28 — `set_parent` (subtask reparenting) deferred to a follow-up patch that extends the borrowed Obj-C helper with a `set_parent` action. The Obj-C helper's `add_subtasks` is one-way (creates new subtasks under a parent); there's no native reparent today. Documented in S1.5 changelog.
- 2026-05-28 — `set_tags` is **additive only** (the helper's `add_tags` action doesn't remove). Parameter is named `add_tags=` to be honest about the semantics. Replacement waits on a `clear_tags` helper extension.
- 2026-05-28 — SQLite `connect()` opens with `mode=ro` (no `immutable=1`). `immutable=1` caches file contents aggressively and prevented the reader from seeing concurrent helper writes — fix discovered mid-S1.5 and is what made every live round-trip green.

## Open blockers

- None active. Phase 3 starts with S3.1 (`set_alarm` for time-based alarms) — the Swift helper already understands `alarm` payload, so the slice should be a small extension to `_native/eventkit.py` + a new tool.

## How to resume (for a fresh agent)

1. Read `AGENTS.md` (project contract, gotchas).
2. Read `TASK_STATE.md` to see which phase/slice is next.
3. Skim `specs/002-modernize-and-foundation/spec.md` for the EARS-notation requirements, then `design.md` for the approach.
4. Do NOT re-plan — spec/design/plan are frozen post-research. Plan changes require an ADR (the first one will create `docs/adr/`).
5. Run `./venv/bin/python verify_setup.py` to confirm the environment is intact before touching code.
6. ALL agent spawns: pass `model: "opus"` explicitly (global policy).

## Do NOT

- Edit `src/mcp_apple_reminders/models.py` after S0.3 lands — the field order is the contract freeze point for the rest of the spec (S0.3 already locked it).
- Add new `exclude_globs` to `VIBE.yaml::architecture` without explicit user approval. The borrowed Swift + Obj-C sources at `_native/src/*` are the one approved exception (documented in `_native/THIRD_PARTY_NOTICES.md`).
- Touch the `Claude-*` workflow lists (Pierce's pre-existing ADHD task system). The new visibility-plane lives under `Agents-<project>` after Phase 4 wires the pilot.
- Bypass commit signing (`-S` is mandatory) or skip the per-commit VERSION bump.
- Re-do S1.1 (`is_default` fix) — already landed in `117cc8a`.
- Reach for AppleScript bridging — Pierce chose ReminderKit. The AppleScript fallback in spec §Unwanted-behavior is degraded-mode only, not a parallel path.
- Re-open `immutable=1` on the SQLite connection — it would re-break concurrent reads after helper writes. Documented in `docs/SQLITE_SCHEMA.md`.
