# 02 — Documentation audit

**Agent**: general-purpose / Opus.
**Prompt**: "Audit every markdown file. Identify stale, duplicated, contradictory, or misplaced docs."
**Already known going in** (excluded): the 10 stale root markdowns from Dec 2025 / March 2026.

## Findings (verbatim)

### Critical (current-session contradictions)

- **`CHANGELOG.md` L689 (`[0.1.9]`)** — still reads `_(fill in — what changed in this version)_` even though `[0.1.10]` claims to backfill it. The backfill never wrote to 0.1.9's body. **Fix**: edit the 0.1.9 body to describe S1.1 `is_default` (`[0.1.10]`'s claim).
- **`CHANGELOG.md` L697 (`[0.1.11]`)** — also `_(fill in)_`. No subsequent entry backfills it. **Fix**: edit 0.1.11 body with actual content from that commit, or remove the entry.
- **`README.md`** — **massively stale**. Claims "22 tools" (L189), shows old `libs/pyremindkit/` tree (L648), `RemindKit (libs/pyremindkit/core.py)` data-flow diagram (L785), `pyremindkit included in libs/` (L768), and Version "0.1.0 (Initial Release)" changelog at the tail. No mention of Resources, Prompts, Sampling, deeplinks, SQLite reader, three-tier architecture, FastMCP, Agents-<project> visibility plane, the new 15 tools, etc. **Fix**: full rewrite — known follow-up per PROGRESS.md and `tasks.md::S4.5`.
- **`AGENTS.md` §9 gotchas** (L67) — falsely lists `NO create_calendar / delete_calendar / update_calendar`, `NO flagged setter`, `NO recurrence rules`, `NO alarms`, `NO subtasks` as capability gaps — every single one was shipped in Phase 1+3. **Fix**: rewrite §9 to list the current real gotchas (SQLite `immutable=1` bug, dead `on_reminder_created` callback, etc.).
- **`src/mcp_apple_reminders/README.md`** — describes the OLD architecture: "22 tools", `libs/pyremindkit/src/pyremindkit/...` import paths (L42, L72, L82), `app: Server` (low-level not FastMCP), `module-level remind = RemindKit()` (replaced by lifespan). References deleted `libs/pyremindkit/VENDOR.md`. **Fix**: full rewrite — describe FastMCP + lifespan + Bridge + _native/ + 37 tools + resources/ + prompts/.
- **`src/mcp_apple_reminders/tools/README.md`** — pre-FastMCP. Documents the now-defunct `TOOLS: list[Tool]` / `HANDLERS: dict` aggregation pattern. Current code uses `@mcp.tool` decorators. Lists 4 modules; actual `tools/` now has alarms, bulk, sections, agents, sampling, groups (post-S5.1), etc. **Fix**: rewrite for FastMCP decorator pattern; refresh module table.

### Stale but lower-impact

