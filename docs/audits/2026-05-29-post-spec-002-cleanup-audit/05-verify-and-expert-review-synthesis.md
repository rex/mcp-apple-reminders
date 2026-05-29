# CL-1 Verify + Expert-Review Synthesis (2026-05-29)

> Produced by the `cl1-verify-and-expert-review` **dynamic workflow** — 19
> agents, ~1.9M tokens, 5 stages: Ground (current MCP/FastMCP/Pydantic docs) →
> Verify-existing ‖ Expert-review (5 lenses) → Synthesize → Adversarial-verify.
> Run ID `wf_6ad8909b-e3f`. HEAD at run time: `e03ff55`.
>
> This file is the durable record. Reports 01–04 captured the original
> 37-finding human audit; this pass re-verifies them against HEAD **and** adds
> a fresh bleeding-edge expert dimension that found a CRITICAL bug the human
> audit missed. Doc-grounding confirmed: repo runs `mcp 1.27.1` (FastMCP is the
> current 1.x high-level API; v2 renames it to `MCPServer` — not yet relevant,
> repo correctly pins `mcp<2`), `pydantic 2.13.4`, `pyobjc 12.1`.

## 0. Executive summary

HEAD is **healthier than the 37-finding audit implied** — `.DS_Store`/`.log`
already untracked, `GEMINI.md`/`CLAUDE.md` already symlinked, and the
code-quality "CRITICAL" `move_reminder_blocked` mismatch is now internally
consistent (drops out). What remains is overwhelmingly **documentation rot**,
**file-organization debt**, and a tight cluster of **small source cleanups** —
sequenced into 9 conflict-free serial batches. The expert pass separately
surfaced **2 real correctness bugs** (write-failure swallowing + bulk
false-success), large **protocol/currency gaps** (zero ToolAnnotations on 41
tools; 12 bare `-> dict` tools emitting no `outputSchema`), and a big
**feature-parity backlog** where the Obj-C backend already exists but no Python
surface does (~70% of `rem_reminderkit.m` unexposed).

## 1. 🔴 CRITICAL (NEW) — EventKit write failures silently swallowed

`_native/_internal.py:110-114` and `_native/core.py:205-209`:

```python
error = None
success = store.saveReminder_commit_error_(reminder, True, error)
if not success:
    raise RuntimeError(...)
```

PyObjC folds the trailing `NSError**` out-param into the **return value**, so
the call returns a `(BOOL, NSError)` **tuple** — always truthy. `not success`
is therefore never true: **the failure branch is dead code and every write
reports success.**

- **Adversarial repro (confirmed, high confidence):** in the repo venv (PyObjC
  12.1), saving a reminder with no calendar returned `(False, <NSError "No
  calendar has been set.">)`; `bool(tuple)` → `True`.
- **Blast radius:** create / update / move / complete / uncomplete / delete
  (single commit sink `_save_ek_reminder` + the second sink
  `removeReminder_commit_error_`). Bulk ops therefore report false
  `{processed:N, failed:[]}` while the elicitation confirm tells the user a
  destructive op succeeded.
- **Note:** this also means AGENTS.md §9's "errors always say `None`" is wrong —
  the error path never runs at all.
- **Fix (own slice, not cleanup):** tuple-unpack
  (`ok, err = store.save..._error_(r, True, None)`), raise
  `RuntimeError(err.localizedDescription())` on failure, add a regression test
  monkeypatching the EKEventStore method to return `(False, fakeNSError)`.

## 2. Verification of the original 37 findings vs HEAD

Tally across the 4 reports (~61 line-items): **55 still-present · 3 partial · 2
stale-drop · 1 already-fixed.**

**Already fixed (no action):** `GEMINI.md` is a symlink; `.DS_Store` + `.log`
untracked (on-disk `rm` only); `.claude/session-context.md` gitignored;
CHANGELOG `[0.1.41]` backfilled in `[0.1.42]`; `server.py` instructions string
rewritten in S5.1.

