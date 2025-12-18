# MCP Apple Reminders

A comprehensive Model Context Protocol (MCP) server that enables Claude and other AI assistants to seamlessly interact with Apple Reminders. This server provides full integration with Apple's Reminders app through the EventKit framework, allowing AI assistants to create, read, update, delete, and search reminders and reminder lists.

## Features

- **Complete CRUD Operations**: Create, read, update, and delete reminders
- **Calendar Management**: List, search, and manage reminder calendars (lists)
- **Workflow Management**: Move reminders between lists with specialized Claude-* workflow tools
- **Advanced Filtering**: Filter reminders by due date, completion status, priority, and calendar
- **Text Search**: Search reminders by title and notes content
- **Smart Queries**: Get overdue reminders, today's reminders, and next upcoming reminder
- **Full Metadata Support**: Due dates, priorities, notes, URLs, flags, and more
- **Native macOS Integration**: Uses Apple's EventKit framework for reliable, system-level access

## Table of Contents

- [Requirements](#requirements)
- [Installation](#installation)
- [Configuration](#configuration)
  - [Claude Desktop App](#claude-desktop-app)
  - [Other MCP Clients](#other-mcp-clients)
- [Permissions](#permissions)
- [Available Tools](#available-tools)
  - [Calendar Management](#calendar-management)
  - [Reminder Operations](#reminder-operations)
  - [Query Operations](#query-operations)
  - [Workflow Management](#workflow-management)
- [Usage Examples](#usage-examples)
- [Development](#development)
- [Troubleshooting](#troubleshooting)
- [Architecture](#architecture)
- [Contributing](#contributing)
- [License](#license)

## Requirements

- **Operating System**: macOS 10.15 (Catalina) or later
- **Python**: 3.10 or later
- **Permissions**: Full access to Reminders (granted on first run)
- **MCP Client**: Claude Desktop App or any MCP-compatible client

## Installation

### Option 1: Install from Source (Recommended)

1. **Clone the repository**:
   ```bash
   cd /path/to/your/projects
   git clone https://github.com/yourusername/mcp-apple-reminders.git
   cd mcp-apple-reminders
   ```

2. **Create a virtual environment** (recommended):
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -e .
   ```

   Or install with development dependencies:
   ```bash
   pip install -e ".[dev]"
   ```

### Option 2: Install with pip

If the package is published to PyPI:

```bash
pip install mcp-apple-reminders
```

### Verify Installation

Test that the server can be imported:

```bash
python3 -c "from mcp_apple_reminders import main; print('Installation successful!')"
```

## Configuration

### Claude Desktop App

The Claude Desktop App is the primary client for this MCP server. To configure it:

1. **Locate the Claude configuration file**:
   ```
   ~/Library/Application Support/Claude/claude_desktop_config.json
   ```

2. **Edit the configuration file** to add the MCP server:

   ```json
   {
     "mcpServers": {
       "apple-reminders": {
         "command": "python3",
         "args": [
           "-m",
           "mcp_apple_reminders"
         ],
         "env": {}
       }
     }
   }
   ```

   **If you installed in a virtual environment**, use the full path to Python:
   ```json
   {
     "mcpServers": {
       "apple-reminders": {
         "command": "/path/to/your/venv/bin/python3",
         "args": [
           "-m",
           "mcp_apple_reminders"
         ],
         "env": {}
       }
     }
   }
   ```

3. **Restart Claude Desktop** to load the new configuration

4. **Verify the server is loaded**:
   - Open Claude Desktop
   - Look for the hammer (🔨) icon in the interface
   - You should see tools from "apple-reminders" available

### Other MCP Clients

For other MCP-compatible clients, refer to their documentation for adding MCP servers. The general pattern is:

```bash
python3 -m mcp_apple_reminders
```

The server communicates via stdin/stdout using the MCP protocol.

## Permissions

On first run, macOS will prompt you to grant the MCP server access to Reminders:

1. **Permission Dialog**: A system dialog will appear asking for permission
2. **Grant Access**: Click "OK" to allow access
3. **System Settings**: If you miss the dialog, go to:
   - System Settings → Privacy & Security → Reminders
   - Enable access for "Terminal" or your Python interpreter

**Note**: If permissions are not granted, the server will exit with an error message.

## Available Tools

The MCP server provides 22 comprehensive tools for managing Apple Reminders:

### Calendar Management

#### `list_calendars`

List all available reminder calendars (lists).

**Parameters**: None

**Returns**: All reminder lists with their IDs, names, colors, and default status.

**Example**:
```
list_calendars()
```

#### `get_calendar`

Get a specific calendar by name.

**Parameters**:
- `name` (string, required): Exact name of the calendar

**Example**:
```
get_calendar(name="Personal")
```

#### `get_calendar_by_id`

Get a specific calendar by its unique ID.

**Parameters**:
- `calendar_id` (string, required): Unique identifier of the calendar

**Example**:
```
get_calendar_by_id(calendar_id="F2E4D3C2-B1A0-...")
```

#### `search_calendars`

Search for calendars by partial name match (case-insensitive).

**Parameters**:
- `query` (string, required): Search query string

**Example**:
```
search_calendars(query="work")
```

#### `get_default_calendar`

Get the default calendar for new reminders.

**Parameters**: None

**Returns**: The default reminder list.

**Example**:
```
get_default_calendar()
```

### Reminder Operations

#### `create_reminder`

Create a new reminder in Apple Reminders.

**Parameters**:
- `title` (string, required): The title/name of the reminder
- `due_date` (string, optional): ISO format datetime (e.g., "2024-01-15T14:30:00")
- `notes` (string, optional): Additional notes or description
- `priority` (string, optional): "none", "low", "medium", "high", or 0-9
- `url` (string, optional): URL to associate with the reminder
- `calendar_id` (string, optional): ID of the calendar to add to (uses default if not specified)

**Example**:
```
create_reminder(
    title="Buy groceries",
    due_date="2024-01-20T18:00:00",
    notes="Milk, eggs, bread",
    priority="high"
)
```

#### `update_reminder`

Update an existing reminder. Only specified fields are updated.

**Parameters**:
- `reminder_id` (string, required): Unique identifier of the reminder
- `title` (string, optional): New title
- `due_date` (string, optional): New due date (ISO format)
- `notes` (string, optional): New notes
- `priority` (string, optional): New priority
- `url` (string, optional): New URL
- `is_completed` (boolean, optional): Completion status

**Example**:
```
update_reminder(
    reminder_id="A1B2C3D4-...",
    title="Buy groceries (Updated)",
    priority="medium"
)
```

#### `complete_reminder`

Mark a reminder as completed.

**Parameters**:
- `reminder_id` (string, required): Unique identifier of the reminder

**Example**:
```
complete_reminder(reminder_id="A1B2C3D4-...")
```

#### `uncomplete_reminder`

Mark a reminder as incomplete (reopen it).

**Parameters**:
- `reminder_id` (string, required): Unique identifier of the reminder

**Example**:
```
uncomplete_reminder(reminder_id="A1B2C3D4-...")
```

#### `get_reminder`

Get a specific reminder by its unique ID.

**Parameters**:
- `reminder_id` (string, required): Unique identifier of the reminder

**Returns**: Complete reminder details including all metadata.

**Example**:
```
get_reminder(reminder_id="A1B2C3D4-...")
```

#### `delete_reminder`

Permanently delete a reminder (cannot be undone).

**Parameters**:
- `reminder_id` (string, required): Unique identifier of the reminder

**Example**:
```
delete_reminder(reminder_id="A1B2C3D4-...")
```

### Query Operations

#### `get_reminders`

Get reminders with optional filters.

**Parameters**:
- `due_after` (string, optional): Only return reminders due after this date (ISO format)
- `due_before` (string, optional): Only return reminders due before this date (ISO format)
- `is_completed` (boolean, optional): Filter by completion status
- `priority` (string, optional): Filter by priority ("none", "low", "medium", "high")
- `calendar_id` (string, optional): Only return reminders from this calendar
- `limit` (integer, optional): Maximum number of results

**Example**:
```
get_reminders(
    due_before="2024-01-20T23:59:59",
    is_completed=false,
    priority="high",
    limit=10
)
```

#### `search_reminders`

Search for reminders by text in title or notes.

**Parameters**:
- `query` (string, required): Search query string
- `limit` (integer, optional): Maximum number of results

**Example**:
```
search_reminders(query="groceries", limit=5)
```

#### `get_next_reminder`

Get the next upcoming incomplete reminder based on due date.

**Parameters**: None

**Returns**: The soonest incomplete reminder with a due date, or nothing if none exist.

**Example**:
```
get_next_reminder()
```

#### `get_overdue_reminders`

Get all incomplete reminders that are overdue (due date in the past).

**Parameters**:
- `limit` (integer, optional): Maximum number of results

**Example**:
```
get_overdue_reminders(limit=10)
```

#### `get_today_reminders`

Get all reminders due today.

**Parameters**:
- `include_completed` (boolean, optional): Whether to include completed reminders (default: false)

**Example**:
```
get_today_reminders(include_completed=true)
```

### Workflow Management

#### `get_workflow_lists`

Get all workflow lists (calendars starting with 'Claude-').

**Parameters**: None

**Returns**: All Claude-* calendars for workflow management.

**Example**:
```
get_workflow_lists()
```

#### `move_reminder_to_list`

Move a reminder to a different calendar/list.

**Parameters**:
- `reminder_id` (string, required): Unique identifier of the reminder
- `calendar_id` (string, required): Unique identifier of the target calendar

**Returns**: The updated reminder in its new list.

**Example**:
```
move_reminder_to_list(
    reminder_id="A1B2C3D4-...",
    calendar_id="E5F6G7H8-..."
)
```

#### `move_reminder_on_deck`

Move a reminder to the 'Claude-On-Deck' workflow list (convenience function).

**Parameters**:
- `reminder_id` (string, required): Unique identifier of the reminder

**Returns**: The updated reminder now in the On-Deck list.

**Example**:
```
move_reminder_on_deck(reminder_id="A1B2C3D4-...")
```

**Note**: This indicates the task is queued and ready to be worked on next.

#### `move_reminder_active`

Move a reminder to the 'Claude-Active' workflow list (convenience function).

**Parameters**:
- `reminder_id` (string, required): Unique identifier of the reminder

**Returns**: The updated reminder now in the Active list.

**Example**:
```
move_reminder_active(reminder_id="A1B2C3D4-...")
```

**Note**: This indicates the task is currently being worked on.

#### `move_reminder_done`

Move a reminder to the 'Claude-Done' workflow list (convenience function).

**Parameters**:
- `reminder_id` (string, required): Unique identifier of the reminder

**Returns**: The updated reminder now in the Done list.

**Example**:
```
move_reminder_done(reminder_id="A1B2C3D4-...")
```

**Note**: This indicates the task has been completed.

#### `move_reminder_blocked`

Move a reminder to the 'Claude-Waiting' workflow list (convenience function).

**Parameters**:
- `reminder_id` (string, required): Unique identifier of the reminder

**Returns**: The updated reminder now in the Waiting list.

**Example**:
```
move_reminder_blocked(reminder_id="A1B2C3D4-...")
```

**Note**: This indicates the task is blocked or waiting for external input.

## Usage Examples

### Example 1: Daily Task Management with Claude

**User**: "Show me all my tasks due today"

**Claude** will use:
```
get_today_reminders(include_completed=false)
```

### Example 2: Creating a Reminder

**User**: "Remind me to call the dentist tomorrow at 2 PM"

**Claude** will:
1. Calculate tomorrow's date at 2 PM
2. Use:
   ```
   create_reminder(
       title="Call the dentist",
       due_date="2024-01-16T14:00:00"
   )
   ```

### Example 3: Managing Priorities

**User**: "Change my 'Finish report' reminder to high priority"

**Claude** will:
1. Search for the reminder:
   ```
   search_reminders(query="Finish report")
   ```
2. Update it:
   ```
   update_reminder(
       reminder_id="<found_id>",
       priority="high"
   )
   ```

### Example 4: Finding Overdue Tasks

**User**: "What tasks am I behind on?"

**Claude** will use:
```
get_overdue_reminders()
```

### Example 5: Working with Multiple Lists

**User**: "Add 'Review PR #123' to my Work list with high priority"

**Claude** will:
1. Find the Work calendar:
   ```
   search_calendars(query="Work")
   ```
2. Create the reminder:
   ```
   create_reminder(
       title="Review PR #123",
       priority="high",
       calendar_id="<work_calendar_id>"
   )
   ```

### Example 6: Completing Tasks

**User**: "I finished buying groceries"

**Claude** will:
1. Find the reminder:
   ```
   search_reminders(query="groceries")
   ```
2. Mark it complete:
   ```
   complete_reminder(reminder_id="<found_id>")
   ```

### Example 7: Workflow Management

**User**: "Move my task about updating docs to the Active list so I can work on it"

**Claude** will:
1. Find the reminder:
   ```
   search_reminders(query="updating docs")
   ```
2. Move to Active:
   ```
   move_reminder_active(reminder_id="<found_id>")
   ```

**User**: "Show me all my workflow lists"

**Claude** will use:
```
get_workflow_lists()
```

**User**: "Move all my brain dump items to On-Deck"

**Claude** will:
1. Get reminders from Brain Dump:
   ```
   get_reminders(calendar_id="<Claude-Brain-Dump ID>")
   ```
2. For each reminder:
   ```
   move_reminder_on_deck(reminder_id="<reminder_id>")
   ```

## Development

### Project Structure

```
mcp-apple-reminders/
├── src/
│   └── mcp_apple_reminders/
│       ├── __init__.py          # Package initialization
│       └── server.py            # MCP server implementation
├── libs/
│   └── pyremindkit/            # Python wrapper for EventKit
│       └── src/
│           └── pyremindkit/
│               ├── __init__.py
│               └── core.py      # Core RemindKit functionality
├── pyproject.toml              # Project configuration
├── README.md                   # This file
└── LICENSE                     # MIT License
```

### Running Tests

```bash
# Install development dependencies
pip install -e ".[dev]"

# Run tests (when available)
pytest
```

### Code Style

This project uses:
- **Black** for code formatting
- **Ruff** for linting
- **Type hints** throughout the codebase

Format code:
```bash
black src/
```

Lint code:
```bash
ruff check src/
```

### Debugging

To debug the MCP server:

1. **Enable logging** in the server code:
   ```python
   import logging
   logging.basicConfig(level=logging.DEBUG)
   ```

2. **Run the server directly**:
   ```bash
   python3 -m mcp_apple_reminders
   ```

3. **Check Claude Desktop logs**:
   ```bash
   tail -f ~/Library/Logs/Claude/mcp*.log
   ```

## Troubleshooting

### Permission Errors

**Problem**: "No access to reminders" error

**Solution**:
1. Go to System Settings → Privacy & Security → Reminders
2. Ensure Python/Terminal has access
3. Try running the server again

### Server Not Appearing in Claude

**Problem**: Tools not visible in Claude Desktop

**Solution**:
1. Check the configuration file path: `~/Library/Application Support/Claude/claude_desktop_config.json`
2. Verify JSON syntax is correct (no trailing commas)
3. Ensure Python path is correct (use `which python3` to find it)
4. Restart Claude Desktop completely (quit from menu bar)
5. Check Claude logs for errors

### Import Errors

**Problem**: "ModuleNotFoundError: No module named 'mcp'" or similar

**Solution**:
```bash
# Reinstall dependencies
pip install --upgrade mcp pyobjc-core pyobjc-framework-EventKit

# Or reinstall the package
pip install -e .
```

### DateTime Parsing Errors

**Problem**: "Invalid datetime format" error

**Solution**: Ensure dates are in ISO format: `YYYY-MM-DDTHH:MM:SS`

Example: `2024-01-15T14:30:00` (not `01/15/2024 2:30 PM`)

### Reminder Not Found

**Problem**: "Reminder with ID '...' not found"

**Possible Causes**:
- Reminder was deleted
- Reminder is in a calendar without access
- ID is incorrect

**Solution**: Use `search_reminders` or `get_reminders` to find the correct reminder ID

## Architecture

### Technology Stack

- **MCP Protocol**: Model Context Protocol for AI-application integration
- **Python**: Core implementation language (3.10+)
- **PyObjC**: Python-Objective-C bridge for macOS frameworks
- **EventKit**: Apple's framework for calendar and reminder access
- **pyremindkit**: Python wrapper around EventKit (included in libs/)

### How It Works

1. **MCP Server**: Implements the Model Context Protocol server interface
2. **Tool Registration**: Each operation is registered as an MCP tool with schema
3. **RemindKit Integration**: Tools call pyremindkit functions
4. **EventKit Communication**: pyremindkit uses PyObjC to communicate with EventKit
5. **System Integration**: EventKit provides system-level access to Apple Reminders

### Data Flow

```
Claude Desktop
    ↓ (MCP Protocol via stdio)
MCP Server (server.py)
    ↓ (Python function calls)
RemindKit (libs/pyremindkit/core.py)
    ↓ (PyObjC bridge)
EventKit Framework
    ↓ (System API)
Apple Reminders App
```

### Priority Mapping

Apple Reminders uses integer priorities (0-9):
- **0**: None (no priority)
- **1-4**: Low (we use 1)
- **5**: Medium
- **6-9**: High (we use 9)

The MCP server accepts both named priorities ("none", "low", "medium", "high") and raw integers (0-9).

### Date Handling

- **Input**: ISO 8601 format strings (`2024-01-15T14:30:00`)
- **Internal**: Python `datetime` objects
- **EventKit**: `NSDate` and `NSDateComponents` objects
- **Output**: ISO format strings in reminder details

## Contributing

Contributions are welcome! Please follow these guidelines:

1. **Fork the repository**
2. **Create a feature branch**: `git checkout -b feature/amazing-feature`
3. **Make your changes**:
   - Add tests for new functionality
   - Update documentation
   - Follow code style (Black + Ruff)
4. **Commit your changes**: `git commit -m 'Add amazing feature'`
5. **Push to the branch**: `git push origin feature/amazing-feature`
6. **Open a Pull Request**

### Development Setup

```bash
# Clone your fork
git clone https://github.com/yourusername/mcp-apple-reminders.git
cd mcp-apple-reminders

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install in development mode
pip install -e ".[dev]"

# Make changes and test
python3 -m mcp_apple_reminders
```

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Support

If you encounter any problems or have suggestions:

- **Issues**: Open an issue on GitHub
- **Discussions**: Use GitHub Discussions for questions and ideas
- **Pull Requests**: Contributions are welcome!

## Acknowledgments

- **pyremindkit**: Python wrapper for Apple's EventKit framework
- **Model Context Protocol**: Anthropic's protocol for AI-application integration
- **Claude Desktop**: Primary client for this MCP server
- **PyObjC**: Python-Objective-C bridge enabling macOS framework access

## Changelog

### Version 0.1.0 (Initial Release)

- Complete CRUD operations for reminders
- Calendar/list management
- Advanced filtering and search
- Smart query operations (overdue, today, next)
- Full metadata support
- Comprehensive documentation
- Claude Desktop integration

---

**Made with ❤️ for the Claude community**
