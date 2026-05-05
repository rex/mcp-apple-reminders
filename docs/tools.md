# MCP Apple Reminders - Complete Tool Reference

This document provides a comprehensive reference for all 17 tools provided by the MCP Apple Reminders server.

## Table of Contents

- [Calendar Management (5 tools)](#calendar-management)
- [Reminder CRUD Operations (6 tools)](#reminder-crud-operations)
- [Query Operations (6 tools)](#query-operations)

---

## Calendar Management

### 1. list_calendars

**Description**: List all available reminder calendars (lists)

**Parameters**: None

**Returns**:
- Calendar name
- Calendar ID (unique identifier)
- Color
- Default status
- Owner

**Example Request**:
```json
{
  "name": "list_calendars",
  "arguments": {}
}
```

**Example Response**:
```
Found 3 calendar(s):

Name: Reminders
ID: F2E4D3C2-B1A0-4F3E-9D8C-7B6A5E4D3C2B
Color: #FF3B30
Default: Yes
Owner: Unknown
----------------------------------------
Name: Work
ID: A1B2C3D4-E5F6-4A3B-8C9D-0E1F2A3B4C5D
Color: #007AFF
Default: No
Owner: Unknown
----------------------------------------
...
```

**Use Cases**:
- Discover available reminder lists
- Get calendar IDs for creating reminders
- View calendar organization

---

### 2. get_calendar

**Description**: Get a specific calendar by its exact name

**Parameters**:
- `name` (string, required): Exact name of the calendar

**Returns**: Single calendar details

**Example Request**:
```json
{
  "name": "get_calendar",
  "arguments": {
    "name": "Work"
  }
}
```

**Example Response**:
```
Calendar Found:
Name: Work
ID: A1B2C3D4-E5F6-4A3B-8C9D-0E1F2A3B4C5D
Color: #007AFF
Default: No
Owner: Unknown
```

**Use Cases**:
- Find a specific list by name
- Get calendar ID for operations
- Verify calendar exists

**Error Handling**: Raises ValueError if calendar not found

---

### 3. get_calendar_by_id

**Description**: Get a specific calendar by its unique identifier

**Parameters**:
- `calendar_id` (string, required): Unique calendar identifier

**Returns**: Single calendar details

**Example Request**:
```json
{
  "name": "get_calendar_by_id",
  "arguments": {
    "calendar_id": "A1B2C3D4-E5F6-4A3B-8C9D-0E1F2A3B4C5D"
  }
}
```

**Example Response**:
```
Calendar Found:
Name: Work
ID: A1B2C3D4-E5F6-4A3B-8C9D-0E1F2A3B4C5D
Color: #007AFF
Default: No
Owner: Unknown
```

**Use Cases**:
- Retrieve calendar by known ID
- More reliable than name lookup
- Verify calendar still exists

**Error Handling**: Raises ValueError if ID not found

---

### 4. search_calendars

**Description**: Search for calendars by partial name match (case-insensitive)

**Parameters**:
- `query` (string, required): Search query string

**Returns**: List of matching calendars

**Example Request**:
```json
{
  "name": "search_calendars",
  "arguments": {
    "query": "work"
  }
}
```

**Example Response**:
```
Found 2 calendar(s) matching 'work':

Name: Work
ID: A1B2C3D4-E5F6-4A3B-8C9D-0E1F2A3B4C5D
Color: #007AFF
Default: No
----------------------------------------
Name: Workouts
ID: B2C3D4E5-F6A7-5B4C-9D0E-1F2A3B4C5D6E
Color: #34C759
Default: No
----------------------------------------
```

**Use Cases**:
- Fuzzy search for calendars
- Find calendars with similar names
- Explore available lists

---

### 5. get_default_calendar

**Description**: Get the default calendar for new reminders

**Parameters**: None

**Returns**: Default calendar details

**Example Request**:
```json
{
  "name": "get_default_calendar",
  "arguments": {}
}
```

**Example Response**:
```
Default Calendar:
Name: Reminders
ID: F2E4D3C2-B1A0-4F3E-9D8C-7B6A5E4D3C2B
Color: #FF3B30
Owner: Unknown
```

**Use Cases**:
- Find where new reminders will be created
- Get default list for operations
- Verify default configuration

---

## Reminder CRUD Operations

### 6. create_reminder

**Description**: Create a new reminder in Apple Reminders

**Parameters**:
- `title` (string, required): Reminder title
- `due_date` (string, optional): ISO format datetime (e.g., "2024-01-15T14:30:00")
- `notes` (string, optional): Additional notes/description
- `priority` (string, optional): "none", "low", "medium", "high", or 0-9
- `url` (string, optional): Associated URL
- `calendar_id` (string, optional): Target calendar ID (uses default if not specified)

**Returns**: Created reminder with all details

**Example Request**:
```json
{
  "name": "create_reminder",
  "arguments": {
    "title": "Buy groceries",
    "due_date": "2024-01-20T18:00:00",
    "notes": "Milk, eggs, bread, cheese",
    "priority": "high",
    "url": "https://grocery-list.example.com"
  }
}
```

**Example Response**:
```
Reminder created successfully!

ID: X9Y8Z7W6-V5U4-T3S2-R1Q0-P9O8N7M6L5K4
Title: Buy groceries
Completed: No
Due Date: 2024-01-20 18:00:00
Notes: Milk, eggs, bread, cheese
URL: https://grocery-list.example.com
Priority: High
List ID: F2E4D3C2-B1A0-4F3E-9D8C-7B6A5E4D3C2B
Created: 2024-01-15 10:30:00
Modified: 2024-01-15 10:30:00
Flagged: No
```

**Use Cases**:
- Create new tasks
- Set reminders with due dates
- Add detailed notes and metadata
- Organize into specific lists

**Priority Values**:
- "none" or 0: No priority
- "low" or 1: Low priority (blue exclamation)
- "medium" or 5: Medium priority (orange exclamation)
- "high" or 9: High priority (red exclamation)
- 2-4, 6-8: Custom intermediate values

---

### 7. update_reminder

**Description**: Update an existing reminder (only specified fields are changed)

**Parameters**:
- `reminder_id` (string, required): Unique reminder identifier
- `title` (string, optional): New title
- `due_date` (string, optional): New due date (ISO format)
- `notes` (string, optional): New notes
- `priority` (string, optional): New priority
- `url` (string, optional): New URL
- `is_completed` (boolean, optional): Completion status

**Returns**: Updated reminder with all details

**Example Request**:
```json
{
  "name": "update_reminder",
  "arguments": {
    "reminder_id": "X9Y8Z7W6-V5U4-T3S2-R1Q0-P9O8N7M6L5K4",
    "title": "Buy groceries (organic)",
    "priority": "medium",
    "notes": "Organic milk, free-range eggs, whole grain bread"
  }
}
```

**Example Response**:
```
Reminder updated successfully!

ID: X9Y8Z7W6-V5U4-T3S2-R1Q0-P9O8N7M6L5K4
Title: Buy groceries (organic)
Completed: No
Due Date: 2024-01-20 18:00:00
Notes: Organic milk, free-range eggs, whole grain bread
Priority: Medium
...
```

**Use Cases**:
- Modify reminder details
- Change due dates
- Update priorities
- Add or modify notes
- Mark as complete/incomplete

**Note**: Only the fields you specify will be updated. All other fields remain unchanged.

---

### 8. complete_reminder

**Description**: Mark a reminder as completed (convenience wrapper for update_reminder)

**Parameters**:
- `reminder_id` (string, required): Unique reminder identifier

**Returns**: Updated reminder showing completed status

**Example Request**:
```json
{
  "name": "complete_reminder",
  "arguments": {
    "reminder_id": "X9Y8Z7W6-V5U4-T3S2-R1Q0-P9O8N7M6L5K4"
  }
}
```

**Example Response**:
```
Reminder marked as complete!

ID: X9Y8Z7W6-V5U4-T3S2-R1Q0-P9O8N7M6L5K4
Title: Buy groceries
Completed: Yes
...
```

**Use Cases**:
- Quick task completion
- Check off finished items
- Update task status

---

### 9. uncomplete_reminder

**Description**: Mark a reminder as incomplete (reopen a completed reminder)

**Parameters**:
- `reminder_id` (string, required): Unique reminder identifier

**Returns**: Updated reminder showing incomplete status

**Example Request**:
```json
{
  "name": "uncomplete_reminder",
  "arguments": {
    "reminder_id": "X9Y8Z7W6-V5U4-T3S2-R1Q0-P9O8N7M6L5K4"
  }
}
```

**Use Cases**:
- Reopen completed tasks
- Fix accidental completions
- Recurring task management

---

### 10. get_reminder

**Description**: Get detailed information about a specific reminder

**Parameters**:
- `reminder_id` (string, required): Unique reminder identifier

**Returns**: Complete reminder details

**Example Request**:
```json
{
  "name": "get_reminder",
  "arguments": {
    "reminder_id": "X9Y8Z7W6-V5U4-T3S2-R1Q0-P9O8N7M6L5K4"
  }
}
```

**Example Response**:
```
Reminder Details:

ID: X9Y8Z7W6-V5U4-T3S2-R1Q0-P9O8N7M6L5K4
Title: Buy groceries
Completed: No
Due Date: 2024-01-20 18:00:00
Notes: Milk, eggs, bread
Priority: High
List ID: F2E4D3C2-B1A0-4F3E-9D8C-7B6A5E4D3C2B
Created: 2024-01-15 10:30:00
Modified: 2024-01-15 10:30:00
Flagged: No
```

**Use Cases**:
- View full reminder details
- Verify reminder exists
- Get reminder metadata
- Check current status

**Error Handling**: Raises ValueError if reminder not found

---

### 11. delete_reminder

**Description**: Permanently delete a reminder (cannot be undone)

**Parameters**:
- `reminder_id` (string, required): Unique reminder identifier

**Returns**: Success/failure message

**Example Request**:
```json
{
  "name": "delete_reminder",
  "arguments": {
    "reminder_id": "X9Y8Z7W6-V5U4-T3S2-R1Q0-P9O8N7M6L5K4"
  }
}
```

**Example Response**:
```
Reminder X9Y8Z7W6-V5U4-T3S2-R1Q0-P9O8N7M6L5K4 deleted successfully.
```

**Use Cases**:
- Remove completed tasks
- Clean up old reminders
- Delete cancelled tasks

**Warning**: This action is permanent and cannot be undone!

**Error Handling**: Raises ValueError if reminder not found

---

## Query Operations

### 12. get_reminders

**Description**: Get reminders with optional filters

**Parameters** (all optional):
- `due_after` (string): Only return reminders due after this date (ISO format)
- `due_before` (string): Only return reminders due before this date (ISO format)
- `is_completed` (boolean): Filter by completion status
- `priority` (string): Filter by priority ("none", "low", "medium", "high")
- `calendar_id` (string): Only return reminders from specific calendar
- `limit` (integer): Maximum number of results

**Returns**: List of matching reminders

**Example Request**:
```json
{
  "name": "get_reminders",
  "arguments": {
    "due_before": "2024-01-20T23:59:59",
    "is_completed": false,
    "priority": "high",
    "limit": 10
  }
}
```

**Example Response**:
```
Found 3 reminder(s):

=== Reminder 1 ===
ID: X9Y8Z7W6-V5U4-T3S2-R1Q0-P9O8N7M6L5K4
Title: Buy groceries
Completed: No
Due Date: 2024-01-20 18:00:00
Priority: High
...
========================================

=== Reminder 2 ===
...
```

**Use Cases**:
- Find reminders by date range
- Filter by completion status
- Get high-priority tasks
- List reminders from specific calendar
- Build custom queries

**Note**: Without any filters, returns ALL reminders from all calendars.

---

### 13. search_reminders

**Description**: Search for reminders by text in title or notes (case-insensitive)

**Parameters**:
- `query` (string, required): Search query string
- `limit` (integer, optional): Maximum number of results

**Returns**: List of matching reminders

**Example Request**:
```json
{
  "name": "search_reminders",
  "arguments": {
    "query": "groceries",
    "limit": 5
  }
}
```

**Example Response**:
```
Found 2 reminder(s) matching 'groceries':

=== Reminder 1 ===
ID: X9Y8Z7W6-V5U4-T3S2-R1Q0-P9O8N7M6L5K4
Title: Buy groceries
Notes: Milk, eggs, bread
...
========================================

=== Reminder 2 ===
ID: A1B2C3D4-E5F6-7G8H-9I0J-K1L2M3N4O5P6
Title: Plan grocery shopping
Notes: Compare prices at different grocers
...
```

**Use Cases**:
- Find reminders by keyword
- Search across all lists
- Locate specific tasks
- Full-text search

**Search Scope**: Searches both title AND notes fields

---

### 14. get_next_reminder

**Description**: Get the next upcoming incomplete reminder (soonest due date)

**Parameters**: None

**Returns**: Single reminder (the next one due), or nothing if no upcoming reminders

**Example Request**:
```json
{
  "name": "get_next_reminder",
  "arguments": {}
}
```

**Example Response**:
```
Next Upcoming Reminder:

ID: X9Y8Z7W6-V5U4-T3S2-R1Q0-P9O8N7M6L5K4
Title: Buy groceries
Due Date: 2024-01-20 18:00:00
Priority: High
...
```

**Use Cases**:
- Find what's coming up next
- Focus on immediate tasks
- Check next deadline
- Task prioritization

**Note**: Only returns incomplete reminders that have a due date set

---

### 15. get_overdue_reminders

**Description**: Get all incomplete reminders with due dates in the past

**Parameters**:
- `limit` (integer, optional): Maximum number of results

**Returns**: List of overdue reminders

**Example Request**:
```json
{
  "name": "get_overdue_reminders",
  "arguments": {
    "limit": 10
  }
}
```

**Example Response**:
```
Found 2 overdue reminder(s):

=== Reminder 1 ===
ID: A1B2C3D4-E5F6-7G8H-9I0J-K1L2M3N4O5P6
Title: Submit expense report
Due Date: 2024-01-10 17:00:00
Priority: High
...
========================================

=== Reminder 2 ===
ID: B2C3D4E5-F6G7-8H9I-0J1K-L2M3N4O5P6Q7
Title: Review contract
Due Date: 2024-01-12 14:00:00
Priority: Medium
...
```

**Use Cases**:
- Find tasks that need immediate attention
- Identify missed deadlines
- Catch-up planning
- Task triage

**Note**: Only returns incomplete reminders (completed overdue tasks are not included)

---

### 16. get_today_reminders

**Description**: Get all reminders due today (midnight to 11:59:59 PM)

**Parameters**:
- `include_completed` (boolean, optional): Include completed reminders (default: false)

**Returns**: List of today's reminders

**Example Request**:
```json
{
  "name": "get_today_reminders",
  "arguments": {
    "include_completed": false
  }
}
```

**Example Response**:
```
Found 4 reminder(s) due today:

=== Reminder 1 ===
ID: X9Y8Z7W6-V5U4-T3S2-R1Q0-P9O8N7M6L5K4
Title: Morning standup
Due Date: 2024-01-15 09:00:00
Completed: No
...
========================================

=== Reminder 2 ===
ID: Y0Z1A2B3-C4D5-E6F7-G8H9-I0J1K2L3M4N5
Title: Lunch meeting
Due Date: 2024-01-15 12:00:00
Completed: No
...
```

**Use Cases**:
- Daily task management
- Morning planning
- Daily review
- Track daily progress

**Note**: "Today" is based on the system's current date and timezone

---

## Error Handling

All tools return errors in a consistent format:

```
Error: [Detailed error message]
```

Common errors:
- **ValueError**: Invalid parameters, reminder/calendar not found
- **PermissionError**: No access to Reminders (needs user to grant permissions)
- **RuntimeError**: Operation failed (e.g., failed to save reminder)

## Date Format

All date/time parameters must use ISO 8601 format:

```
YYYY-MM-DDTHH:MM:SS
```

Examples:
- `2024-01-15T14:30:00` (January 15, 2024 at 2:30 PM)
- `2024-12-31T23:59:59` (December 31, 2024 at 11:59:59 PM)

## Priority Mapping

| String | Integer | Display | EventKit Range |
|--------|---------|---------|----------------|
| none   | 0       | None    | 0              |
| low    | 1       | !       | 1-4            |
| medium | 5       | !!      | 5              |
| high   | 9       | !!!     | 6-9            |

You can use either string values ("low") or integers (0-9) for priority parameters.

## Best Practices

1. **Use calendar_id when possible**: More reliable than calendar names
2. **Store reminder IDs**: For future updates/deletions
3. **Handle not found errors**: Reminders can be deleted outside your app
4. **Use appropriate filters**: Narrow results with `limit` parameter
5. **Test permissions first**: Call `list_calendars` to verify access
6. **Use ISO dates**: Always format dates as `YYYY-MM-DDTHH:MM:SS`
7. **Search before update**: Use `search_reminders` to find reminder IDs

## Tool Combinations

### Complete Workflow Examples

**Creating a reminder in a specific list**:
1. `search_calendars(query="Work")` - Find the work calendar
2. `create_reminder(title="...", calendar_id="...")` - Create in that calendar

**Finding and updating a reminder**:
1. `search_reminders(query="...")` - Find the reminder
2. `update_reminder(reminder_id="...", ...)` - Update it

**Daily review workflow**:
1. `get_overdue_reminders()` - Check what's late
2. `get_today_reminders()` - See today's tasks
3. `get_next_reminder()` - Preview what's coming

**Task completion workflow**:
1. `search_reminders(query="...")` - Find the task
2. `complete_reminder(reminder_id="...")` - Mark it done

---

For more examples and detailed usage, see the [main README](README.md).
