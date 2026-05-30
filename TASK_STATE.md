# TASK_STATE — 002-modernize-and-foundation (+ CL-1 cleanup)

> Source of truth for in-flight work. Humans and agents both write here.
> Committed to the repo. Survives sessions, machines, context compactions.
>
> Spec: `specs/002-modernize-and-foundation/` (spec · plan · tasks) ·
> ADR: `docs/adr/0001-list-group-support.md` ·
> Audit: `docs/audits/2026-05-29-post-spec-002-cleanup-audit/`
> Branch: `main` (trunk strategy) · Owner (human): @pierce · Last update: 2026-05-30 by Claude (CL-2.6–2.9 + 2 wire bug fixes; pre-compaction handoff)

## 0. TL;DR for a fresh agent session

Spec **002 (modernize-and-foundation) is COMPLETE** — all of Phases 0–5 shipped: FastMCP on MCP 1.27.1, the three-tier native substrate (direct SQLite reads + Swift EventKit helper subprocess + Obj-C ReminderKit helper subprocess), frozen Pydantic v2 models with deeplinks, **41 MCP tools**, 5 Resources, 4 Prompts, Sampling, Elicitation, alarms/recurrence/bulk, the agent-visibility plane (S4.1), and list-groups (S5.1, ADR 0001). The only originally-planned slice not shipped is **S4.2** (TodoWrite mirror — stretch, deferred until Claude Code exposes a hookable TodoWrite surface).

**CL-1 cleanup pass: COMPLETE** (2026-05-29) — all 9 batches (B0–B9) plus the CRITICAL EventKit write-swallow bugfix shipped (commits `aa613fb`→`3b2c2b2`), each gate-green + pushed. Audit + plan live in `docs/audits/2026-05-29-post-spec-002-cleanup-audit/`. One sub-item was DECLINED: `make sync-skeleton` on the 3 hooks (the skeleton v0.37.0 versions regressed `cd … || exit 1`; see §2 + AGENTS §9). **CL-2 capability expansion: slices 2.1–2.13 SHIPPED** (2026-05-30, v0.1.84) — smart lists; list/group appearance+pinning; templates; grocery; urgent/early-reminder/sections; **2.6 attachments** (generic files unlocked in `rem_reminderkit.m`; local-file tool opt-in behind env `MCP_APPLE_REMINDERS_ENABLE_FILE_ATTACHMENTS`); **2.7 read-side** (`get_recently_deleted` + `reminders://recently-deleted`; `flagged` filter; ZPARENTREMINDER fix → `parent_reminder_id`/`subtasks` populate); **2.8 `clear_tags`** + `reminders://tags`; **2.9 recurrence/alarm/early-reminder read-back** (ADR 0002). Now **58 tools, 8 resources (6 static + 2 templates), 5 prompts, 2 ADRs**. Plus two wire-level BUG FIXES this session (see AGENTS §9): **datetime structured-output v0.1.77**, **elicitation-guard v0.1.78**. **CL-2.10–2.13 all SHIPPED**: 2.10 ToolAnnotations on all 58 tools (shared READ/CREATE/MUTATE/DESTROY presets + human titles, v0.1.81); 2.11 typed result models (`results.py` — WriteResult/DeleteResult/BulkResult/TriageResult, v0.1.82); 2.12 resources/prompts polish (titles + `organize_into_sections` prompt + per-param `Field(description=)`; complete/uncomplete split to `tools/completion.py`, v0.1.83); 2.13 catalog regen + docs sweep (v0.1.84). **CL-2 is COMPLETE.** **USER DIRECTIVE (2026-05-30): CL-2.10–2.13 are SHIPPED; NOW BEGIN the integration-testing phase — which Pierce specified is FULLY AUTOMATED, agent-driven end-to-end, and EXHAUSTIVE.** Integration fixture already in the store: group `CL29-Alarm-Tests` → list `Alarm Lab` (id `94F21A71-6D6B-47BE-A7D9-329A2E57AD85`), 8 items covering every alarm/recurrence type — KEEP until integration testing is complete. **INTEGRATION SUITE COMPLETE** (`tests/integration/`, run `./venv/bin/python -m tests.integration.run $(date +%H%M%S)`; NOT in the unit gate, needs Reminders permission; 12 scenario modules + harness + self-cleaning `MCP-IntegTest` fixture): **165 wire-level checks green** (v0.1.85→v0.1.91) covering every tool family — CRUD, alarms/recurrence/early-reminder read-back (ADR 0002), queries + all 7 `reminders://` resources, calendars, groups, workflow board moves, smart-lists/appearance/pinning, subtasks/sections, templates/grocery, attachments + file-gate, bulk — and all 5 prompts. **2 REAL BUGS FOUND + fix tasks spawned** (both encoded as self-flipping expected-error known-issues): (1) `set_urgent` crashes the ReminderKit helper (`urgentAlarmContext` unrecognized selector); (2) `create_smart_list` without `filter_data_b64` errors "filterData is required" (contradicts its docs). SQLite read-after-write lag on hashtag/subtask/section rows is handled by polling (not a bug).

