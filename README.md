# MCP Apple Reminders

A macOS-only [Model Context Protocol](https://modelcontextprotocol.io) server that
exposes Apple Reminders to Claude Code, Codex, and the Claude Desktop app. It can
create, read, update, delete, search, and organize reminders and lists, drive a
Claude-* workflow board, manage sidebar groups, set alarms and recurrence, run bulk
operations, and work with subtasks, sections, and tags.

The server is built on the MCP Python SDK (FastMCP) and reads/writes Apple Reminders
through a three-tier native stack (direct SQLite reads + a Swift EventKit helper +
an Objective-C ReminderKit helper). See [Architecture](#architecture).

## Features

- **41 MCP tools** across 10 categories (full catalog in [`docs/TOOLS.md`](docs/TOOLS.md)).
- **Calendar/list management** — create, delete, update, search lists.
- **Reminder CRUD** — create, update, complete/uncomplete, delete, fetch by ID.
- **Rich queries** — today, overdue, next-up, completed-in-range, text search, filters.
- **Workflow board** — move reminders across Pierce's `Claude-*` lists.
- **Sidebar groups** — create/list/delete folders and move lists into them.
- **Alarms & recurrence** — time alarms, location alarms, repeat rules.
- **Bulk operations** — complete, move, and purge-completed in one call.
- **Subtasks, sections & tags** — hierarchy and grouping via the ReminderKit helper.
- **MCP Resources, Prompts, Elicitation, Sampling, and progress reporting** (see below).
- **Deeplinks** — every Reminder and Calendar carries an `x-apple-reminderkit://` deeplink.

## Requirements

- **OS**: macOS (EventKit-backed; macOS owns iCloud sync). No cross-platform support.
- **Python**: 3.10+ (the repo venv runs 3.13).
- **Xcode Command Line Tools**: `swiftc` + `clang`, required once to compile the native helpers.
- **Permission**: Reminders access, granted **per interpreter binary** (see [Permissions](#permissions)).
- **MCP client**: Claude Code, Codex, the Claude Desktop app, or any MCP-compatible client.

Key dependencies: MCP Python SDK `1.27.x` (FastMCP), Pydantic v2, and PyObjC/EventKit.

## Installation

### Recommended: `install.sh`

From the repo root:

```bash
./install.sh
```

This creates `./venv`, installs the package in editable mode with its dependencies,
and compiles the native helpers (`make build-native`).

### Manual

```bash
python3 -m venv venv
source venv/bin/activate
pip install -e ".[dev]"
make build-native           # compiles the Swift + Obj-C helpers into _native/bin/
```

### Verify the install

```bash
./venv/bin/python3 -c "from mcp_apple_reminders import cli_main; print('ok')"
./venv/bin/python3 verify_setup.py     # preflight: interpreter, deps, perms, client configs
```

`verify_setup.py` triggers the macOS Reminders permission prompt on first run. Approve it.

## Configuration

In every client, the launch command **must** be this repo's venv interpreter
(the binary that was granted Reminders access — see [Permissions](#permissions)),
not a bare `python3`. On many macOS systems `/usr/bin/python3` is too old anyway.

Replace `/absolute/path/to/mcp-apple-reminders` with your local checkout in each snippet.

### Claude Code

```bash
claude mcp add apple-reminders \
  /absolute/path/to/mcp-apple-reminders/venv/bin/python3 -- -m mcp_apple_reminders
```

### Codex

Codex reads MCP servers from `~/.codex/config.toml`:

```toml
[mcp_servers.apple-reminders]
command = "/absolute/path/to/mcp-apple-reminders/venv/bin/python3"
args = ["-m", "mcp_apple_reminders"]
cwd = "/absolute/path/to/mcp-apple-reminders"
enabled = true
```

### Claude Desktop app

Edit `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "apple-reminders": {
      "command": "/absolute/path/to/mcp-apple-reminders/venv/bin/python3",
      "args": ["-m", "mcp_apple_reminders"],
      "env": {}
    }
  }
}
```

Restart Claude Desktop, then look for the tools under "apple-reminders".

### First-run permission shim

If the Reminders permission prompt never appears, point the client's `command` at
`./shim_mcp.sh` (args `[]`) once to surface the prompt, then switch back to the venv
interpreter above.

### Other clients

The server speaks MCP over stdio. The general invocation is:

```bash
/absolute/path/to/mcp-apple-reminders/venv/bin/python3 -m mcp_apple_reminders
```

## Permissions

Apple Reminders access is granted **per binary**, so the exact interpreter the client
launches (the conda/venv `python3`) must be the one that holds the grant.

1. On first launch macOS shows a permission dialog — click **OK**.
2. If you miss it, run `./venv/bin/python3 verify_setup.py` (or `./shim_mcp.sh`) once and approve.
3. To inspect/toggle manually: **System Settings → Privacy & Security → Reminders**.

Without the grant the server cannot read or write reminders.

## Tools, Resources & Prompts

The 41 tools are grouped into 10 modules under `src/mcp_apple_reminders/tools/`.
The exhaustive, always-current catalog (parameters + return shapes) lives in
[`docs/TOOLS.md`](docs/TOOLS.md). Summary by category:

| Category | Count | What it does |
|---|---|---|
| **calendars** | 8 | create/delete/update lists, get by name/ID, default, list, search |
| **reminders** | 6 | create, update, delete, complete, uncomplete, get by ID |
| **queries** | 6 | get/filter, today, overdue, next-up, completed-in-range, search |
| **workflow** | 6 | move across `Claude-*` board lists; list the board |
| **groups** | 4 | create/list/delete sidebar folders; move a list into a group |
| **alarms** | 3 | time alarm, location alarm, recurrence rule |
| **bulk** | 3 | bulk complete, bulk move, bulk delete-completed |
| **sections** | 3 | get subtasks, set parent, assign section |
| **agents** | 1 | `bootstrap_agent_list` — agent-visibility plane |
| **sampling** | 1 | `triage_brain_dump` — server-initiated LLM sampling |

The **workflow board** is Pierce's `Claude-*` list family: `Claude-Brain-Dump`,
`Claude-On-Deck`, `Claude-Active`, `Claude-Waiting`, and `Claude-Done`. **Groups** are
Reminders.app sidebar folders.

Beyond tools, the server also exposes:

- **MCP Resources** (read-only views): `reminders://default`, `reminders://today`,
  `reminders://overdue`, `reminders://list/{calendar_id}`, and
  `agents://current/{project_name}` (the agent-visibility plane).
- **MCP Prompts**: `daily_review`, `weekly_retro`, `brain_dump_triage`, `agent_visibility_sync`.
- **Elicitation guards** on destructive operations (e.g. deletes/purges).
- **Server-initiated Sampling** via `triage_brain_dump`.
- **Progress reporting** on long-running operations.

## Usage examples

Once configured, ask your client in natural language — it picks the tools:

- "Show me everything due today." → `get_today_reminders`
- "Remind me to call the dentist tomorrow at 2pm." → `create_reminder`
- "What am I behind on?" → `get_overdue_reminders`
- "Move the 'update docs' task to Active." → `move_reminder_active`
- "Triage my brain dump." → `triage_brain_dump` (with elicitation/sampling)

## Architecture

`server.py` is the FastMCP instance; importing the `tools`, `resources`, and `prompts`
packages registers everything against it. `lifespan.py` builds the `AppContext`
(SQLite store path + helper binary paths); `models.py` holds frozen Pydantic v2 models,
each Reminder/Calendar carrying a `deeplink` (e.g. `x-apple-reminderkit://REMCDReminder/{uuid}`).

All native access lives under `src/mcp_apple_reminders/_native/` in three tiers:

1. **SQLite reads** (`sqlite.py`) — reads the Reminders.app CoreData SQLite store
   directly. Fast path for reads, including sections, subtasks, tags, and groups.
2. **EventKit writes** (`eventkit.py`) — Python wrapper around a compiled Swift
   EventKit helper subprocess for public-API writes. Binary `_native/bin/rem_eventkit`,
   compiled from `_native/src/rem_eventkit.swift`.
3. **ReminderKit writes** (`reminderkit.py` transport + `reminderkit_actions.py` typed
   wrappers) — Python wrapper around a compiled Objective-C ReminderKit (a **private**
   framework) helper subprocess for subtasks, tags, sections, flagged state, and groups.
   Binary `_native/bin/rem_reminderkit`, compiled from `_native/src/rem_reminderkit.m`.

Both native helpers are borrowed from [viticci/remctl](https://github.com/viticci/remctl)
(MIT); see [`src/mcp_apple_reminders/_native/THIRD_PARTY_NOTICES.md`](src/mcp_apple_reminders/_native/THIRD_PARTY_NOTICES.md).

```
Client (Claude Code / Codex / Claude Desktop)
    | MCP over stdio (JSON-RPC)
server.py  (FastMCP: tools + resources + prompts)
    | lifespan AppContext (sqlite path, helper paths)
_native/  ── sqlite.py ........... direct CoreData SQLite reads
           ├ eventkit.py ........ Swift helper subprocess  (public-API writes)
           └ reminderkit.py ..... Obj-C helper subprocess  (private-framework writes)
    |
Apple Reminders store
```

**No stdout, ever.** stdio *is* the JSON-RPC transport; any stray `print` corrupts the
protocol. All logs go to stderr only.

## Development

```bash
# Lint, format-check, line-limit gate
ruff check src/ test_*.py test_support/
black --check src/ test_*.py test_support/
make check-architecture            # hard cap 400 lines/file

# Tests (root-level, explicit paths — root is not on testpaths)
./venv/bin/python -m pytest test_mcp_tools.py test_workflow_tools.py test_e2e.py

# Rebuild native helpers after editing the Swift/Obj-C sources
make build-native                  # or: make clean-native && make build-native
```

Run the server directly for debugging (logs to stderr):

```bash
./venv/bin/python3 -m mcp_apple_reminders
```

The installed console script `mcp-apple-reminders` maps to `mcp_apple_reminders:cli_main`.

## Troubleshooting

- **"No access to reminders"** — the grant is per binary. Confirm the client launches
  the venv interpreter and that *that* binary is enabled under System Settings →
  Privacy & Security → Reminders. Re-run `verify_setup.py` or `./shim_mcp.sh` to re-prompt.
- **Tools missing in the client** — verify the config path and JSON/TOML syntax, confirm
  the interpreter path is absolute, and fully restart the client.
- **`ModuleNotFoundError`** — reinstall: `pip install -e ".[dev]"`.
- **Native helper missing / write failures** — run `make build-native` (needs Xcode CLI
  tools). Check `_native/bin/rem_eventkit` and `_native/bin/rem_reminderkit` exist.
- **DateTime errors** — use ISO 8601, e.g. `2026-01-15T14:30:00`.
- **Reminder not found** — the ID may be stale; re-fetch via `search_reminders` / `get_reminders`.

Client logs (Claude Desktop): `tail -f ~/Library/Logs/Claude/mcp*.log`.

## Further docs

- [`docs/TOOLS.md`](docs/TOOLS.md) — full tool catalog.
- [`docs/MAP.md`](docs/MAP.md) — module map.
- [`docs/SQLITE_SCHEMA.md`](docs/SQLITE_SCHEMA.md) — Reminders SQLite schema notes.
- [`docs/SECURITY-REVIEW.md`](docs/SECURITY-REVIEW.md) — security review.
- [`AGENTS.md`](AGENTS.md) — agent collaboration guide.
- [`CHANGELOG.md`](CHANGELOG.md) — release history.

## License

MIT. See [LICENSE](LICENSE). Native helpers are MIT-licensed third-party code — see
[`src/mcp_apple_reminders/_native/THIRD_PARTY_NOTICES.md`](src/mcp_apple_reminders/_native/THIRD_PARTY_NOTICES.md).