**Stale / non-actionable (dropped):** `scripts/` clean; `specs/_archive/001`
parked; VIBE.yaml accurate; `.pre-commit-config.yaml` fine; `install.sh` body
fine (only the requirements.txt line goes); positive MCP confirmations
("stdout discipline clean", "`await ctx.info` correct for 1.27 — do NOT migrate
to v2 `ctx.log`").

**Downgraded CRITICAL — `move_reminder_blocked` (owner may veto):** the audit's
#1 CRITICAL claimed a tool/name mismatch. At HEAD the tool name, description
("Move … to the Claude-Waiting workflow list … blocked or waiting for external
input"), and target (`_move_to_named_list … "Claude-Waiting"`) are all
internally consistent. "blocked" = "waiting for external input" =
`Claude-Waiting` is coherent by design → **dropped, no rename, no edit.**

## 3. Cleanup execution plan — 9 batches

Ordered so prerequisites precede dependents and **no two batches edit the same
file**. Executed serially under the 400-LOC cap with a real `--changelog-note`
bump + signed commit + push per batch. **Execution reorder:** B9 runs
immediately after B4 (they are file-disjoint) because relocating tests breaks
`make lint`'s root-glob until B9 repairs the Makefile, and the Stop hook runs
`make lint` at every turn boundary.

| # | Batch | Files (one per batch) |
|---|---|---|
| 1 | Pure deletions + on-disk noise | requirements.txt, install.sh (ref line), AGENTS.md.pre-retrofit, .claude terraform/ansible/scaffold/retrofit, *.DS_Store, *.log |
| 2 | Stale root-markdown sweep + MAP relocate | ~10 dead root .md, dup TOOLS.md, FIXES/TESTING reports; `git mv MAP.md docs/MAP.md` |
| 3 | CHANGELOG placeholder backfill | CHANGELOG.md (`[0.1.9]` L814, `[0.1.11]` L806) |
| 4 | Relocate tests → `tests/` + rename 4 workflow modules | 29 `test_*.py` + `test_support/` → `tests/`(`_support/`); drop `test_` prefix on the 4 fixtureless workflow modules |
| 9 | Build-config (after B4) | pyproject (testpaths/email/urls/dev-extras/mypy), Makefile (lint+test → `src/ tests/`), `make sync-skeleton` (3 hooks), claude_desktop_config |
| 5 | Documentation rewrites | README, both src READMEs, AGENTS.md §9, docs/MAP.md, TASK_STATE.md, session-context |
| 6 | Dead-code removal | formatting.py (`format_reminder`), core.py (dead callbacks + create loop), _native/bulk.py (dead cancel branch), tools/__init__ (5→10 modules) |
| 7 | `_app_context`/`_bridge` dedup into lifespan | lifespan.py + 8 tool modules (watch 400-LOC on lifespan.py) |
| 8 | Per-module small fixes | reminders/calendars/queries/sections/groups/bulk + tests/test_bulk_ops.py |

**Owner-deferred:** PROGRESS.md merge/delete (FO-6) — PROGRESS.md was touched
at HEAD and is used for compaction handoff; **kept** (not deleted) pending
explicit owner approval.

## 4. Conflict map (files touched by >1 finding)

- **CHANGELOG.md** ← B3 `[0.1.9]`/`[0.1.11]` (the `move_reminder_blocked` note is dropped)
- **README.md** ← stale tool count + libs/pyremindkit tree + broken `import main` + missing FastMCP/Resources/Prompts/Sampling/Alarms/Bulk coverage
- **AGENTS.md** ← §9 false "NO …" gaps; §4 pre-retrofit ref (remove after B1 delete); KEEP §9 dead-callback bullet
- **pyproject.toml** ← testpaths (post-B4) + email + urls + dev-extras + mypy
- **Makefile** ← lint root-glob + test target + native drift
- **tools/{bulk,calendars,reminders,queries,sections,groups,sampling}.py** ← B7 dedup + B8 small fix + (CL-2 typed-result + ToolAnnotations later)
- **tools/workflow.py** ← B7 `_bridge` dedup (move_reminder_blocked stale-dropped)
- **tools/__init__.py** ← B6 5→10 modules + stale docstring
- **_native/core.py** ← B6 dead callbacks + §1 CRITICAL swallow sink
- **_native/_internal.py** ← §1 CRITICAL swallow sink + pyremindkit docstring ghost
- **_native/bulk.py** ← B6 dead cancel branch + CancelledError propagation (bugfix)
- **_native/_sqlite_helpers.py / sqlite.py / models.py / lifespan.py** ← investigate/CL-2/roadmap (NOT in the 9 cleanup batches)
- **docs/MAP.md** ← B2 relocate + B5 rewrite; **TASK_STATE.md** ← B5 refresh

## 5. New-findings register (triaged; 8 high-sev all adversarially confirmed)

**fold-into-cleanup (cleanup-grade, but own batch — deferred from the 9):**
- HIGH — zero `ToolAnnotations` on 41 tools (destructive deletes look read-only to clients). Own batch (touches every tool module; conflicts with B7/B8).
- HIGH — elicitation/sampling `except AttributeError` guards are dead on mcp 1.27 (`ctx.elicit`/`create_message` are concrete; gate on `check_client_capability`, replace with `except McpError`).
- LOW — Resources/Prompts call bare `connect()` instead of lifespan `open_sqlite()`; add `ctx` + `app_context().open_sqlite()`.
- LOW — Prompts/Resources expose no `title`.
- LOW — LIKE searches don't escape `%`/`_` (add `ESCAPE '\'` at 3 sites).
- LOW — `_resolve_section_name` `json.loads` unbounded blob → masks corruption (size guard + debug log).

**CL-2-capability:**
- HIGH — typed result models for 12 bare `-> dict` tools (DeleteResult/BulkResult/MoveResult/AlarmResult/TriageResult) → FastMCP auto-emits `outputSchema`+`structuredContent`.
- HIGH — Templates create/apply/delete (`rem_reminderkit.m:1132/1192/1239`) compiled, zero Python surface.
- MEDIUM — grocery auto-categorize (`:1395`) unexposed.
- MEDIUM — `get_recently_deleted` (one inverted `ZMARKEDFORDELETION` predicate) — natural undo for `bulk_delete_completed`.
- LOW — flagged/urgent/has-subtask query filter (`ZFLAGGED` already read).
- LOW — `clear_tags` / replace semantics (tags are append-only today).

**feature-roadmap:**
- HIGH — ~13 Obj-C private-API actions stranded (smart-lists, pinning, appearance, urgent, early-reminder, templates, grocery, attachments) — ~70% of compiled surface unexposed. One epic.
- HIGH — recurrence/alarms/attachments are write-only; no read-back (model + `_REMINDER_COLS` lack fields). ADR-gated, biggest parity hole.
- MEDIUM — attachments write actions (`:1543/:1490/:1486`) unexposed; gate file paths behind kill-switch.
- LOW — no Resource for lists/groups hierarchy or tag vocabulary; no template/grocery Prompts.
- LOW — dual `Reminder` types (NamedTuple vs Pydantic) bridged by a lossy converter; collapse once SQLite is sole read path.

**investigate (real bugs, own slices):**
- 🔴 CRITICAL — EventKit write-swallow (see §1).
- HIGH — bulk false-success counts (downstream of §1).
- MEDIUM — `ZPARENTREMINDER` selected but discarded → `parent_reminder_id`/`subtasks` never populated (read-path data loss).
- MEDIUM — `model_copy(update=)` bypasses validation on frozen models in write hot-paths.
- MEDIUM — `deeplink` is a stored required field that's a pure function of `id` → should be `@computed_field` (ADR, interacts with S0.3 freeze).
- LOW — naive-local datetimes serialize offset-less (ambiguous wire contract).
- LOW — `Calendar.color` required `''` sentinel vs `owner: Optional[str]` inconsistency.
- LOW — Swift `requestAccess` `sem.wait()` has no timeout; helper-path resolution follows symlinks (benign TOCTOU).

## 6. Adversarial verdicts

All 8 high-severity NEW findings submitted to refutation skeptics; **8/8
confirmed REAL at high confidence, 0 refuted**: write-swallow, bulk
false-success, zero ToolAnnotations, 12 bare `-> dict`, dead `except
AttributeError` guards, templates unexposed, ~13 stranded actions, write-only
recurrence/alarms.
