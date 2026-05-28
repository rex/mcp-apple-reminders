# Spec — 002-modernize-and-foundation

> Requirements in EARS notation. Canonical source of truth. `plan.md` and
> `tasks.md` derive from this. Fix the plan when they drift, not the spec.

## Summary

Modernize the mcp-apple-reminders server to current MCP gold-standard
(FastMCP, Resources, Prompts, Sampling, Elicitation, structured outputs,
lifespan), pivot to a RemCTL-style three-tier native architecture
(direct SQLite reads + Swift EventKit write helper + Objective-C
ReminderKit write helper), then ship the full P0–P2 capability matrix
and the agent-visibility-plane pilot. End-state: feature parity with
`FradSer/mcp-server-apple-events` and `viticci/remctl` plus a unique
agent-collaboration story no other Reminders MCP offers.

Combines what was originally five separate efforts into one coherent
program because they share substrate (the new module layout, the
native-helper build pipeline, the FastMCP rewrite, the deeplink data
model). Splitting them would force mid-program seam adjustments.

## Goals

- Adopt FastMCP, MCP 1.27+, and lifespan-managed application context.
- Expose Resources, Prompts, Sampling, Elicitation, progress, structured logging — the protocol features we currently ignore.
- **Adopt RemCTL's proven three-tier native architecture**:
  1. **Reads** — direct SQLite query of `~/Library/Group Containers/group.com.apple.reminders/Container_v1/Stores/Data-*.sqlite`. Exposes sections, subtasks, tags, attachments, alarms metadata, recurrence metadata in tens of milliseconds.
  2. **Public writes** — Swift subprocess helper (`_native/bin/rem_eventkit`) wrapping EventKit. Borrowed from `viticci/remctl::remctl-bridge.swift` (MIT) with attribution.
  3. **Private writes** — Objective-C subprocess helper (`_native/bin/rem_reminderkit`) wrapping ReminderKit. Borrowed from `viticci/remctl::remctl-private.m` (MIT) with attribution.
- Add calendar lifecycle (`create_calendar`, `delete_calendar`, `update_calendar`) and the `is_default` fix (already shipped in S1.1).
- Surface subtasks, `flagged`, tags, sections — through the SQLite reader for reads, through the Obj-C helper for writes.
- Bring time-based and location-based alarms online via public EventKit (`EKAlarm`).
- Ship recurrence rules via `EKRecurrenceRule`.
- Add bulk operations and multi-calendar queries.
- **Every `Reminder` and `Calendar` response includes a `deeplink` field** — `x-apple-reminderkit://REMCDReminder/<uuid>` or `x-apple-reminderkit://REMCDList/<uuid>` — that opens the entity in Reminders.app.
- Pilot the `Agents-<project>` visibility-plane protocol on top of the new primitives.

## Non-goals

- iOS / iPadOS support — macOS-only, period.
- Calendar (events) support — Reminders only. `FradSer/apple-events` covers events; we don't compete on that axis.
- Public PyPI release of pyremindkit — vendored substrate gets renamed into the server's own package, dropping the third-party-dep theater.
- Re-implementing Reminders.app's UI features that have no API surface (grocery list smart sorting, image attachments are surface-level — full editing surface deferred to Phase 3.X).
- Cross-platform substrate — we lean into the three-tier native stack because Pierce explicitly accepted the private-API risk.

## Acceptance criteria (EARS notation)

### Ubiquitous (always true)

