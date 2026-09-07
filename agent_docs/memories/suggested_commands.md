# Suggested Commands

## Setup

- `./install.sh` — fresh venv + editable install.
- `./venv/bin/python3 verify_setup.py` — full preflight (interpreter, deps, perms, client configs).
- `./shim_mcp.sh` — first-launch shim that surfaces macOS Reminders permission prompt via `osascript` before starting the MCP server. Use once per interpreter binary.

## Validate / before commit

- `make check-architecture` — line-limit gate + module-shape gate. Currently grandfathered for 4 oversized files (see `VIBE.yaml::architecture.exclude_globs`).
- `ruff check src/ libs/pyremindkit/src/` — linter (Makefile stub fails closed until lang-mcp overlay).
- `black --check src/ libs/pyremindkit/src/` — formatter check.
- `make bump-patch` (or `bump-minor` / `bump-major`) — bump VERSION before each commit (`bump_required_per_commit: true`).
- `git commit -S` — signed commit required.

## Tests (deferred; run explicitly)

- `./venv/bin/python -m pytest test_mcp_tools.py test_workflow_tools.py test_e2e.py` — root-level tests, explicit paths.
- `./venv/bin/python -m pytest test_comprehensive_crud.py` — full CRUD suite (slow).

## MCP runtime

- `./venv/bin/python3 -m mcp_apple_reminders` — start the MCP server on stdio.
- Client configs:
  - Codex: `~/.codex/config.toml`
  - Claude Desktop: `~/Library/Application\ Support/Claude/claude_desktop_config.json`
  - Claude Code (user-level): `~/.claude.json::mcpServers`

## Darwin-specific commands

- `sqlite3 ~/Library/Application\ Support/com.apple.TCC/TCC.db "SELECT client, auth_value FROM access WHERE service='kTCCServiceReminders'"` — inspect TCC grants (auth_value=2 means allowed).
- `osascript -e 'tell application "Reminders" to ...'` — trigger AppleScript bridge.
- `tccutil reset Reminders <bundle-id>` — reset permission grants per app.

## Make targets (skeleton-provided)

- `make help` — list all targets with colored output.
- `make help-stack` — shows the lang-* skill that owns stub recipe bodies (lang-mcp for this stack).
- `make check-if-the-agent-can-consider-this-task-completed` — full completion gate (lint + typecheck + architecture + version + docs + precommit + tests).
