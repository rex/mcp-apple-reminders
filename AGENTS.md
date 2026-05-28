# AGENTS.md

## 1. Project snapshot

- **What**: macOS-only MCP server exposing Apple Reminders (EventKit) to Claude Code, Codex, and Claude Desktop.
- **Runtime**: Python 3.10+ (repo venv runs 3.13.5 from miniconda). MCP SDK + PyObjC EventKit. Vendored `pyremindkit` in `libs/`.
- **Platform**: macOS only — depends on `EventKit` and a granted Reminders permission on the interpreter binary.
- **Owner**: @pierce (single-author repo as of 2026-05).
- **Non-goals**: cross-platform support, reminder UI (use Reminders.app), iCloud sync logic (macOS handles it).

## 2. Setup

```bash
./install.sh                          # creates ./venv, installs editable pkg + deps
./venv/bin/python3 verify_setup.py    # preflight: interpreter, deps, perms, client configs
```

Grant Reminders permission on first launch — approve the macOS dialog when `verify_setup.py` runs, OR run `./shim_mcp.sh` once and approve. Permission is per-binary; the conda Python interpreter must be the one approved.

## 3. Commands the agent MUST run before declaring done

- `ruff check src/ libs/pyremindkit/src/`
- `black --check src/ libs/pyremindkit/src/`
- `./venv/bin/python -m pytest test_mcp_tools.py test_workflow_tools.py test_e2e.py` — root-level tests, explicit paths (no auto-discovery)
- `make check-architecture` (line-limit gate: hard cap 400 lines/file)
- `make bump-patch` (or minor/major) before commit — `bump_required_per_commit: true`

## 4. Repo layout

```
src/mcp_apple_reminders/        MCP server orchestrator (server.py) + formatting helpers
src/mcp_apple_reminders/tools/  Per-category tool defs (calendars, reminders, queries, workflow)
libs/pyremindkit/               Vendored EventKit wrapper
libs/pyremindkit/src/pyremindkit/  core (RemindKit), calendars (Calendar + Manager), models, _internal
scripts/                        Gate scripts (bump_version, check_architecture, check_module_rules, …)
test_*.py                       Per-domain test files at repo root (orchestrators + per-domain modules)
test_support/                   Shared test scaffolding (TestResults harness, cleanup)
verify_setup.py                 Install + permission + client-config verification
install.sh, shim_mcp.sh         Bootstrap + first-run permission-prompt shim
AGENTS.md.pre-retrofit          Original 205-line guide (preserved for reference)
```

## 5. Code style

- 120-line column (`pyproject.toml`).
- Type hints throughout; prefer `from __future__ import annotations` for forward refs.
- Module docstrings mandatory on every source file; function docstrings on non-trivial functions.

## 6. Testing policy

- `deferred` (see VIBE.yaml). Tests exist at root (`test_*.py`) and must run with explicit paths — root is not on `testpaths`.

## 7. Security (hard stops)

- **Never write to stdout from the MCP server.** stdio IS the JSON-RPC transport; any stray print corrupts the protocol. Logs go to stderr only.
- No personal absolute paths (`/Users/<name>/...`) — use `Path(__file__).resolve()`.
- macOS Reminders permission is privileged — do not chain shell calls that escalate access without the user's knowledge.

## 8. Architectural decisions

- Decision log: `VIBE.yaml::project.decisions` (append-only).

## 9. Things agents get wrong here

- **`Calendar.is_default` is buggy** — `libs/pyremindkit/src/pyremindkit/calendars.py::CalendarManager.list()` uses `EKCalendar.isImmutable()` as the proxy. That's wrong; `isImmutable` means "user can't modify," not "is the default list." Should compare against `event_store.defaultCalendarForNewReminders()`. Every list currently reports `Default: No`.
- **Dead callbacks**: pyremindkit's `on_reminder_created` / `on_reminder_completed` register but never fire. Don't rely on them.
- **EventKit error out-params are mishandled** — `error = None` then passed to PyObjC. Actual errors never propagate; failure messages always literally say `None`.
- **Significant capability gaps from EventKit**: NO `create_calendar` / `delete_calendar` / `update_calendar`, NO `flagged` setter, NO recurrence rules, NO alarms (time- or location-based), NO subtasks. P0–P3 roadmap in `PROGRESS.md` (after PR4).
- **Architecture gate is opt-OUT**: every source file is scanned by default. Hard cap 400 lines, soft 250. The 4 pre-retrofit oversized files (`server.py`, `core.py`, two test files) were split — do NOT add new files that bust the cap on the assumption a grandfather glob will catch them. There are no grandfather globs.

## 10. Workflow

1. Read this file.
2. Check `MAP.md` (after PR2) for the module you're touching.
3. If `.mcp.json` declares `serena` (after PR3): `mcp__serena__activate_project` first, then `onboarding` on a fresh project else `list_memories`. Use Serena's symbolic tools (`find_symbol`, `replace_symbol_body`, `search_for_pattern`) over `Read`/`Edit`/`Grep`. Full protocol: `.claude/rules/serena.md` (after PR5).
4. Run §3 commands before declaring done. Bump VERSION before commit.

## 11. When ending a session

- Update `TASK_STATE.md` §6 Handoff (after PR4) if work continues.
- Promote durable new facts into AGENTS.md §9 — don't accumulate tribal knowledge in Serena auto-memory.

## 12. Subdirectory AGENTS.md (precedence: nearest wins)

- `libs/pyremindkit/` is treated as a vendored dep; may gain its own AGENTS.md if it diverges into independent work.