- The server shall be built on FastMCP (`from mcp.server.fastmcp import FastMCP`) with `mcp>=1.27`.
- Every tool, resource, and prompt shall be registered via decorator (`@mcp.tool()`, `@mcp.resource()`, `@mcp.prompt()`) — no manual `list_tools()` / `call_tool()` dispatching.
- The application context (the unified `Bridge` over SQLite + EventKit helper + ReminderKit helper) shall be managed via lifespan and injected into handlers via `Context`.
- Every existing tool's NAME and INPUT SCHEMA shall be preserved bit-for-bit (no client breakage). Output FORMAT may change to structured Pydantic.
- Every `Reminder` returned to a client shall include `parent_reminder_id`, `subtasks: list[str]`, `tags: list[str]`, `section_name: str | None`, `flagged: bool`, `deeplink: str` (`x-apple-reminderkit://REMCDReminder/{id}`) fields.
- Every `Calendar` returned to a client shall include a `deeplink: str` field (`x-apple-reminderkit://REMCDList/{id}`).
- Reads shall be served from the local SQLite store as the primary path; EventKit-mediated reads are a fallback when the SQLite path errors.
- Public-API writes (create / update / delete reminders, calendar lifecycle, alarms, recurrence) shall be dispatched to the Swift EventKit helper subprocess.
- Private-API writes (subtasks, tags, sections, flagged, attachments) shall be dispatched to the Objective-C ReminderKit helper subprocess. If the helper fails to launch, the server shall degrade — the affected tools return `Error: ReminderKit helper unavailable` — while other tools continue to work.
- The architecture gate (`make check-architecture`) shall pass without exclusions throughout. Native helper sources (`*.swift`, `*.m`) live under `_native/` and are excluded from the Python line-count gate because they aren't Python (the gate's scope is Python source).
- Borrowed code from `viticci/remctl` shall carry MIT-license attribution in `_native/THIRD_PARTY_NOTICES.md` and in inline file headers.

### Event-driven (`when`)

- When `create_calendar` is invoked with a unique name, the system shall create a new reminder calendar in the user's primary source and return it with its `deeplink`.
- When `create_calendar` is invoked with a duplicate name, the system shall return an error without creating a second calendar.
- When `delete_calendar` is invoked with `force=false` and the calendar contains reminders, the system shall raise an error listing the count and require `force=true`. With `force=true` it shall delete the calendar and all reminders inside.
- When `update_calendar` is invoked with `name` or `color`, the system shall update those attributes via the Swift EventKit helper and return the updated calendar.
- When `create_reminder` is invoked with `parent_reminder_id`, the system shall create the new reminder as a subtask of that parent via the ReminderKit helper, in the parent's calendar.
- When `get_subtasks` is invoked, the system shall return the ordered list of subtask `Reminder` objects.
- When `set_parent` is invoked with a non-null parent ID, the system shall reassign via the ReminderKit helper. With a null parent, it shall detach.
- When `create_reminder` or `update_reminder` is invoked with `flagged=true`, the system shall set the flag via the ReminderKit helper.
- When `update_reminder` is invoked with `tags=[...]`, the system shall replace the tag set via the ReminderKit helper.
- When `assign_section` is invoked with a `reminder_id` + `section_name`, the system shall move that reminder into the named section via the ReminderKit helper.
- When a bulk operation (`bulk_complete`, `bulk_delete_completed`, `bulk_move`) is invoked over N items, the system shall emit `Context.report_progress` updates at minimum every 10 items.
- When a destructive operation (`delete_calendar`, `bulk_delete_completed`) is invoked, the system shall use `Context.elicit` to confirm with the user before executing.
- When a sampling-driven tool (e.g. `triage_brain_dump`) is invoked, the system shall call back to the client LLM via `ctx.session.create_message` and return the structured triage result.
- When the server starts a session and `Agents-<project>` does not yet exist (and the visibility-plane is enabled), the system shall auto-create it.

### State-driven (`while`)

- While the lifespan context is active, exactly one `Bridge` instance shall exist; tools shall not instantiate their own SQLite connection or helper subprocess.
- While the `Agents-<project>` visibility-plane is enabled, the server shall mirror the agent's active `TodoWrite` items into the corresponding reminder list within 5s of any change. (Stretch goal — Phase 4.)

### Unwanted-behavior (`if`/`then`)