- **`MAP.md`** — points at `_native/core.py` correctly but doesn't reference resources/, prompts/, `_native/sqlite.py`, `_native/eventkit.py`, `_native/reminderkit.py`, `_native/bulk.py`, `tools/{alarms,bulk,sections,agents,sampling}.py`. "Domains" table covers only the original 4 tool categories. **Fix**: add SQLite-reader, EventKit-helper, ReminderKit-helper, resources/, prompts/, new tool modules.
- **`TASK_STATE.md`** — §0 TL;DR still says "Next action: pick up Slice 0.1" and §5 "Next actions" list starts at S0.1. Stale by ~31 slices. §6 Handoff is from the pre-S0.1 session. Slice 5.1 is correctly added but buried. **Fix**: rewrite §0 + §5; replace §6 handoff with a post-spec-002 entry.
- **`.claude/session-context.md`** — stack line still says `"EventKit via PyObjC; vendored pyremindkit"`; both wrong post-S0.2. `created/updated` both 2026-05-28T00:00:00. Auto-generated stub from retrofit. **Fix**: refresh stack line, or `.gitignore` it (CHANGELOG 0.1.6 says it should be ignored, but it's still committed — verify).

### Fine

- **`docs/SECURITY-REVIEW.md`** — real, thorough OWASP MCP Top 10 walk-through. Keep.
- **`docs/SQLITE_SCHEMA.md`** — real schema notes, including the `immutable=1` lesson. Keep.
- **`docs/TOOLS.md`** — matches live 37-tool surface bit-for-bit. Keep (auto-gen).
- **`docs/adr/0001-list-group-support.md`** — internally consistent; aligns with `tasks.md::S5.1` and `plan.md::Phase 5`. Keep.
- **`src/mcp_apple_reminders/_native/THIRD_PARTY_NOTICES.md`** — pinned at RemCTL `baaa57b…` / 1.0.3 (2026-05-27). Current. Keep. **Note**: S5.1 will add a `create_group` local mod — already pre-documented in ADR 0001.
- **`PROGRESS.md`** — accurate as of right now (31 slices, 37 tools, all phases done, S5.1 next). Keep.
- **`AGENTS.md.pre-retrofit`** — preserved per AGENTS.md §4 layout note; still referenced. Keep.
  *(Note: Audit 01 disagrees and says delete this since git history preserves it; Pierce to decide.)*
- **`specs/002-modernize-and-foundation/{spec,design,plan,tasks}.md`** — internally consistent. spec.md says "22 → 38+ tools by Phase 3" but live is 37 (S4.1 added 1, not all "8+7+1=16" deltas hit); minor projection drift, not a real defect. tasks.md and plan.md track the same 32 slices including Phase 5. Keep.
- **`specs/_archive/001-visibility-foundation/{README,spec,design,plan,tasks}.md`** — correctly archived; archive README explains retirement; the `libs/pyremindkit/` refs inside are correct historical context (the archive shouldn't be rewritten). Keep verbatim.
- **`CHANGELOG.md`** structure (versions 0.1.6 → 0.1.42, 37 entries) — well-formed apart from the two `_(fill in)_` holes above and a stale "libs/pyremindkit" refs inside pre-S0.2 entries (those refs are historically accurate, not bugs).

### Cross-reference fallout (when the 10 stale root files are deleted)

- `AGENTS.md.pre-retrofit` L26 lists `README.md, QUICKSTART.md, TOOLS.md, PROJECT_SUMMARY.md, WORKFLOW_FEATURES.md` — historical doc, leave as-is.
- `PROJECT_SUMMARY.md` → `QUICKSTART.md` → `TESTING_REPORT.md` → `WORKFLOW_FEATURES.md` → `FINAL_WORKFLOW_SUMMARY.md` → `NEW_FEATURES_SUMMARY.md` → `COMPREHENSIVE_TEST_RESULTS.md` form a self-referential mesh of stale files; deleting all 10 together produces zero dangling refs (verified — only intra-cluster refs).
- `TOOLS.md` (root, stale) is referenced by `PROJECT_SUMMARY.md` (also deleting), `CHANGELOG.md` (historical, fine), `PROGRESS.md` + `TASK_STATE.md` + `specs/002/tasks.md` — those all point to `docs/TOOLS.md` (the new auto-gen one), not the root `TOOLS.md`. Safe to delete root `TOOLS.md`.

### One-liner fix plan

1. Delete the 10 stale root markdowns (already planned).
2. Edit `CHANGELOG.md` L689 + L697 to fill in 0.1.9 / 0.1.11 placeholders.
3. Rewrite `README.md`, `AGENTS.md §9`, `src/mcp_apple_reminders/README.md`, `src/mcp_apple_reminders/tools/README.md` for post-spec-002 reality.
4. Refresh `MAP.md` Domains table + Components for new modules.
5. Rewrite `TASK_STATE.md` §0 / §5 / §6.
6. Refresh `.claude/session-context.md` (or verify gitignore status).
