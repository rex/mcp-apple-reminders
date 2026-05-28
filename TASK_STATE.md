# TASK_STATE — 002-modernize-and-foundation

> Source of truth for in-flight work. Humans and agents both write here.
> Committed to the repo. Survives sessions, machines, context compactions.
>
> Spec: `specs/002-modernize-and-foundation/spec.md` ·
> Plan: `specs/002-modernize-and-foundation/plan.md` ·
> Tasks: `specs/002-modernize-and-foundation/tasks.md`
> Branch: `main` (trunk-strategy — all work commits directly to main, no feature branches) ·
> Owner (human): @pierce · Last update: 2026-05-28 by Claude (post-research re-plan)

## 0. TL;DR for a fresh agent session

Spec `001-visibility-foundation` was retired (archived in `specs/_archive/`) after a research pass against gold-standard MCP servers and the actual RemCTL architecture. The successor spec — **`002-modernize-and-foundation`** — adopts RemCTL's three-tier native pattern: (1) direct SQLite reads of the Reminders.app store (tens of milliseconds, exposes sections/subtasks/tags/attachments/alarms/recurrence for free), (2) Swift EventKit helper subprocess for public-API writes (borrowed from `viticci/remctl::remctl-bridge.swift`), (3) Objective-C ReminderKit helper subprocess for private-API writes (borrowed from `viticci/remctl::remctl-private.m`). Plus FastMCP, MCP 1.27+, Resources/Prompts/Sampling/Elicitation, deeplinks on every Reminder + Calendar response, and the agent-visibility-plane pilot. **Next action: pick up Slice 0.1** — bump `mcp>=1.27` and PyObjC pins. Slice 1.1 (is_default fix) is already complete; preserved in commit `117cc8a`.

## Standing user directives

- Subtasks must land in Phase 1 (Pierce-explicit, 2026-05-28). Now backed by ReminderKit private API (Pierce-explicit, 2026-05-28).
- No grandfathering ever — bring files into compliance via refactor, not exclude_globs.
- All four phases (modernize + P0 + MCP primitives + feature parity + visibility-plane) — Pierce-explicit "all four phases", 2026-05-28.
- ALL subagents run on Opus (Pierce-explicit, 2026-05-28, global preference — see `mem:global/agent_model_policy`).
- Modernize-first ordering — Phase 0 happens before any new capability work (Pierce-explicit, 2026-05-28).
- Interactive autonomy — stop and ask between meaningful steps.

## 1. Phases

| # | Phase | Status | Exit criteria |
|---|---|---|---|
| 0 | Modernize platform (FastMCP, MCP 1.27+, lifespan, Pydantic, Context logging) | ⏸ pending | All 22 existing tools work end-to-end on the new substrate; no surface changes |
| 1 | P0 capabilities (SQLite reader + calendar lifecycle + ReminderKit helper integration + subtasks + flagged + tags + sections) | 🟡 partial | S1.1 done (117cc8a); S1.0 + S1.2-1.8 pending |
| 2 | MCP protocol primitives (Resources, Prompts, Sampling, Elicitation, progress) | ⏸ pending | Resources surface live views; 4 prompts; sampling proven on one tool |
| 3 | Feature parity (alarms time + location, recurrence, bulk ops, multi-cal query) | ⏸ pending | Matches FradSer/apple-events feature surface + bonus |
| 4 | Visibility-plane pilot + cross-cutting (security, kill switches, docs sweep) | ⏸ pending | Agents-<project> bootstrap; SECURITY-REVIEW.md done |

Statuses: `⏸ pending` · `🟡 in-prog` · `✅ done` · `🔴 blocked`

## 2. Slices

### Slice 0.1 — Upgrade `mcp>=1.27` + PyObjC pins  ← NEXT

- Status: ⏸ pending
- Owner: unassigned
- Files (planned edits): `pyproject.toml`, `requirements.txt`, `verify_setup.py`
- Files (do NOT edit): server.py, tools/, _native/ (touched in S0.2-0.4)
- Depends on: (none)
- Acceptance: see `specs/002-modernize-and-foundation/tasks.md::S0.1`.

### Slice 0.2 — Rename libs/pyremindkit → src/mcp_apple_reminders/_native/

- Status: ⏸ pending
- Files: many (move + import updates)
- Depends on: S0.1
- Acceptance: see `tasks.md::S0.2`. Tip: do this with git mv for history preservation.

### Slice 0.3 — Pydantic models

- Status: ⏸ pending
- Files: `src/mcp_apple_reminders/models.py` (new), `_native/_internal.py`
- Depends on: S0.2
- Acceptance: see `tasks.md::S0.3`. CONTRACT FREEZE at end of this slice for the Reminder field order.

### Slice 0.4 — FastMCP migration

- Status: ⏸ pending
- Files: `server.py` (rewrite), every `tools/*.py`, new `lifespan.py`
- Depends on: S0.3
- Acceptance: see `tasks.md::S0.4`. THE BIGGEST SLICE — may need split mid-execution.

### Slice 0.5 — Context-based logging

- Status: ⏸ pending
- Files: every `tools/*.py`, server.py
- Depends on: S0.4
- Acceptance: see `tasks.md::S0.5`.

### Slice 0.6 — Native build pipeline (borrow Swift + Obj-C helpers from RemCTL)

- Status: ⏸ pending
- Files: `_native/src/rem_eventkit.swift`, `_native/src/rem_reminderkit.m`, `_native/THIRD_PARTY_NOTICES.md`, `Makefile`, `install.sh`
- Depends on: S0.5
- Acceptance: see `tasks.md::S0.6`. Borrows from `viticci/remctl` (MIT) with attribution.

