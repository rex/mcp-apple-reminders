# Tool reference

Auto-generated against `mcp-apple-reminders` v0.2.0.

The server exposes three MCP capabilities:

- **Tools** — read/write actions, listed below.
- **Resources** — `apple-reminders://` URIs for browsing without spending tool turns.
- **Prompts** — pre-canned ADHD workflow recipes (`plan_my_day`, `triage_inbox`, `weekly_review`, `quick_capture`, `defer_to_someday`, `snooze`).

All tool inputs are Pydantic-validated; outputs are Pydantic models that the
MCP SDK serializes as structured JSON in the tool result.

## Lists ("calendars" in Apple's API)

### `list_calendars`

List every reminder list. Returns `CalendarList`.

### `get_calendar(name: str) -> Calendar`

Get a list by exact name.

### `get_calendar_by_id(calendar_id: str) -> Calendar`

Get a list by ID. More reliable than name lookup.

### `search_calendars(query: str) -> CalendarList`

Substring search over list names (case-insensitive).

### `get_default_calendar() -> Calendar`

The default list new reminders are created in.

### `get_workflow_lists() -> CalendarList`

The four kanban-style workflow lists (On-Deck / Active / Done / Blocked).
Naming follows `MCP_APPLE_REMINDERS_LIST_PREFIX` (default: `Claude-`).

## Reminder CRUD

### `create_reminder(...)`

| Arg | Type | Default | Notes |
|---|---|---|---|
| `title` | `str` | required | min length 1 |
| `due_date` | `str \| None` | `None` | ISO 8601; trailing `Z` accepted |
| `notes` | `str \| None` | `None` | |
| `priority` | `str \| int \| None` | `None` | `'none'`/`'low'`/`'medium'`/`'high'` or 0-9 |
| `url` | `str \| None` | `None` | |
| `flagged` | `bool` | `False` | |
| `calendar_id` | `str \| None` | `None` | Defaults to user's default list |

Returns `Reminder`.

### `update_reminder(reminder_id, ...)`

Same fields as `create_reminder` plus `is_completed: bool | None`. Only
fields you explicitly pass are touched. Pass an empty string to **clear**
`notes` or `url`; pass `0` to clear `priority`. Use `None` (default) to
leave a field unchanged.

### `complete_reminder(reminder_id: str) -> Reminder`

Mark a reminder done.

### `uncomplete_reminder(reminder_id: str) -> Reminder`

Re-open a completed reminder.

### `get_reminder(reminder_id: str) -> Reminder`

Fetch one reminder by ID.

### `delete_reminder(reminder_id: str) -> OperationResult`

Permanently delete. Cannot be undone.

### `set_flagged(reminder_id: str, flagged: bool = True) -> Reminder`

Set or clear the ⚑ flag.

## Reminder queries

### `get_reminders(...)`

| Arg | Type | Default | Notes |
|---|---|---|---|
| `due_after` | `str \| None` | `None` | ISO 8601 |
| `due_before` | `str \| None` | `None` | ISO 8601, exclusive |
| `is_completed` | `bool \| None` | `None` | |
| `priority` | `str \| int \| None` | `None` | |
| `calendar_id` | `str \| None` | `None` | |
| `limit` | `int \| None` | `None` | 1-1000 |

Returns `ReminderList`.

### `search_reminders(query: str, limit: int | None = None) -> ReminderList`

Free-text search across titles and notes.

### `get_next_reminder() -> Reminder | OperationResult`

Soonest incomplete reminder with a due date, or an `OperationResult`
indicating none upcoming.

### `get_overdue_reminders(limit: int | None = None) -> ReminderList`

Incomplete reminders with due dates in the past.

### `get_today_reminders(include_completed: bool = False) -> ReminderList`

Reminders due today (00:00 to next-day 00:00, exclusive — no microsecond
hackery).

## Workflow (kanban) tools

The kanban convention is four lists named with a configurable prefix:

| Role | Default list name | Meaning |
|---|---|---|
| `on_deck` | `Claude-On-Deck` | Queued, ready to start |
| `active` | `Claude-Active` | In progress (≤3 items is healthy) |
| `done` | `Claude-Done` | Completed |
| `blocked` | `Claude-Blocked` | Waiting on someone or something |

Override the prefix via `MCP_APPLE_REMINDERS_LIST_PREFIX`.

### `move_reminder_on_deck(reminder_id: str) -> Reminder`
### `move_reminder_active(reminder_id: str) -> Reminder`
### `move_reminder_done(reminder_id: str) -> Reminder`
### `move_reminder_blocked(reminder_id: str) -> Reminder`

Each moves a reminder into the corresponding workflow list. If the list
doesn't exist, raises `WorkflowListMissingError` with a message guiding
you to either create it or set the prefix env var.

### `move_reminder_to_list(reminder_id: str, calendar_id: str) -> Reminder`

Move to an arbitrary list by ID.

### `workflow_status() -> dict`

One-shot kanban snapshot: open-count + top-3 preview for each role. Used
by the `plan_my_day` prompt; cheap enough to call directly.

## Batch operations

### `batch_create_reminders(titles: list[str], calendar_id: str | None = None) -> ReminderList`

Create up to 200 reminders in one call. Ideal for inbox capture from a
brain-dump.

### `batch_complete_reminders(reminder_ids: list[str]) -> ReminderList`

Mark up to 500 reminders done in one call.

### `batch_delete_reminders(reminder_ids: list[str]) -> OperationResult`

Delete up to 500 reminders. Cannot be undone.

## Output models

```python
class Calendar(BaseModel):
    id: str
    name: str
    color: str | None
    is_default: bool
    owner: str | None

class Reminder(BaseModel):
    id: str
    title: str
    completed: bool
    due_date: datetime | None
    notes: str | None
    url: str | None
    priority: int          # 0=None, 1=Low, 5=Medium, 9=High (Apple's UI levels)
    flagged: bool
    list_id: str | None
    created_date: datetime | None
    modified_date: datetime | None

class CalendarList(BaseModel):
    calendars: list[Calendar]
    count: int

class ReminderList(BaseModel):
    reminders: list[Reminder]
    count: int

class OperationResult(BaseModel):
    success: bool
    message: str
    data: dict | None
```
