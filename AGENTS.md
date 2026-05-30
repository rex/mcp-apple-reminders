# AGENTS.md

## 1. Project snapshot

- **What**: macOS-only MCP server exposing Apple Reminders (EventKit + private ReminderKit) to Claude Code, Codex, and Claude Desktop.
- **Runtime**: Python 3.10+ (repo venv runs 3.13.5 from miniconda). MCP SDK 1.27+ (FastMCP) + PyObjC. Three-tier native layer at `src/mcp_apple_reminders/_native/` (renamed from `libs/pyremindkit/` in slice 0.2).
- **Platform**: macOS only — depends on `EventKit` / `ReminderKit` and a granted Reminders permission on the interpreter binary.
- **Owner**: @pierce (single-author repo as of 2026-05).
- **Non-goals**: cross-platform support, reminder UI (use Reminders.app), iCloud sync logic (macOS handles it).

## 2. Setup

```bash
./install.sh                          # creates ./venv, installs editable pkg + deps, builds native helpers
./venv/bin/python3 verify_setup.py    # preflight: interpreter, deps, perms, client configs
```

Grant Reminders permission on first launch — approve the macOS dialog when `verify_setup.py` runs, OR run `./shim_mcp.sh` once and approve. Permission is per-binary; the conda Python interpreter must be the one approved.

## 3. Commands the agent MUST run before declaring done

- `ruff check src/ tests/`
- `black --check src/ tests/`
- `./venv/bin/python -m pytest tests/test_mcp_tools.py tests/test_workflow_tools.py tests/test_e2e.py` — explicit paths (or `make test-actual`)
- `make check-architecture` (line-limit gate: hard cap 400 lines/file)
- `make bump-patch` (or minor/major) before commit — `bump_required_per_commit: true`

## 4. Repo layout

```
src/mcp_apple_reminders/        FastMCP server (server.py) + lifespan.py + models.py + formatting.py
src/mcp_apple_reminders/tools/  17 @mcp.tool modules: calendars, reminders, completion, queries,
                                workflow, groups, alarms, bulk, sections, smartlists, appearance,
                                templates, flags, attachments, grocery, agents, sampling (58 tools)
src/mcp_apple_reminders/resources/  @mcp.resource SQLite views (e.g. agents://current/{project})
src/mcp_apple_reminders/prompts/    @mcp.prompt canned workflows
src/mcp_apple_reminders/_native/    Three-tier native layer: sqlite.py (+ _sqlite_helpers) = reads;
                                eventkit.py = Swift EventKit helper; reminderkit.py +
                                reminderkit_actions.py = Obj-C ReminderKit (private) helper;
                                legacy PyObjC wrapper (core, _internal, calendars, models); bulk.py
src/mcp_apple_reminders/_native/bin/  Compiled rem_eventkit + rem_reminderkit (from _native/src/
                                *.swift / *.m; build with `make build-native`)
scripts/                        Gate scripts (bump_version, check_architecture, check_module_rules, …)
tests/                          Test suite (test_*.py) + tests/_support/ (TestResults harness, cleanup)
docs/                           MAP.md, TOOLS.md, SQLITE_SCHEMA.md, SECURITY-REVIEW.md, adr/, audits/
verify_setup.py                 Install + permission + client-config verification
install.sh, shim_mcp.sh         Bootstrap + first-run permission-prompt shim
```

## 5. Code style

- 120-line column (`pyproject.toml`).
- Type hints throughout; prefer `from __future__ import annotations` for forward refs.
- Module docstrings mandatory on every source file; function docstrings on non-trivial functions.

## 6. Testing policy

- `deferred` (see VIBE.yaml). Tests live in `tests/` (`testpaths = ["tests"]`); run the §3 explicit suites or `make test-actual`. Shared scaffolding in `tests/_support/`. The workflow suite (`tests/test_workflow_tools.py`) is a script orchestrator (`__test__ = False`) — run it with `python tests/test_workflow_tools.py`.

## 7. Security (hard stops)

- **Never write to stdout from the MCP server.** stdio IS the JSON-RPC transport; any stray print corrupts the protocol. Logs go to stderr only.
- No personal absolute paths (`/Users/<name>/...`) — use `Path(__file__).resolve()`.
- macOS Reminders permission is privileged — do not chain shell calls that escalate access without the user's knowledge.

## 8. Architectural decisions

- Decision log: `VIBE.yaml::project.decisions` (append-only). ADRs in `docs/adr/`.

## 9. Things agents get wrong here

