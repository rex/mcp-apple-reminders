# Quick Start Guide

Get up and running with MCP Apple Reminders in under 5 minutes!

## Prerequisites

- macOS 10.15 or later
- Python 3.10 or later
- Claude Desktop App installed

## Installation Steps

### 1. Install the MCP Server

Run the installation script:

```bash
cd /Users/pierce/Code/mcp-apple-reminders
./install.sh
```

This will:
- Create a virtual environment
- Install all dependencies
- Set up the MCP server

### 2. Configure Claude Desktop

Edit the Claude configuration file:

```bash
open ~/Library/Application\ Support/Claude/claude_desktop_config.json
```

Add the MCP server configuration:

```json
{
  "mcpServers": {
    "apple-reminders": {
      "command": "/Users/pierce/Code/mcp-apple-reminders/venv/bin/python3",
      "args": ["-m", "mcp_apple_reminders"]
    }
  }
}
```

**Important**: Replace `/Users/pierce/Code/mcp-apple-reminders` with the actual path to your installation if different.

### 3. Restart Claude Desktop

Completely quit Claude Desktop (⌘Q) and reopen it.

### 4. Grant Permissions

On first use, macOS will prompt for Reminders access:

1. A system dialog will appear
2. Click "OK" to grant access
3. If you miss it, go to: System Settings → Privacy & Security → Reminders

### 5. Test It Out!

Try these commands in Claude:

- "Show me all my reminder lists"
- "What reminders do I have due today?"
- "Create a reminder to buy milk tomorrow at 2 PM"
- "Show me my overdue tasks"

## Verification

Look for the hammer icon (🔨) in Claude Desktop. Click it to see available tools from "apple-reminders".

## Troubleshooting

### Tools not appearing?

1. Check the config file path is correct
2. Verify the Python path in the config
3. Check Claude logs: `tail -f ~/Library/Logs/Claude/mcp*.log`
4. Restart Claude Desktop completely

### Permission errors?

Go to System Settings → Privacy & Security → Reminders and ensure Python/Terminal has access.

## Next Steps

- Read the [full README](README.md) for all features
- Explore all 17 available tools
- Create custom workflows with Claude

## Need Help?

- Check the [README](README.md) for detailed documentation
- See [Troubleshooting](README.md#troubleshooting) section
- Open an issue on GitHub
