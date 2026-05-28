# Spec — 002-modernize-and-foundation

> Requirements in EARS notation. Canonical source of truth. `plan.md` and
> `tasks.md` derive from this. Fix the plan when they drift, not the spec.

## Summary

Modernize the mcp-apple-reminders server to current MCP gold-standard
(FastMCP, Resources, Prompts, Sampling, Elicitation, structured outputs,
lifespan), then ship the full P0–P2 capability matrix and the
agent-visibility-plane pilot. End-state: feature parity with
`FradSer/mcp-server-apple-events` plus a unique agent-collaboration story
no other Reminders MCP offers.

Combines what was originally five separate efforts into one coherent
program because they share substrate (the new module layout, the new
ReminderKit bindings, the FastMCP rewrite). Splitting them would force
mid-program seam adjustments.

## Goals

- Adopt FastMCP, MCP 1.27+, and lifespan-managed application context.
- Expose Resources, Prompts, Sampling, Elicitation, progress, structured logging — the protocol features we currently ignore.
- Add calendar lifecycle (`create_calendar`, `delete_calendar`, `update_calendar`) and the `is_default` fix (already shipped in 1.1 prior).
- Bind to private `ReminderKit.framework` via PyObjC for the features EventKit lacks: subtasks (parent + children), `flagged`, tags, sections.
- Bring time-based and location-based alarms online via public EventKit (`EKAlarm`).
- Ship recurrence rules via `EKRecurrenceRule`.
- Add bulk operations and multi-calendar queries.
- Pilot the `Agents-<project>` visibility-plane protocol on top of the new primitives.

## Non-goals

- iOS / iPadOS support — macOS-only, period.
- Calendar (events) support — Reminders only. `FradSer/apple-events` covers events; we don't compete on that axis.
- Public PyPI release of pyremindkit — vendored substrate gets renamed into the server's own package, dropping the third-party-dep theater.
- Re-implementing Reminders.app's UI features that have no API surface (grocery list smart sorting, image attachments are deferred until the binding work is done; revisited at Phase 3.8).
- Cross-platform substrate — we lean into ReminderKit because Pierce explicitly accepted the private-API risk.

## Acceptance criteria (EARS notation)

### Ubiquitous (always true)

- The server shall be built on FastMCP (`from mcp.server.fastmcp import FastMCP`) with `mcp>=1.27`.
- Every tool, resource, and prompt shall be registered via decorator (`@mcp.tool()`, `@mcp.resource()`, `@mcp.prompt()`) — no manual `list_tools()` / `call_tool()` dispatching.
- The application context (`RemindKit`-equivalent, the `ReminderKit` bridge) shall be managed via lifespan and injected into handlers via `Context`.
- Every existing tool's NAME and INPUT SCHEMA shall be preserved bit-for-bit (no client breakage). Output FORMAT may change to structured Pydantic.
- Every reminder returned to a client shall include `parent_reminder_id`, `subtasks: list[str]`, `tags: list[str]`, `flagged: bool` fields populated from ReminderKit (or `None`/`[]`/`false` if unavailable).
- The architecture gate (`make check-architecture`) shall pass without exclusions throughout.

### Event-driven (`when`)

- When `create_calendar` is invoked with a unique name, the system shall create a new reminder calendar in the user's primary source and return it.
- When `create_calendar` is invoked with a duplicate name, the system shall return an error without creating a second calendar.
- When `delete_calendar` is invoked, the system shall delete the calendar and ALL reminders inside it; if `force=false` (default) and the calendar contains reminders, the system shall raise an error listing the count and require `force=true`.
- When `update_calendar` is invoked with `name` or `color`, the system shall update those attributes and return the updated calendar.
- When `create_reminder` is invoked with `parent_reminder_id`, the system shall create the new reminder as a subtask of that parent via ReminderKit, in the parent's calendar.
- When `get_subtasks` is invoked, the system shall return the ordered list of subtask `Reminder` objects.
- When `set_parent` is invoked with a non-null parent ID, the system shall reassign the reminder. With a null parent, it shall detach.
- When `create_reminder` or `update_reminder` is invoked with `flagged=true`, the system shall set the flag via ReminderKit.
- When `update_reminder` is invoked with `tags=[...]`, the system shall replace the tag set via ReminderKit.
- When a bulk operation (`bulk_complete`, `bulk_delete_completed`, `bulk_move`) is invoked over N items, the system shall emit `Context.report_progress` updates at minimum every 10 items.
- When a destructive operation (`delete_calendar`, `bulk_delete_completed`) is invoked, the system shall use `Context.elicit` to confirm with the user before executing.
- When a sampling-driven tool (e.g. `triage_brain_dump`) is invoked, the system shall call back to the client LLM via `ctx.session.create_message` and return the structured triage result.
- When the server starts a session and `Agents-<project>` does not yet exist (and the visibility-plane is enabled), the system shall auto-create it.

