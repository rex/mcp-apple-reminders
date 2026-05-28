# Spec — 001-visibility-foundation

> Requirements in EARS notation. This file is the canonical source of truth.
> Plan and tasks derive from it. When they drift, fix the plan, not the spec.

## Summary

Add the three minimum-viable MCP capabilities required to pilot the
"Agents-`<project>`" visibility-plane protocol (May 2026 design): a corrected
default-calendar reporter, a `create_calendar` tool, and Apple-Reminders
subtask (parent-reminder) support. Once shipped, an agent in any repo can spin
up its own per-project task list and structure phased work as a parent
reminder with subtask children — the dashboard view that drives the entire
collaboration model.

## Goals

- Agents can create a new reminder list (`Agents-<project>`) programmatically without the user opening Reminders.app.
- Agents can attach subtasks to a parent reminder so phased work has native hierarchy (no title-prefix `[Phase N]` hack).
- `list_calendars` reports exactly one calendar as `Default: Yes`, the EventKit-declared default.

## Non-goals

- `delete_calendar` and `update_calendar` (rename / recolor) — P1, separate spec.
- `flagged` setter on `create_reminder` / `update_reminder` — P1.
- Recurrence rules, alarms (time- or location-based) — P2.
- Bulk operations (`bulk_complete`, `bulk_delete_completed`) — P1.
- Real-time change-notification observer — P3.
- The visibility-plane protocol itself (AGENTS.md rule, per-session bootstrap) — separate spec, depends on this one shipping.

## Acceptance criteria (EARS notation)

### Ubiquitous

- The system shall expose a `create_calendar` MCP tool that creates a new Reminders list with the given name.
- The system shall include `parent_reminder_id: Optional[str]` and `subtasks: list[str]` fields on every `Reminder` value returned to clients.
- The `Calendar.is_default` field shall be `True` for exactly one calendar in `list_calendars` output — the one returned by `EKEventStore.defaultCalendarForNewReminders()`.

### Event-driven (`when`)

- When `create_calendar` is invoked with a name that already exists, the system shall return an error indicating the duplicate without creating a second list.
- When `create_reminder` is invoked with `parent_reminder_id`, the system shall create the new reminder as a subtask of the specified parent in the parent's calendar.
- When `get_reminder` is invoked for a reminder that has subtasks, the system shall include the subtask IDs in the response.
- When `get_subtasks` is invoked for a reminder, the system shall return the list of subtask `Reminder` objects in their stored order.
- When `set_parent` is invoked with a non-null parent ID, the system shall reassign the reminder under that parent.
- When `set_parent` is invoked with a null parent ID, the system shall detach the reminder from its current parent (promoting it to a top-level reminder in its calendar).

### Unwanted-behavior (`if`/`then`)

- If `create_calendar` is invoked on an EventKit source that does not support reminder calendars, then the system shall return an error rather than silently creating into a wrong source.
- If `create_reminder` is invoked with `parent_reminder_id` AND `calendar_id` where the parent's calendar differs from the supplied calendar, then the system shall reject with a validation error (a subtask cannot live in a different calendar than its parent).
- If `set_parent` is invoked with a parent_reminder_id that doesn't exist, then the system shall raise a not-found error and not modify the reminder.

### Optional (`where`)

- Where the caller passes a `color` argument to `create_calendar`, the system shall set the new calendar's color to the named value (red, orange, yellow, green, blue, purple, brown, custom hex). Otherwise the calendar uses the system default for its source.

## Success metrics

- An agent in any repo can run `create_calendar(name="Agents-foo")` and `list_calendars` returns the new list within 2s.
- `list_calendars` returns exactly one calendar with `Default: Yes` (matches `get_default_calendar` output).
- An agent can build a 3-reminder workflow (parent: "Phase 1: refactor"; subtasks: "Slice 1.1", "Slice 1.2", "Slice 1.3") and `get_subtasks` returns all three in order.

## Open questions

- macOS's subtask API stability — `EKReminder` exposes subtasks via the iOS 17 / macOS 14 hierarchy APIs, but PyObjC binding completeness needs verification at implementation time. Fallback: store parent_reminder_id in notes as a `[parent: <uuid>]` prefix and reconstruct on read. Decided in design.md.
- Color encoding — EventKit takes `NSColor` / `CGColor`; we need a string-name-to-NSColor mapping. Standard 8-color palette matches Reminders.app's color picker.

## References

- Capability-gap audit (May 2026 session): `AGENTS.md §9`, `MAP.md`, and the chat transcript that produced this spec.
- Pierce's visibility-plane protocol design notes (in-conversation, May 2026).
- pyremindkit upstream commit `d960eaa` (`libs/pyremindkit/VENDOR.md`).