### Slice 1.0 — Direct SQLite reader (NEW — first slice of Phase 1 after 1.1)

- Status: ⏸ pending
- Files: `_native/sqlite.py`, `_native/bridge.py`
- Depends on: S0.6
- Acceptance: see `tasks.md::S1.0`. Replaces slow EventKit iteration for `list_calendars`, `search_reminders`, `get_reminders`. Reads sections, subtasks, tags, attachments, alarms metadata, recurrence metadata — all from one fast indexed query.

### Slice 1.8 — `assign_section` (NEW)

- Status: ⏸ pending
- Files: `tools/reminders.py`, `_native/reminderkit.py`
- Depends on: S1.7
- Acceptance: see `tasks.md::S1.8`.

### Slices 1.2-4.5 — see tasks.md

(Detailed acceptance criteria for all 19 remaining slices live in `specs/002-modernize-and-foundation/tasks.md`. TASK_STATE here tracks active phase + slice; the full catalog is one indirection away.)

## 3. Blockers / open questions

- **SQLite schema column names** — verify at S1.0 implementation. Schema dump captured as inline comments. Schema has been historically stable for years; RemCTL relies on it.
- **Helper-process lifetime mode** (long-lived vs per-call) — decided at S0.6 based on borrowed RemCTL pattern.
- **Deeplink UUID resolution** — verify EKReminder.calendarItemIdentifier matches SQLite ZIDENTIFIER. Verified at S0.3.
- **ReminderKit helper ABI** — confirm the JSON-over-stdio protocol from RemCTL's `remctl-private.m` works verbatim or whether we wrap. Decided at S1.4.
- **Sampling-driven `triage_brain_dump` UX** — sync vs async return shape. Decided at S2.5.

## 4. Recent decisions (append-only, newest first)

- 2026-05-28 — **Spec 002 pivoted to RemCTL three-tier architecture** (SQLite direct reads + Swift EventKit helper subprocess + Obj-C ReminderKit helper subprocess). Replaces the earlier "PyObjC for everything" approach. Borrows `remctl-bridge.swift` and `remctl-private.m` from `viticci/remctl` (MIT, 40★, last push 2026-05-26) with attribution. Added Slice 0.6 (native build pipeline) and Slice 1.0 (SQLite reader). Reminder + Calendar Pydantic models gain `deeplink: str` field. All Pierce-explicit.
- 2026-05-28 — Spec 001 retired, replaced by spec 002 (`modernize-and-foundation`). Scope materially expanded after research found (a) public EventKit lacks subtasks/tags, (b) ReminderKit private framework exists and works on macOS 26.1, (c) MCP Python SDK at 1.27.1 with FastMCP + Resources + Prompts + Sampling + Elicitation, (d) competitor `FradSer/apple-events` ships full feature set in 533 commits.
- 2026-05-28 — Subtask backend: **ReminderKit private API via PyObjC** (Pierce-explicit, post-verification that the framework exists at `/System/Library/PrivateFrameworks/ReminderKit.framework`).
- 2026-05-28 — Scope: **all four phases** (Pierce-explicit). ~22 slices, ~2-3 weeks realistic.
- 2026-05-28 — Modernize-first ordering (Pierce-explicit).
- 2026-05-28 — ALL agents run on Opus (Pierce-explicit, global). Cross-cutting work to bake into agentic-skeleton.
- 2026-05-28 — Slice 1.1 (is_default fix) preserved across the re-plan; status `✅ done` (commit 117cc8a).
- 2026-05-28 — Subtasks scoped into Phase 1 (Pierce explicit, "absolute must").
- 2026-05-28 — Phase 0.3 (Pydantic models) is the contract-freeze point — `Reminder` field order locked after.

## 5. Next actions (ordered)

1. Pick up **Slice 0.1** (upgrade `mcp>=1.27`). Smallest possible kickoff — version pin + verify-setup probe.
2. **Slice 0.2** (rename `libs/pyremindkit` → `src/mcp_apple_reminders/_native`). Mostly mechanical with `git mv` + import updates.
3. **Slice 0.3** (Pydantic models with `deeplink`). CONTRACT FREEZE point. Verify EKReminder.calendarItemIdentifier == SQLite ZIDENTIFIER.
4. **Slice 0.4** (FastMCP migration). The big one. May split mid-execution.
5. **Slice 0.5** (Context logging) — cleanup pass.
6. **Slice 0.6** (native build pipeline) — borrow `remctl-bridge.swift` + `remctl-private.m` from `viticci/remctl` with attribution; compile to `_native/bin/`. Decide long-lived vs per-call subprocess mode.
7. Phase 1 begins with **Slice 1.0** (SQLite reader) — drastically faster reads + bonus features (sections, attachments, alarms metadata).
8. Then **Slice 1.2** (`create_calendar`) and onward through Phase 1.
9. After Phase 1 lands, expand Phase 2 tasks if needed (currently fully enumerated).
10. After Phase 2, plan Phase 3 in detail (currently sketched).
11. Phase 4 last (visibility-plane pilot is the payoff).

## 6. Handoff note (fill when ending a session)

2026-05-28 (Claude, /retrofit → research → re-plan session): Repo retrofit complete and merged to main. Spec 002 replaces spec 001 after gold-standard research surfaced significant new opportunities (FastMCP, MCP 1.27+, ReminderKit private API for subtasks/flagged/tags, competitor feature surface). Next agent: read this file's §0 + Slice 0.1, read `specs/002-modernize-and-foundation/spec.md` and `design.md`, then start S0.1 (`mcp>=1.27` upgrade). `verify_setup.py` is the safety net — run it after each substrate change. Slice 1.1 is preserved as already-done; don't re-do it.