- If the SQLite file is not present (Reminders.app never opened), then the SQLite reader shall raise `RemindersDBUnavailable`; tools degrade to EventKit-mediated reads.
- If the Swift EventKit helper subprocess fails to launch or returns non-zero, then the server shall log via `Context.error` and the calling tool shall return a structured error to the client. Other tools continue.
- If the Objective-C ReminderKit helper subprocess fails to launch, then the tools dependent on it (`set_parent`, `set_flagged`, `set_tags`, `assign_section`, subtask create) return `Error: ReminderKit helper unavailable`; the SQLite reader and EventKit-backed paths continue.
- If a tool receives a `parent_reminder_id` AND a `calendar_id` whose calendars do not match, then the system shall reject with `ValueError("parent_reminder_id and calendar_id specify different calendars.")`.
- If `delete_calendar` is invoked on the user's default calendar, then the system shall reject (you can't delete the default).
- If a Pydantic model validation fails on a structured tool output, then the system shall surface the validation error to the client (not silently coerce).

### Optional (`where`)

- Where the caller passes a `color` argument to `create_calendar` or `update_calendar`, the system shall accept the 8 named palette colors (red, orange, yellow, green, blue, purple, brown, gray) or a `#rrggbb` hex string.
- Where the caller passes `recurrence` to `create_reminder`, the system shall set up an `EKRecurrenceRule` per the supplied frequency / interval / end condition.
- Where the caller passes `alarm` to `create_reminder` with an absolute date OR a relative offset, the system shall attach an `EKAlarm`.
- Where the caller passes `location_alarm` to `create_reminder` with a location + proximity (`enter` | `leave`), the system shall attach a geofence `EKAlarm`.
- Where the caller passes `early_reminder` (macOS 26 feature) to `create_reminder`, the system shall set the early-reminder timing via the ReminderKit helper.
- Where the agent-visibility-plane is enabled (per `VIBE.yaml::agents.visibility_plane.enabled`), the server shall expose the `bootstrap_agent_list` tool and the `agents://current` resource.

## Success metrics

- Every existing test still passes. (Backwards-compatible refactor.)
- 22 → 38+ tools after Phase 3.
- 0 hand-formatted text outputs after Phase 0.4 (everything goes through Pydantic).
- 0 `print(..., file=sys.stderr)` calls in tool handlers after Phase 0.5 (replaced by `Context` logging).
- `list_calendars` and `get_reminders` (no filter) latency under 50ms cold, under 10ms warm (SQLite-served).
- An agent running this server can create an `Agents-<project>` list, populate it with phased work as parent + subtasks, mark them done, and have the user see all of it in Reminders.app in real time. Every response includes a `deeplink` that opens the entity in the app.
- `make check-architecture` stays green throughout (no exclusions ever).

## Open questions

- **SQLite schema stability across macOS releases** — Reminders.app's Core Data schema has been stable for years, but no guarantee. Mitigation: schema version detection + a thin SchemaShim layer in `_native/sqlite.py`. Decided at S1.0 design time.
- **`x-apple-reminderkit://` UUID resolution** — verify that EventKit's `calendarItemIdentifier` matches the `REMCDReminder/<uuid>` segment used in deeplinks. If they diverge, we resolve via SQLite at read time. Tested at S0.3 model time.
- **ReminderKit helper ABI** — RemCTL's `remctl-private.m` accepts JSON over stdin and emits JSON to stdout. We need to confirm we can use the same protocol verbatim or whether we wrap it. Decided at S1.4 borrow-and-port time.

## References

- Capability-gap audit (May 2026 session): `AGENTS.md §9`, `MAP.md`, this conversation transcript.
- Pierce's visibility-plane protocol design notes (in-conversation, May 2026).
- Competitor benchmark: `FradSer/mcp-server-apple-events` (122★, 16 releases, 533 commits) — feature surface we aim to match + exceed.
- **Primary reference implementation: `viticci/remctl` (40★, MIT, actively maintained as of 2026-05-26)** — three-tier architecture, SQLite reads + EventKit Swift helper + ReminderKit Obj-C helper. We borrow `remctl-private.m` and `remctl-bridge.swift` with attribution.
- Header dump for ReminderKit class layout: `xybp888/iOS-Header/.../ReminderKit.framework/`.
- MCP spec revision **2025-11-25** (current).
- MCP Python SDK PyPI **1.27.1** (May 8, 2026).
- Archived predecessor: `specs/_archive/001-visibility-foundation/`.
