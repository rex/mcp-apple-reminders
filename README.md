<div align="center">

<img src="images/logo.png" alt="mcp-apple-reminders" width="160" />

# mcp-apple-reminders

**Conversational ADHD task management for Claude — an MCP server for Apple Reminders.**

[![CI](https://github.com/rex/mcp-apple-reminders/actions/workflows/ci.yml/badge.svg)](https://github.com/rex/mcp-apple-reminders/actions/workflows/ci.yml)
[![PyPI version](https://img.shields.io/pypi/v/mcp-apple-reminders.svg)](https://pypi.org/project/mcp-apple-reminders/)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![macOS only](https://img.shields.io/badge/platform-macOS-lightgrey.svg)](https://www.apple.com/macos/)
[![MCP](https://img.shields.io/badge/MCP-compatible-purple.svg)](https://modelcontextprotocol.io)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

</div>

---

## Why this exists

I have ADHD and a lot of stale reminders. Apple Reminders is a fine database;
the bottleneck is the human in front of it. So I gave Claude a key.

This server turns Apple Reminders into something you talk *to*: triage an
inbox of 200 items in five minutes, plan your day in three sentences, snooze
the things that are stressing you out without losing them, and run a weekly
review that actually happens because it's a chat, not a ritual.

It's a Model Context Protocol server, so it works with **Claude Desktop,
Codex, Cursor, Cline, Continue, Zed, Windsurf** — any MCP-compatible client
on macOS.

> **Status:** v0.2.0 first public release. Stable for daily use; see the
> [roadmap](#roadmap) for what's next.

## What you can ask for

```
You> Plan my day.
Claude> You have 4 overdue and 7 due today. Top 3 to tackle:
        1. Call dentist — overdue by 2 days, takes 5 min
        2. Submit Q3 expense report — due tomorrow, blocking finance
        3. Review draft PR — small, finishes the chain on the Stripe migration
        Move these to Active? [Y/n]

You> Triage my inbox.
Claude> 23 orphan items in your default list. Grouped by suggested action:
        → On-Deck (8): things you flagged but haven't started
        → Blocked (3): waiting on Sarah, Mike, the IRS
        → Delete (5): "buy oat milk" from 6 months ago — already bought twice
        → Rename (2): "fix the thing" — what thing? add context?
        Walk through these in batches?

You> Snooze 'gym' until next Monday.
Claude> Done. Pushed 'Renew gym membership' to 2025-11-10T09:00.

You> Capture: book flight, return library books, follow up with Eric, mom's birthday gift
Claude> Captured 4 to inbox. Suggesting: 'follow up with Eric' → On-Deck (active
        thread), 'mom's birthday gift' → On-Deck with due date 2 weeks before,
        rest stay in inbox. Apply?
```

Each of those is one of six prompts shipped with the server. You can also
use the 28 underlying tools directly.

## Quickstart

### Install

```bash
brew install uv  # if you don't already have it
```

That's it on the user side — `uvx` will fetch the package on demand.

### Configure your MCP client

<details open>
<summary><b>Claude Desktop</b></summary>

Edit `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "apple-reminders": {
      "command": "uvx",
      "args": ["mcp-apple-reminders"]
    }
  }
}
```

Restart Claude Desktop.
</details>

<details>
<summary><b>Codex</b></summary>

Edit `~/.codex/config.toml`:

```toml
[mcp_servers.apple-reminders]
command = "uvx"
args = ["mcp-apple-reminders"]
enabled = true
```
</details>

<details>
<summary><b>Cursor / Cline / Continue / Zed / Windsurf</b></summary>

Same `command: uvx`, `args: ["mcp-apple-reminders"]` shape — see your
client's MCP server docs for the exact config-file location.
</details>

### Grant Reminders permission

On first launch macOS prompts for Reminders access. Click **OK**. If you
miss it, System Settings → Privacy & Security → Reminders → enable your
interpreter or terminal.

If your MCP client suppresses the prompt, point it at `shim_mcp.sh` once
to surface it, then switch back to the regular config.

## Tools, resources, and prompts

The server exposes three MCP capabilities:

### Prompts (the headline feature)

| Prompt | What it does |
|---|---|
| `plan_my_day` | Triages overdue + today, recommends 3 to make Active |
| `triage_inbox` | Sorts orphan reminders into On-Deck / Blocked / delete / rename |
| `weekly_review` | Summarizes Done, surfaces stale Active, unblocks Blocked |
| `quick_capture` | Parses a brain-dump into reminders with smart list assignment |
| `defer_to_someday` | Pushes items to a "someday" bucket without losing them |
| `snooze` | Pushes a single reminder's due date forward |

### Tools (28 of them)

Calendar / list management, reminder CRUD, queries (overdue, today, next),
the Claude-* kanban workflow (`move_reminder_on_deck`, `move_reminder_active`,
`move_reminder_done`, `move_reminder_blocked`), batch operations, flagged-state
toggling. Full reference: **[docs/tools.md](docs/tools.md)**.

### Resources

| URI | What it returns |
|---|---|
| `apple-reminders://lists` | All reminder lists |
| `apple-reminders://list/{id}` | One list and its open reminders |
| `apple-reminders://reminder/{id}` | One reminder by ID |

Resources let agents browse without spending tool turns.

## The kanban convention

Workflows assume four lists named (by default) `Claude-On-Deck`,
`Claude-Active`, `Claude-Done`, `Claude-Blocked`. Create them once in Apple
Reminders. Override the prefix:

```bash
export MCP_APPLE_REMINDERS_LIST_PREFIX="Work/"
```

The `triage_inbox` and `plan_my_day` prompts both encourage keeping fewer
than ~3 items in Active at a time. Anything else is in On-Deck (queued)
or Blocked (waiting on someone).

## Client compatibility

| Client | Status | Notes |
|---|---|---|
| Claude Desktop | ✅ Tested | Primary target |
| Codex | ✅ Tested | `~/.codex/config.toml` |
| Cursor | ✅ Should work | Same config shape; user-tested in v0.1 |
| Cline | ⚠ Untested | Should work; please report issues |
| Continue | ⚠ Untested | Should work; please report issues |
| Zed | ⚠ Untested | Should work in Zed's MCP support |
| Windsurf | ⚠ Untested | Same Cursor-shaped config |

If you successfully use this with a client not on the list, please open
a PR adding it.

## Configuration

| Env var | Default | Purpose |
|---|---|---|
| `MCP_APPLE_REMINDERS_LIST_PREFIX` | `Claude-` | Workflow-list naming convention |
| `MCP_APPLE_REMINDERS_LOG_LEVEL` | `WARNING` | `DEBUG` / `INFO` / `WARNING` / `ERROR` (logs to stderr) |

## Development

```bash
git clone https://github.com/rex/mcp-apple-reminders.git
cd mcp-apple-reminders
./install.sh
source venv/bin/activate
pre-commit install
```

```bash
ruff check .                      # lint
black --check .                   # format
mypy src/                         # types
pytest tests/unit/                # hermetic, runs on Linux + macOS
MCP_APPLE_REMINDERS_LIVE_TESTS=1 pytest tests/integration/  # macOS only
```

The unit suite mocks `pyremindkit` so it runs anywhere. The integration
suite mutates a real Reminders database under a uniquely-prefixed test list
and cleans up after itself — don't point it at an account you care about.

See [`CONTRIBUTING.md`](CONTRIBUTING.md) for more.

## Architecture

```
┌──────────────────────┐    stdio JSON-RPC     ┌─────────────────────────┐
│ MCP client           │ ◄───────────────────► │ mcp-apple-reminders     │
│ (Claude Desktop, …)  │                       │  ├── FastMCP server     │
└──────────────────────┘                       │  ├── tools / resources  │
                                               │  └── prompts            │
                                                          │
                                                          │ Python API
                                                          ▼
                                               ┌─────────────────────────┐
                                               │ pyremindkit             │
                                               │  └── PyObjC + EventKit  │
                                               └────────────┬────────────┘
                                                            │ macOS frameworks
                                                            ▼
                                               ┌─────────────────────────┐
                                               │ Apple Reminders         │
                                               │ (CalDAV + iCloud sync)  │
                                               └─────────────────────────┘
```

- **Tool schemas are generated** from Pydantic-typed function signatures
  via FastMCP — no hand-written JSON Schema.
- **Output payloads are structured** Pydantic models (Reminder, Calendar,
  ReminderList, …) serialized as JSON for downstream agent consumption.
- **`pyremindkit` is imported lazily** so the package is importable on
  Linux/CI for unit tests without EventKit available.

## Roadmap

Open to PRs on any of these:

- Subtasks (`parent_reminder_id`)
- Recurrence rules (`EKRecurrenceRule`)
- Multiple alarms per reminder
- Location reminders
- iOS Reminders Hashtags (iOS 17+, when EventKit exposes them)
- MCP `completions/complete` for argument autocompletion
- MCP resource subscriptions / change notifications

## Troubleshooting

| Symptom | Fix |
|---|---|
| `ModuleNotFoundError: pyremindkit` | `uvx --refresh mcp-apple-reminders` (after the package publishes to PyPI) |
| `Permission denied` on first run | System Settings → Privacy & Security → Reminders → enable your interpreter |
| Workflow tools error "list not found" | Create `Claude-On-Deck` / `Claude-Active` / `Claude-Done` / `Claude-Blocked` in Apple Reminders, or set `MCP_APPLE_REMINDERS_LIST_PREFIX` to match your existing names |
| `RFC 3339 datetime` errors | The server now accepts the `Z` suffix; if you still hit this, please [file an issue](https://github.com/rex/mcp-apple-reminders/issues) |
| Tools never appear in the client | Check `~/Library/Logs/Claude/mcp*.log` (Claude Desktop) or your client's equivalent |

## Contributing

See [`CONTRIBUTING.md`](CONTRIBUTING.md). Bug reports and feature
ideas welcome via [GitHub Issues](https://github.com/rex/mcp-apple-reminders/issues).
Security: see [`SECURITY.md`](SECURITY.md).

## License

MIT. See [`LICENSE`](LICENSE).

## Acknowledgments

- [`pyremindkit`](https://pypi.org/project/pyremindkit/) — the EventKit wrapper this server is built on
- [Model Context Protocol](https://modelcontextprotocol.io) — Anthropic's open protocol for tool-use
- [PyObjC](https://github.com/ronaldoussoren/pyobjc) — Python ↔ Objective-C bridge for macOS frameworks
