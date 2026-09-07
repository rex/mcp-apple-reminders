# Conventions

## Style

- Black, line-length 120. Ruff `select=["E","F","I","N","W","B","C4","PT","SIM","TCH"]`, ignore `E501`.
- Type hints on all public functions. `from __future__ import annotations` for forward refs.
- Module docstring required on every source file (purpose, responsibilities, side effects).
- Function/method docstrings required on non-trivial functions (purpose, params, returns, raises).

## File-size policy

- Hard cap 400 lines/file, soft 250 (`VIBE.yaml::architecture.max_lines_per_file`).
- Opt-OUT gate: every source file is scanned by default. The only exclusions are `**/*.generated.*` and `**/node_modules/**`. No grandfather globs exist — new files must comply.
- If a file is genuinely over the hard limit, the answer is split-by-responsibility, not exclude. See how `server.py` (961) → 7 files and `core.py` (504) → 4 files were handled.

## MCP protocol safety (non-negotiable)

- Server speaks JSON-RPC over stdio. `print()` to stdout is forbidden — corrupts the protocol.
- Diagnostic output: `print(..., file=sys.stderr)`.
- `shim_mcp.sh` may emit `osascript` output to stderr (intentional, see header comment).

## Path conventions

- Never hardcode `/Users/<name>/...`. Use `Path(__file__).resolve().parent.parent.parent`-style relative resolution.
- Repo venv at `./venv/bin/python3` — prefer over bare `python3` (system Python may be < 3.10).

## Versioning

- VERSION file at root, semver. `bump_required_per_commit: true` enforces a bump per commit.
- `pyproject.toml` has its own version (0.1.0) currently NOT synced with VERSION. Sync is a known TODO.
- Signed commits required (`git commit -S`).

## Tool naming (MCP)

- Tool names are snake_case, action-first: `create_reminder`, `get_today_reminders`, `move_reminder_to_list`.
- Convenience wrappers around `move_reminder_to_list` follow `move_reminder_<state>` pattern: `move_reminder_on_deck`, `move_reminder_active`, `move_reminder_done`, `move_reminder_blocked`.
- `get_workflow_lists` returns calendars matching `Claude-*` prefix — a hardcoded convention used by Pierce's pre-existing ADHD task system. New agent-collaboration lists use `Agents-<project>` prefix instead (per visibility-protocol design, May 2026).

## Tool / handler module layout (in `src/mcp_apple_reminders/tools/`)

- Each `tools/<category>.py` exports two module-level symbols:
  - `TOOLS: list[Tool]` — the MCP `Tool` schemas (name, description, inputSchema)
  - `HANDLERS: dict[str, Callable]` — name → handler function, signature `(arguments: dict, remind: RemindKit) -> list[TextContent]`
- `tools/__init__.py` aggregates them into `ALL_TOOLS` and `ALL_HANDLERS`. Add new categories by adding a module and a one-line update to `__init__.py`.
- Handlers raise `ValueError` for user-input errors (rendered as `Error: ...` to the client) or other exceptions for runtime errors (rendered as `Error executing <name>: ...`). The wrapping try/except is centralized in `server.py::call_tool`; do not duplicate it inside handlers.

## Vendored dependency

- `libs/pyremindkit/` is a vendored EventKit wrapper. Treated as an integrated local dep, not a third-party package.
- Public surface re-exported from `pyremindkit/__init__.py`: `RemindKit, Reminder, Priority, Calendar, CalendarManager`. Submodule imports are internal — do not reach into `_internal`, `calendars`, `models` from outside the package.
- Server code MAY modify `pyremindkit` deliberately. Document coupling between server logic and library quirks in code comments.
- Do NOT pip-install pyremindkit separately; the `sys.path` insertion in `server.py` is intentional.