- **EventKit write errors propagate (since the CL-1 fix)** — the commit sinks (`_internal.py::_save_ek_reminder`, `core.py::delete_reminder`) unpack PyObjC's `(ok, NSError)` out-param tuple and raise `RuntimeError(localizedDescription())` on failure. Do NOT reintroduce the `error = None; success = store.save..._error_(...)` pattern — it captures the whole always-truthy tuple into `success`, making the failure branch dead and silently swallowing every write failure.
- **Capability state (2026-05-30, v0.1.84)**: CL-2.1–2.13 shipped — smart lists, list/group appearance+pinning, templates, grocery, urgent/early-reminder/sections, attachments (generic files via `addFileAttachmentWithURL:`, local-file tool opt-in behind env `MCP_APPLE_REMINDERS_ENABLE_FILE_ATTACHMENTS`), read-side (recently-deleted + `flagged` filter + parent/subtask population), `clear_tags`, and recurrence/alarm/early-reminder **read-back** (ADR 0002). **58 tools, 8 resources (6 static + 2 templates), 5 prompts, 2 ADRs.** The old "recurrence/alarms write-only" gap is CLOSED. CL-2.10 ToolAnnotations (shared READ/CREATE/MUTATE/DESTROY presets + titles, `tools/_annotations.py`), CL-2.11 typed result models (`results.py` — WriteResult/DeleteResult/BulkResult/TriageResult; `extra="allow"` envelopes + `_Result.of()` factory), and CL-2.12 resources/prompts polish (titles + `organize_into_sections` + per-param `Field(description=)`; `complete`/`uncomplete` split into `tools/completion.py`) all SHIPPED. CL-2 is COMPLETE.
- **Wire-level integration suite (`tests/integration/`, run `./venv/bin/python -m tests.integration.run $(date +%H%M%S)`)** — **165 checks** against the LIVE store via a fresh stdio server; NOT in the unit gate (needs Reminders permission), self-cleans an `MCP-IntegTest` group/list. This is the ONLY layer that catches native-helper crashes + structured-output/datetime wire bugs (unit tests mock the helper). It surfaced **two real bugs**, both encoded as self-flipping expected-error known-issues with fix tasks queued: (1) `set_urgent` crashes the helper (`-[REMReminderStorage urgentAlarmContext]: unrecognized selector`, uncaught NSException); (2) `create_smart_list` without `filter_data_b64` errors "filterData is required" (contradicts its docs). SQLite read-after-write lag on hashtag/subtask/section rows is real — the suite polls, don't assert once.
- **Reminder datetimes MUST serialize offset-bearing (RFC 3339)** — naive-local datetimes serialize to offset-less ISO (`2026-06-19T04:00:00`), which fails the JSON-Schema `date-time` format check MCP structured-output enforces → every Reminder-returning tool errors `-32602` *over the wire* (the EventKit write still succeeds; unit tests miss it because they bypass wire validation). `models.py::Reminder._serialize_local_datetime` (a `field_serializer`, `when_used="json"`) stamps the local offset. Do NOT remove it or emit/store naive datetimes. (Fixed v0.1.77.)
- **Destructive-tool elicitation guards must be broad** — `delete_calendar` / `bulk_delete_completed` guard `ctx.elicit` with a broad `except Exception` (degrade-and-proceed), NOT `except AttributeError` only: a client that exposes `ctx.elicit` but doesn't advertise elicitation capability raises a non-AttributeError ("Elicitation not supported") and the op fails even with force=true. `delete_calendar` now treats `force=true` AS the confirmation (no elicitation). (Fixed v0.1.78.)
- **Recurrence + alarms are NOT in the SQLite store** — there is no `ZREMCDRECURRENCERULE` / `ZREMCDALARM` table or column; they live only in the opaque `ZCKSERVERRECORDDATA` CloudKit blob (NSKeyedArchiver). Read-back is EventKit summaries (`_native/eventkit_readback.py`), populated only in `get_reminder(id)` (ADR 0002). Early-reminders ARE in SQLite (`ZDUEDATEDELTAALERTSDATA`, JSON). `urgent` + the "when messaging <person>" trigger are CloudKit-blob-only = unreadable (dropped from read-back). Do NOT re-attempt a SQLite recurrence/alarm read.
- **The CONNECTED MCP server can run stale code** — after you edit source, the in-session apple-reminders server keeps the OLD code until restarted (Inspector restart / `/mcp` reconnect; it runs the editable `venv/bin/python -m mcp_apple_reminders`). To wire-test current code regardless, drive a FRESH server via `mcp.client.stdio.stdio_client` + `ClientSession` (proven this session). To delete a test list+group, call the helpers directly — `_native.eventkit.delete_calendar(name)` cascades, then `_native.reminderkit_actions.delete_group(id)` — which bypasses the elicitation layer.
- **Do NOT `make sync-skeleton` the hooks** — agentic-skeleton v0.37.0's `.claude/hooks/{auto-commit,changelog-append,stop-gate}.sh` dropped `cd … || exit 1`, which trips shellcheck SC2164 (a pre-commit gate) and is less safe. The repo's hooks are intentionally ahead; `check-skeleton` will keep flagging this drift on those 3 files — that's expected, not actionable here (the fix belongs upstream in the skeleton).
- **Architecture gate is opt-OUT**: every source file is scanned by default. Hard cap 400 lines, soft 250. The 4 pre-retrofit oversized files (`server.py`, `core.py`, two test files) were split — do NOT add new files that bust the cap on the assumption a grandfather glob will catch them. There are no grandfather globs.

## 10. Workflow

1. Read this file.
2. Check `docs/MAP.md` for the module you're touching.
3. If `.mcp.json` declares `serena` (after PR3): `mcp__serena__activate_project` first, then `onboarding` on a fresh project else `list_memories`. Use Serena's symbolic tools (`find_symbol`, `replace_symbol_body`, `search_for_pattern`) over `Read`/`Edit`/`Grep`. Full protocol: `.claude/rules/serena.md` (after PR5).
4. **Visibility-plane (post-S4.1)**: at session start, agents that share state with the human SHOULD call `bootstrap_agent_list(project_name="<this-project>")` to ensure the `Agents-<project>` Reminders list exists, then mirror their in-flight todos into it with `create_reminder` / `update_reminder` / `complete_reminder` / `delete_reminder`. The human pulls the live state via the `agents://current/{project_name}` Resource (or just opens Reminders.app).
5. Run §3 commands before declaring done. Bump VERSION before commit.

## 11. When ending a session

- Update `TASK_STATE.md` §6 Handoff (after PR4) if work continues.
- Promote durable new facts into AGENTS.md §9 — don't accumulate tribal knowledge in Serena auto-memory.

## 12. Subdirectory AGENTS.md (precedence: nearest wins)

- `src/mcp_apple_reminders/_native/` houses the three-tier native layer (formerly vendored as `libs/pyremindkit/`; renamed in S0.2).