### State-driven (`while`)

- While the lifespan context is active, exactly one `ReminderKit` (the EventKit + ReminderKit bridge) instance shall exist; tools shall not instantiate their own.
- While the `Agents-<project>` visibility-plane is enabled, the server shall mirror the agent's active `TodoWrite` items into the corresponding reminder list within 5s of any change. (Stretch goal — Phase 4.)

### Unwanted-behavior (`if`/`then`)

- If the ReminderKit private framework fails to load at startup, then the server shall log a stderr warning and degrade — flagged/tags/subtasks tools return an `Error: ReminderKit unavailable` message, but EventKit-backed tools continue to work.
- If a tool receives a `parent_reminder_id` AND a `calendar_id` whose calendars do not match, then the system shall reject with `ValueError("parent_reminder_id and calendar_id specify different calendars.")`.
- If `delete_calendar` is invoked on the user's default calendar, then the system shall reject (you can't delete the default).
- If a Pydantic model validation fails on a structured tool output, then the system shall surface the validation error to the client (not silently coerce).

### Optional (`where`)

- Where the caller passes a `color` argument to `create_calendar` or `update_calendar`, the system shall accept the 8 named palette colors (red, orange, yellow, green, blue, purple, brown, gray) or a `#rrggbb` hex string.
- Where the caller passes `recurrence` to `create_reminder`, the system shall set up an `EKRecurrenceRule` per the supplied frequency / interval / end condition.
- Where the caller passes `alarm` to `create_reminder` with an absolute date OR a relative offset, the system shall attach an `EKAlarm`.
- Where the caller passes `location_alarm` to `create_reminder` with a location + proximity (`enter` | `leave`), the system shall attach a geofence `EKAlarm`.
- Where the agent-visibility-plane is enabled (per `VIBE.yaml::agents.visibility_plane.enabled`), the server shall expose the `bootstrap_agent_list` tool and the `agents://current` resource.

## Success metrics

- Every existing test still passes. (Backwards-compatible refactor.)
- 22 → 35+ tools after Phase 3. Tool count is not the goal; coverage is.
- 0 hand-formatted text outputs after Phase 0.4 (everything goes through Pydantic).
- 0 `print(..., file=sys.stderr)` calls in tool handlers after Phase 0.5 (replaced by `Context` logging).
- An agent running this server can create an `Agents-<project>` list, populate it with phased work as parent + subtasks, mark them done, and have the user see all of it in Reminders.app in real time.
- `make check-architecture` stays green throughout (no exclusions ever).

## Open questions

- **ReminderKit PyObjC binding ergonomics** — PyObjC does NOT auto-discover private framework classes. We have to load the binary explicitly (`objc.loadBundle(...)` or `NSBundle.bundleWithPath_(...)`) and then access `REMReminder` etc. by name. Pattern verified in `BRO3886/rem` — need to port the technique.
- **`EKRecurrenceRule` end-condition shapes** — count-based vs date-based vs forever. Tooling shape decided at Phase 3.3 design time.
- **Sampling vs Elicitation for "auto-sort brain dump"** — sampling lets the server call back into the client's LLM autonomously; elicitation pauses for structured user input. Probably want both. Decided at Phase 2.5 design time.

## References

- Capability-gap audit (May 2026 session): `AGENTS.md §9`, `MAP.md`, this conversation transcript.
- Pierce's visibility-plane protocol design notes (in-conversation, May 2026).
- Competitor benchmark: `FradSer/mcp-server-apple-events` (122★, 16 releases, 533 commits) — feature surface we aim to match + exceed.
- ReminderKit bindings prior art: `BRO3886/rem` (Swift CLI), `xybp888/iOS-Header/.../ReminderKit.framework/` (header dump).
- MCP spec revision **2025-11-25** (current).
- MCP Python SDK PyPI **1.27.1** (May 8, 2026).
- Archived predecessor: `specs/_archive/001-visibility-foundation/`.
