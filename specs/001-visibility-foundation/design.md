# Design — 001-visibility-foundation

> How we satisfy `spec.md`. Each design decision references the spec section
> that justifies it.

## Architecture overview

```
MCP client (Claude Code / Codex / Claude Desktop)
    ↓
src/mcp_apple_reminders/tools/calendars.py    (new: create_calendar)
src/mcp_apple_reminders/tools/reminders.py    (extended: parent_reminder_id arg)
src/mcp_apple_reminders/tools/queries.py      (new: get_subtasks, set_parent)
    ↓
libs/pyremindkit/src/pyremindkit/
    core.py            (extended: RemindKit.update_reminder accepts parent_reminder_id)
    calendars.py       (new: CalendarManager.create, fixed: is_default lookup)
    models.py          (extended: Reminder gets parent_reminder_id + subtasks fields)
    _internal.py       (extended: _convert_ek_reminder_to_reminder reads parent + children)
    ↓
EventKit (macOS framework)
    ├── EKEventStore.saveCalendar:commit:error:        (calendar creation)
    ├── EKEventStore.defaultCalendarForNewReminders    (is_default ground truth)
    ├── EKReminder.parentReminder / setParentReminder: (subtask wiring; iOS 17+/macOS 14+)
    └── EKEventStore.fetchRemindersMatchingPredicate:  (subtask listing via parent filter)
```

## Components

### `CalendarManager.create(name, color=None) -> Calendar`

- **Responsibility**: Create a new reminder calendar in the user's primary source (iCloud if present, else Local).
- **Inputs**: `name: str` (required), `color: Optional[str]` (8-color palette name).
- **Outputs**: The newly-created `Calendar` dataclass instance.
- **Dependencies**: `EKEventStore.sources`, `EKCalendar.calendarForEntityType:eventStore:`, `EKEventStore.saveCalendar:commit:error:`.
- **Satisfies**: spec §Ubiquitous (create_calendar tool), §Event-driven (duplicate-name handling), §Unwanted-behavior (unsupported source), §Optional (color).

### `CalendarManager.list()` — `is_default` fix

- **Responsibility**: Correctly identify the default calendar.
- **Change**: replace `is_default=calendar.isImmutable()` with `is_default=(calendar.calendarIdentifier() == default_id)`, where `default_id` is captured once at the top of the method from `event_store.defaultCalendarForNewReminders()`.
- **Satisfies**: spec §Ubiquitous (exactly one calendar reports Default: Yes).

### `Reminder` extension (in `models.py`)

- **Responsibility**: Expose parent / subtask relationships to MCP clients.
- **Change**: Add two fields at the END of the NamedTuple (preserving positional-unpacking compatibility for the existing 11 fields):
  ```python
  parent_reminder_id: Optional[str]  # None if top-level
  subtasks: list[str]                # ordered list of child reminder IDs; empty if none
  ```
- **Satisfies**: spec §Ubiquitous (parent_reminder_id + subtasks on every Reminder), §Event-driven (get_reminder surfaces subtask IDs).

### `_convert_ek_reminder_to_reminder` (in `_internal.py`)

- **Responsibility**: Read parent + children from EventKit and populate the new fields.
- **Implementation**:
  - `parent_reminder_id`: `ek_reminder.parentReminder().calendarItemIdentifier() if ek_reminder.parentReminder() else None`. PyObjC binding presence MUST be verified at implementation time (see Open Question in spec).
  - `subtasks`: iterate `ek_reminder.subtasks()` if available; otherwise empty list.
- **Fallback**: If `parentReminder` / `subtasks` methods are missing from the PyObjC bridge, encode parent in notes as a `\n[parent: <uuid>]` line and reconstruct on read. This fallback is documented in `_internal.py` with a TODO and a runtime warning to stderr.

### `RemindKit.create_reminder` extension

- **Responsibility**: Accept a `parent_reminder_id` argument and wire the new reminder under the parent.
- **Change**: After `EKReminder.reminderWithEventStore_(...)` and before save, if `parent_reminder_id` is supplied: resolve the parent via `event_store.calendarItemWithIdentifier_(parent_reminder_id)`, raise `ValueError` if not found, then call `new_reminder.setParentReminder_(parent_ek)`. Use the parent's calendar — IGNORE `calendar_id` if it differs (the spec §Unwanted-behavior says reject; we reject with `ValueError`).
- **Satisfies**: spec §Event-driven (subtask creation), §Unwanted-behavior (calendar mismatch).

### `RemindKit.get_subtasks(reminder_id) -> Generator[Reminder]` (new)

- **Responsibility**: Stream the subtasks of a parent reminder.
- **Implementation**: Resolve parent via `calendarItemWithIdentifier_`, return `[_convert(child) for child in parent.subtasks()]`.

### `RemindKit.set_parent(reminder_id, parent_id | None) -> Reminder` (new)

- **Responsibility**: Reassign or detach a reminder's parent.
- **Implementation**: Look up both reminders; call `child.setParentReminder_(parent_ek)` (or `setParentReminder_(None)` for detach); save; return converted child.

### MCP tools (in `tools/calendars.py`, `tools/reminders.py`, `tools/queries.py`)

