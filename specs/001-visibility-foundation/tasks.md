# Tasks — 001-visibility-foundation

> Concrete task list. One task per slice. Implementers execute from here.
> TASK_STATE.md tracks the ACTIVE slice; this file is the full catalog.

## How to use this file

- Check off each acceptance bullet as it lands.
- Add `(agent: <name>)` when an agent picks up a task.
- Add `(blocked: <reason>)` if a task blocks.
- Each acceptance bullet is EARS-notation from `spec.md`.

## Phase 1 — P0 capabilities

### S1.1 — Fix `is_default` in `CalendarManager.list()`

- **Files**: `libs/pyremindkit/src/pyremindkit/calendars.py` (edit), `test_crud_calendars.py` (extend)
- **Files (do NOT edit)**: `libs/pyremindkit/src/pyremindkit/models.py`, `libs/pyremindkit/src/pyremindkit/_internal.py`
- **Acceptance**:
  - [ ] The `is_default` field shall be `True` for exactly one calendar in `list_calendars` output — the one returned by `EKEventStore.defaultCalendarForNewReminders()`.
  - [ ] `mem:core` and `AGENTS.md §9` are updated to remove the bug note.
  - [ ] Test: extend `test_calendar_operations` to assert exactly one `is_default == True` across `list()` output and that ID equals `get_default().id`.
  - [ ] `make check-architecture` green.
- [ ] Complete

### S1.2 — `CalendarManager.create()` + `create_calendar` MCP tool

- **Files**: `libs/pyremindkit/src/pyremindkit/calendars.py` (add method), `src/mcp_apple_reminders/tools/calendars.py` (add tool + handler), `test_crud_calendars.py` (add tests)
- **Files (do NOT edit)**: `models.py` (frozen), `_internal.py`
- **Acceptance**:
  - [ ] The system shall expose a `create_calendar` MCP tool that creates a new Reminders list with the given name. (spec §Ubiquitous)
  - [ ] When `create_calendar` is invoked with a name that already exists, the system shall return an error indicating the duplicate without creating a second list. (spec §Event-driven)
  - [ ] If `create_calendar` is invoked on an EventKit source that does not support reminder calendars, then the system shall return an error rather than silently creating into a wrong source. (spec §Unwanted-behavior)
  - [ ] Where the caller passes a `color` argument, the system shall set the new calendar's color from the named palette. (spec §Optional)
  - [ ] Test: create + verify + delete in `test_crud_calendars` (delete is manual cleanup until S2.1 ships `delete_calendar`; use `osascript` cleanup for now).
  - [ ] `make check-architecture` green.
- [ ] Complete

### S1.3 — Extend `Reminder` + `_convert_ek_reminder_to_reminder` for parent / subtasks

- **Files**: `libs/pyremindkit/src/pyremindkit/models.py` (extend NamedTuple), `libs/pyremindkit/src/pyremindkit/_internal.py` (update converter), `src/mcp_apple_reminders/formatting.py` (extend `format_reminder` to display Parent + Subtasks count)
- **Files (do NOT edit)**: `calendars.py`, `core.py` (in this slice; next slice extends them)
- **Acceptance**:
  - [ ] The system shall include `parent_reminder_id: Optional[str]` and `subtasks: list[str]` fields on every Reminder value returned to clients. (spec §Ubiquitous)
  - [ ] When `get_reminder` is invoked for a reminder that has subtasks, the system shall include the subtask IDs in the response. (spec §Event-driven)
  - [ ] PyObjC binding presence for `setParentReminder_` / `parentReminder` / `subtasks` is documented in `_internal.py` comments; if absent, the notes-prefix fallback is wired and a one-time stderr warning fires.
  - [ ] Test: `test_crud_reminders` extended with "create reminder; assert parent_reminder_id is None and subtasks == []" to verify the new fields surface for the simple case.
  - [ ] `make check-architecture` green.
- [ ] Complete

### S1.4 — Extend `create_reminder` for `parent_reminder_id`; add `get_subtasks` + `set_parent`

- **Files**: `libs/pyremindkit/src/pyremindkit/core.py` (extend `create_reminder`, add `get_subtasks`, add `set_parent`), `libs/pyremindkit/src/pyremindkit/calendars.py` (extend `Calendar.create_reminder` to forward parent), `src/mcp_apple_reminders/tools/reminders.py` (extend create_reminder schema; add set_parent tool), `src/mcp_apple_reminders/tools/queries.py` (add get_subtasks tool), `test_crud_reminders.py` and/or new `test_subtasks.py`
- **Files (do NOT edit)**: `models.py` (frozen now)
- **Acceptance**:
  - [ ] When `create_reminder` is invoked with `parent_reminder_id`, the system shall create the new reminder as a subtask of the specified parent in the parent's calendar. (spec §Event-driven)
  - [ ] When `get_subtasks` is invoked for a reminder, the system shall return the list of subtask Reminder objects in their stored order. (spec §Event-driven)
  - [ ] When `set_parent` is invoked with a non-null parent ID, the system shall reassign the reminder under that parent. (spec §Event-driven)
  - [ ] When `set_parent` is invoked with a null parent ID, the system shall detach the reminder from its current parent. (spec §Event-driven)
  - [ ] If `create_reminder` is invoked with `parent_reminder_id` AND `calendar_id` where the parent's calendar differs, then the system shall reject with a validation error. (spec §Unwanted-behavior)
  - [ ] If `set_parent` is invoked with a parent_reminder_id that doesn't exist, then the system shall raise a not-found error and not modify the reminder. (spec §Unwanted-behavior)
  - [ ] Test: a new `test_subtasks.py` module that creates a parent, three children, lists subtasks, reparents one child, detaches another, verifies state, and cleans up.
  - [ ] `make check-architecture` green.
- [ ] Complete

## Phase 2 — P1 capabilities (deferred)

(See `plan.md` §Phase 2. Tasks expanded when Phase 1 lands.)

## Phase 3 — P2 capabilities (deferred)

(See `plan.md` §Phase 3.)

## Phase 4 — P3 capabilities + visibility-plane pilot (deferred)

(See `plan.md` §Phase 4.)

## Done when

- [ ] All Phase 1 acceptance bullets checked.
- [ ] `make check-architecture` green (no new oversized files).
- [ ] `make check-if-the-agent-can-consider-this-task-completed` green (or stub-gates noted as expected fails).
- [ ] No open blockers in `TASK_STATE.md` §3.
- [ ] AGENTS.md §9 reflects the `is_default` bug being fixed (or kept-and-tracked if PyObjC blocks).
- [ ] Capability-gap audit (in `mem:core` and PROGRESS.md) updated to reflect P0 → ✓.
