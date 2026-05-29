# PROGRESS

- **Project**: mcp-apple-reminders (python-mcp; macOS-only EventKit + ReminderKit MCP server)
- **Active branch**: `main` (trunk strategy)
- **Active feature spec**: `specs/002-modernize-and-foundation/` + `docs/adr/0001-list-group-support.md`
- **Active TASK_STATE**: `TASK_STATE.md`
- **Last session**: 2026-05-29 (Claude — autonomous slice sprint + audit + ADR 0001 + S5.1)

## 🎯 Where we stand

- **41 MCP tools** registered.
- **3 static MCP Resources + 2 templated** (`reminders://` + `agents://current/{project_name}`).
- **4 Prompts** (`daily_review`, `weekly_retro`, `brain_dump_triage`, `agent_visibility_sync`).
- **74 source files** scanned; all under 400-LOC hard cap; module shape gate green across 43 modules.
- **`make lint && make check-architecture && make typecheck`** — all green.
- **8 live round-trips PASSED** end-to-end against the user's Reminders.app this session.

## Phase status

| Phase | Status | Notes |
|---|---|---|
| 0 — substrate | ✅ done (6/6) | S0.1–S0.6 |
| 1 — P0 capabilities | ✅ done (9/9) | S1.0–S1.8 |
| 2 — MCP primitives | ✅ done (5/5) | S2.1–S2.5 |
| 3 — feature parity | ✅ done (6/6) | S3.1–S3.6 |
| 4 — visibility plane + cross-cutting | ✅ done (4/5) | S4.1, S4.3, S4.4, S4.5. **S4.2 TodoWrite mirror = stretch, deferred** (awaits Claude Code hookable TodoWrite surface). |
| 5 — list-group support (ADR 0001) | ✅ done (1/1) | S5.1. Includes `delete_group` follow-up patch. |

**32 slices shipped this session.**

## Outstanding follow-up streams (NOT yet planned/specced)

### CL-1 — Post-spec-002 cleanup pass — **NEXT**

Captured in full at `docs/audits/2026-05-29-post-spec-002-cleanup-audit/`. 37
distinct findings across 4 dimensions:

- 5 CRITICAL bugs (silent `move_reminder_blocked` routing, 4 un-collectable
  test modules, README `import main` ImportError, `pyproject.testpaths` lies,
  2 unfilled CHANGELOG placeholders).
- ~18 HIGH (README + AGENTS.md §9 + src-tree READMEs + MAP.md all lying about
  reality; tools/__init__.py re-exports 5 of 9 modules; format_reminder dead;
  3 skeleton hooks drifted v0.37.0).
- ~14 MEDIUM (polish, consistency, attribution placement, `.claude/` spillover).

**Open decision** (Pierce to call): single slice `CL-1` or split `CL-1a` docs /
`CL-1b` source / `CL-1c` tests-into-`tests/` relocate / `CL-1d` skeleton drift.

### CL-2 (proposed) — Capability extensions (smart lists, badges, pinning)

Optional follow-up slice batch — every backend action already exists in the
helper. Roughly **~3 medium slices**:

- Smart lists: `create_smart_list`, `update_smart_list`, `delete_smart_list`
  MCP tools (~1 slice).
- Calendar parameter extensions: `badge_emblem`, `is_pinned`, `sorting_style`
  on `create_calendar` + `update_calendar`. Add `update_group` tool. (~1 slice).
- Helper extensions for `clear_tags` + `set_urgent` + `set_early_reminder` MCP
  exposure. (~1 slice).

### S4.2 — TodoWrite mirror (originally planned)

Stretch goal. Pending hookable surface in Claude Code's TodoWrite tool.

## Last decisions

- 2026-05-29 — **Test artifact cleanup**: Swift `delete_list` cannot see
  groups (EventKit can't see them). Added Obj-C `delete_group` action via
  `removeFromParentWithAccountChangeItem:` selector. Live test rewritten to
  self-clean by detaching child → deleting child via Swift → deleting group
  via Obj-C. Zero orphans now.
- 2026-05-29 — **S5.1 reverse-engineering finding**: `setParentListID:` is the
  correct selector for reparenting a list under a group. `setParentOwnerID:`
  is for account-parent semantics only and returns `com.apple.reminderkit
  error -1` when given a group's REMObjectID. The SQLite column `ZPARENTLIST`
  was the clue that the matching setter mirrored it.
- 2026-05-29 — **ADR 0001 / Phase 5** introduced for list-group support.

## How to resume

1. Read `AGENTS.md` (gotchas + agent contract).
2. Read `TASK_STATE.md` (current phase + slice).
3. Read `docs/audits/2026-05-29-post-spec-002-cleanup-audit/README.md` for the
   cleanup-pass landscape.
4. Read `docs/adr/0001-list-group-support.md` for the Phase 5 background.
5. `make lint && make check-architecture && make typecheck` should be green.
6. `verify_setup.py` validates the environment.

## Standing rules

- Trunk strategy: commit + push together. Never leave committed-but-unpushed.
- ALL subagents on Opus (Pierce-explicit global preference, `mem:global/agent_model_policy`).
- VIBE.yaml rules apply to ALL first-party code; only vendored upstream
  (`_native/src/*.swift`/`*.m` from `viticci/remctl` MIT) is exempt.
- No grandfathering ever. `_native/src/*` is the one documented exception.
- Subtasks via ReminderKit helper subprocess, NOT PyObjC / AppleScript.
- Deeplinks on every Reminder + Calendar response
  (`x-apple-reminderkit://REMCD{Reminder,List}/{id}`).
- Pre-commit gates: signed (-S), VERSION bump, CHANGELOG entry.

## Do NOT

- Edit `models.py::Reminder` field order (S0.3 CONTRACT FREEZE; tail-add only
  with default, never reorder).
- Add `VIBE.yaml::architecture.exclude_globs` without explicit user approval.
  Only `_native/src/*.swift`/`*.m` (vendored upstream MIT) is approved.
- Touch `Claude-*` workflow lists (Pierce's pre-existing ADHD system). The
  visibility-plane lives under `Agents-<project>` after S4.1.
- Re-open `immutable=1` on the SQLite connection. It caches and hides
  concurrent helper writes. Documented in `docs/SQLITE_SCHEMA.md`.
- Reach for AppleScript bridging. Path is borrowed RemCTL Swift + Obj-C.
- Use `setParentOwnerID:` for group-parent semantics. It's account-only.
  Use `setParentListID:` for groups (S5.1 reverse-engineered).