| Tool | Module | Schema | Handler |
|---|---|---|---|
| `create_calendar` | calendars.py | `{name: string, color?: string}` | `_handle_create_calendar` |
| `create_reminder` (extended) | reminders.py | add `parent_reminder_id?: string` | `_handle_create_reminder` (modify) |
| `get_subtasks` | queries.py | `{reminder_id: string}` | `_handle_get_subtasks` |
| `set_parent` | reminders.py | `{reminder_id: string, parent_reminder_id?: string \| null}` | `_handle_set_parent` |

## Data model

### Changed types

- `Reminder` NamedTuple — append `parent_reminder_id: Optional[str]` and `subtasks: list[str]` after `flagged`. Total field count goes from 11 → 13. Positional unpacking of the first 11 fields stays compatible.

### EventKit-level data

No changes — relies on existing EKReminder.parentReminder and EKReminder.subtasks (when available in PyObjC; fallback discussed above).

## API surface (MCP tools)

### New tools

- **`create_calendar`** — `{name: string, color?: "red"|"orange"|"yellow"|"green"|"blue"|"purple"|"brown"|<hex>}`. Returns the new `Calendar` block.
- **`get_subtasks`** — `{reminder_id: string}`. Returns a numbered list of `Reminder` blocks.
- **`set_parent`** — `{reminder_id: string, parent_reminder_id?: string | null}`. Returns the updated `Reminder`.

### Changed tools

- **`create_reminder`** — adds `parent_reminder_id?: string`. If supplied, the parent's calendar is used (any `calendar_id` argument MUST match the parent's calendar or the call rejects).
- **`get_reminder`** — output now includes `Parent: <id-or-(none)>` and `Subtasks: <count>` lines via the extended `format_reminder` helper.

## Contracts (freeze in Phase 1, Slice 1.1)

```python
# models.py (frozen field order)
class Reminder(NamedTuple):
    id: str
    title: str
    due_date: Optional[datetime]
    notes: Optional[str]
    completed: bool
    url: Optional[str]
    priority: int
    list_id: str
    created_date: Optional[datetime]
    modified_date: Optional[datetime]
    flagged: bool
    parent_reminder_id: Optional[str]   # NEW — added at tail, do not reorder
    subtasks: list[str]                 # NEW — added at tail, do not reorder
```

MCP tool names and schemas (above) are also frozen after Phase 1.

## Error handling

| Condition | Behavior | Where raised |
|---|---|---|
| `create_calendar` with duplicate name | `ValueError("Calendar named 'X' already exists.")` | `CalendarManager.create` |
| `create_calendar` on unsupported source | `RuntimeError("Source 'X' does not support reminders.")` | `CalendarManager.create` |
| `create_reminder` parent doesn't exist | `ValueError("Parent reminder 'X' not found.")` | `RemindKit.create_reminder` |
| `create_reminder` parent/calendar mismatch | `ValueError("parent_reminder_id and calendar_id specify different calendars.")` | `RemindKit.create_reminder` |
| `set_parent` parent doesn't exist | `ValueError("Reminder 'X' not found.")` | `RemindKit.set_parent` |
| EventKit save failure | `RuntimeError` (existing pattern) | `_save_ek_reminder` |

All errors surface to MCP clients via the existing `server.py::call_tool` translator (ValueError → `Error: <message>`, other → `Error executing <name>: ...`).

## Observability

- No metrics framework in this server yet — out of scope.
- Diagnostic prints go to stderr (existing rule); new tools follow the same pattern.
- The PyObjC binding-presence check in `_internal.py` emits a one-time stderr warning if `parentReminder` is missing and the fallback path activates.

## Security considerations

- No auth changes — Reminders permission is the only gate; already established.
- Calendar creation can pollute the user's Reminders.app sidebar; we mitigate by surfacing the name in the duplicate-error case rather than silently creating a second list. There is no quota / rate limit; agents are trusted.

## Performance considerations

- `get_subtasks` is `O(N_subtasks)` — fine.
- The `is_default` fix adds one EventKit call per `list()` invocation (cache the default ID at the top of the method, not per-calendar). Single extra round-trip.
- Subtask enumeration in `_convert_ek_reminder_to_reminder` is now called per reminder — concern if a calendar has 1000+ reminders. Mitigation: subtasks list is a property access on `EKReminder`, not a refetch. Should be cheap.

## Alternatives considered

### Encode parent in notes (`[parent: <uuid>]`)

- **Why considered**: Avoids dependency on PyObjC binding for `setParentReminder_`. Works across all macOS versions.
- **Why rejected**: Pollutes user-visible notes field. Doesn't show up as hierarchy in Reminders.app UI. Breaks Apple's first-class subtask UX.
- **Kept as fallback**: If PyObjC binding is missing for `setParentReminder_`, the fallback activates. Documented in code with a stderr warning.

### Submodule pyremindkit instead of vendor

- **Why considered**: Easier upstream sync.
- **Why rejected**: Already vendor-flattened in the refactor commit (`1fc2ab4` + `912bdf7`). Not revisiting.

### Add `flagged` to Phase 1 scope

- **Why considered**: Same touchpoint as the other `create_reminder`/`update_reminder` edits.
- **Why rejected**: Pierce explicitly scoped Phase 1 to the 3 P0 items (is_default, create_calendar, subtasks). `flagged` is P1.

## Open design questions

- **PyObjC `setParentReminder_` availability** — confirmed at first slice implementation, before contracts freeze. If missing, the fallback path becomes the primary path and the stderr warning is removed (since it's expected, not exceptional).
