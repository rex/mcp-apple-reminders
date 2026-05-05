# Quick Start

Get up and running in under 5 minutes.

## Prerequisites

- macOS 10.15+
- Python 3.10+ (Homebrew recommended: `brew install python@3.12`)
- An MCP-compatible client (Claude Desktop, Codex, Cursor, Cline, Continue, Zed, …)
- [`uv`](https://docs.astral.sh/uv/) (recommended): `brew install uv`

## Option A — `uvx` (recommended, no checkout)

Point your MCP client at `uvx`. It downloads the latest release into a managed
cache and runs it.

**Claude Desktop** (`~/Library/Application Support/Claude/claude_desktop_config.json`):

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

**Codex** (`~/.codex/config.toml`):

```toml
[mcp_servers.apple-reminders]
command = "uvx"
args = ["mcp-apple-reminders"]
enabled = true
```

Restart your client and look for the `apple-reminders` tools.

## Option B — local checkout (for development)

```bash
git clone https://github.com/rex/mcp-apple-reminders.git
cd mcp-apple-reminders
./install.sh
```

The installer creates `./venv` and installs the package in editable mode. Then
configure your client to use the venv interpreter:

```json
{
  "mcpServers": {
    "apple-reminders": {
      "command": "/ABS/PATH/mcp-apple-reminders/venv/bin/python3",
      "args": ["-m", "mcp_apple_reminders"]
    }
  }
}
```

> Replace `/ABS/PATH/` with the absolute path to your checkout.

## First-run permission

On first launch macOS shows a Reminders access prompt. Click **OK**. If the
prompt never appears (some MCP clients suppress it), point the client at the
included `shim_mcp.sh` once — it pokes Reminders so the prompt surfaces — then
switch back to the regular config.

If you missed the prompt, grant access in
**System Settings → Privacy & Security → Reminders**.

## Try it

In your MCP client, ask:

- "Show me everything overdue."
- "Plan my day."
- "Triage my inbox."
- "Move 'Call dentist' to On Deck."

## Troubleshooting

| Symptom | Fix |
|---|---|
| Tools don't appear | Restart the client; check `~/Library/Logs/Claude/mcp*.log` |
| `python3: not found` | Install Python 3.10+; don't rely on the macOS system Python |
| Permission error | System Settings → Privacy & Security → Reminders → enable your interpreter |
| `ModuleNotFoundError: pyremindkit` | Make sure `pyremindkit` is on PyPI and reinstall (`uvx --refresh mcp-apple-reminders`) |

## Next steps

- Full docs: [README.md](README.md)
- Tool reference: [docs/tools.md](docs/tools.md)
- Report issues: <https://github.com/rex/mcp-apple-reminders/issues>
