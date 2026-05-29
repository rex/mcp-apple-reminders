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
src/mcp_apple_reminders/tools/  10 @mcp.tool modules: calendars, reminders, queries, workflow,
                                groups, alarms, bulk, sections, agents, sampling (41 tools total)
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

- **EventKit error out-params are mishandled** — `error = None` then passed to PyObjC. Actual errors never propagate; failure messages always literally say `None`.
- **Capability state (2026-05-29)**: `create_calendar` / `delete_calendar` / `update_calendar`, `set_flagged`, `set_recurrence`, `set_alarm` + `set_location_alarm`, subtasks (`create_reminder(parent_reminder_id=…)` + `get_subtasks`), tags, sections, and list-groups are all SHIPPED via the Swift EventKit + Obj-C ReminderKit helpers — the old "NO X" gaps are gone. Real remaining gaps: recurrence/alarms are write-only (no read-back in `models.py`); and smart-list create/manage, templates, grocery auto-categorize, attachments, list pinning/appearance, urgent/early-reminder, and `clear_tags` are implemented in `_native/src/rem_reminderkit.m` but NOT yet exposed as MCP tools (~70% of the Obj-C helper surface). Backlog: `docs/audits/2026-05-29-post-spec-002-cleanup-audit/` + `PROGRESS.md`.
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