## Standing user directives

- Subtasks land in Phase 1 (Pierce-explicit, 2026-05-28). Backed by ReminderKit private API.
- No grandfathering ever — bring files into compliance via refactor, not exclude_globs.
- ALL subagents run on Opus (Pierce-explicit, 2026-05-28, global — see `mem:global/agent_model_policy`).
- Trunk strategy: commit directly to main, signed; bump VERSION + push every commit (commits are atomic with their push).
- Interactive autonomy — stop and ask between meaningful steps (overridden per-task by explicit user go-ahead, e.g. the CL-1 autonomous run).

## 1. Phases

| # | Phase | Status | Exit criteria |
|---|---|---|---|
| 0 | Modernize platform (FastMCP, MCP 1.27+, lifespan, Pydantic, Context logging, native build) | ✅ done | All tools work end-to-end on the new substrate |
| 1 | P0 capabilities (SQLite reader + calendar lifecycle + ReminderKit + subtasks + flagged + tags + sections) | ✅ done | S1.0–S1.8 landed |
| 2 | MCP protocol primitives (Resources, Prompts, Sampling, Elicitation, progress) | ✅ done | S2.1–S2.5 |
| 3 | Feature parity (alarms time+location, recurrence, bulk, multi-cal query, completed-in-range) | ✅ done | S3.1–S3.6 |
| 4 | Visibility-plane pilot + cross-cutting (security, kill switches, docs, streamable HTTP) | ✅ done (4/5; S4.2 deferred) | S4.1/S4.3/S4.4/S4.5 |
| 5 | List-group support — ADR 0001 | ✅ done | S5.1 shipped 2026-05-29 |

Statuses: `⏸ pending` · `🟡 in-prog` · `✅ done` · `🔴 blocked`

## 2. Slice status

All slices across Phases 0–5 are ✅ done: S0.1–S0.6, S1.0–S1.8, S2.1–S2.5, S3.1–S3.6, S4.1/S4.3/S4.4/S4.5, S5.1. **S4.2 (TodoWrite mirror)** is the lone deferred stretch slice. Per-slice acceptance lives in `specs/002-modernize-and-foundation/tasks.md`; the build history is in `CHANGELOG.md` + git.

### CL-1 cleanup batches (2026-05-29)

- B0 ✅ capture verify+expert synthesis (`docs/audits/.../05-verify-and-expert-review-synthesis.md`)
- B1 ✅ delete `requirements.txt` + `AGENTS.md.pre-retrofit` (IaC/scaffold/retrofit `.claude` files left in place — skeleton-owned; deleting per-repo fights `sync-skeleton`)
- B2 ✅ sweep 10 stale root markdowns + relocate `MAP.md` → `docs/MAP.md`
- B3 ✅ backfill CHANGELOG `[0.1.9]` / `[0.1.11]` placeholders
- B4 ✅ relocate suite → `tests/` (`tests/_support/`) + fix CQ-2 collection (orchestrator `__test__ = False`)
- B9 ✅ build-config: Makefile/pyproject → `tests/`, `test-actual` target, repair 4 stale `reminderkit_actions` test imports
- B5 ✅ documentation rewrites (README, both src READMEs, docs/MAP.md, AGENTS.md §9, TASK_STATE.md)
- B6 ✅ dead-code removal (`format_reminder`, dead `on_reminder_*` callbacks, dead cancel branch + `BulkCancelled`) + `tools/__init__` 5→10
- B7 ✅ `_app_context`/`_bridge_from_ctx` deduped into `lifespan.py` (alias imports across all 10 modules)
- B8 ✅ per-module small fixes (docstrings, hoist `_ConfirmCascade`, drop `_unused` hack, silent-`[]`→raise)
- CL-bug ✅ EventKit write-swallow fixed in both sinks + regression tests (v0.1.58)
- (final) ⊘ `make sync-skeleton` **DECLINED** — v0.37.0's 3 hooks dropped `cd … || exit 1` (shellcheck SC2164 regression, less safe). Repo's hooks kept (intentionally ahead); their `check-skeleton` drift is expected. Fix belongs upstream in the skeleton.

## 3. Blockers / open questions

- ✅ **(FIXED v0.1.58) EventKit write-swallow** — `_save_ek_reminder` (`_internal.py`) and `RemindKit.delete_reminder` (`core.py`) now unpack the PyObjC `(BOOL, NSError)` out-param tuple and raise `RuntimeError(localizedDescription())` on failure; regression tests in `tests/test_write_error_propagation.py`. Bulk ops now surface real per-item failures in `failed[]`.
- All prior spec-002 open questions (SQLite schema, helper lifetime mode, deeplink UUID equivalence) were resolved during the build.

## 4. Recent decisions (append-only, newest first)

- 2026-05-29 — **CL-1 cleanup pass** executed via a dynamic verify+expert-review workflow (19 agents). Decisions: IaC/scaffold/retrofit `.claude/` files are skeleton-owned and left in place (per-repo deletion fights `sync-skeleton`); `PROGRESS.md` kept (owner-deferred merge into TASK_STATE); `make sync-skeleton` hook refresh deferred to the end of the run; the audit's #1 "CRITICAL" (`move_reminder_blocked` mismatch) re-judged a non-bug and dropped.
- 2026-05-28 — Spec 002 pivoted to the RemCTL three-tier architecture (SQLite reads + Swift EventKit helper + Obj-C ReminderKit helper), borrowing `remctl-bridge.swift` + `remctl-private.m` from `viticci/remctl` (MIT) with attribution.
- 2026-05-28 — Spec 001 retired, replaced by spec 002. Scope expanded after research (public EventKit lacks subtasks/tags; ReminderKit private framework works on macOS 26.1; MCP SDK at 1.27.1).
- 2026-05-28 — Subtasks land in Phase 1 (Pierce-explicit). Pydantic models are the S0.3 contract-freeze point (field order locked).
- 2026-05-28 — All subagents on Opus (Pierce-explicit, global). Modernize-first ordering. All four phases in scope.

## 5. Next actions (ordered)

1. Finish CL-1 batches **B5 → B6 → B7 → B8**, then the final `make sync-skeleton`.
2. **CL-bug**: fix the CRITICAL EventKit write-swallow + add the regression test; then re-verify bulk-op `failed[]` populates.
3. **CL-2 capability extensions** (≈3 medium slices): typed result models for the 12 bare `-> dict` tools; smart-list create/manage; templates + grocery + `clear_tags`; `ToolAnnotations` on all 41 tools. Full register: audit doc `05-...md` §5.
4. **Exhaustive integration testing** — Pierce's stated next major phase, after cleanup lands.
5. **S4.2** TodoWrite mirror — if/when Claude Code exposes a hookable TodoWrite surface.

## 6. Handoff note

**2026-05-29 (Claude — CL-1 cleanup pass, autonomous commit-push-per-batch):**

Spec 002 is fully shipped (41 tools, phases 0–5). This session runs the CL-1 cleanup plan from the verify+expert-review workflow. Batches B0–B4 + B9 are committed & pushed; B5 (docs) is in flight. Remaining: B6 (dead code), B7 (lifespan dedup), B8 (per-module fixes), the CL-bug write-swallow fix, and the final `sync-skeleton`. The big new finding is the CRITICAL write-swallow bug in §3 — it is real (adversarially confirmed with a live PyObjC repro) and queued as its own fix+test slice after the cleanup batches.

Before code: read `AGENTS.md` → this file §0/§2/§3 → the audit synthesis `docs/audits/2026-05-29-post-spec-002-cleanup-audit/05-verify-and-expert-review-synthesis.md`. Prior session history (spec-002 build) lives in `CHANGELOG.md` + git log. Session memories worth reading: `mem:core`, `mem:suggested_commands`, `mem:task_completion`, `mem:global/agent_model_policy`.
