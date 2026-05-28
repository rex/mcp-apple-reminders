# Design — 002-modernize-and-foundation

> How we satisfy `spec.md`. Section references are to spec.md.

## Architecture overview

```
MCP client (Claude Code / Codex / Claude Desktop)
    ↓
src/mcp_apple_reminders/server.py            (FastMCP instance, lifespan, transport)
    ↓
src/mcp_apple_reminders/tools/*.py           (@mcp.tool() decorators)
src/mcp_apple_reminders/resources/*.py       (@mcp.resource() decorators)         NEW
src/mcp_apple_reminders/prompts/*.py         (@mcp.prompt() decorators)           NEW
src/mcp_apple_reminders/models.py            (Pydantic schemas, structured I/O)   NEW
    ↓
src/mcp_apple_reminders/_native/             (renamed from libs/pyremindkit/)     RENAMED
    eventkit.py        — public EventKit bridge (RemindKit, Calendar, CalendarManager, Reminder)
    reminderkit.py     — private ReminderKit bridge (subtasks, flagged, tags)     NEW
    bridge.py          — unified facade combining the two                          NEW
    models.py          — Priority enum, Reminder NamedTuple
    _internal.py       — _grant_permission, ek conversions
    ↓
EventKit (public) + ReminderKit (private) frameworks via PyObjC
    ↓
Apple Reminders.app
```

- `libs/pyremindkit/` directory ELIMINATED. The vendored-dep theater drops; this code is ours.
- `_native/` is the new home: clear that this is the OS-bridge layer.

## Components

### `_native/eventkit.py` — EventKit bridge (was pyremindkit core)

- **Responsibility**: EventKit (public framework) operations only. Calendars, basic reminders, EKAlarm, EKRecurrenceRule.
- **Inputs / Outputs**: Python value types in/out; `EKEventStore` instance held privately.
- **Satisfies**: spec §Ubiquitous (every existing tool's bindings continue to work).

### `_native/reminderkit.py` — Private framework bridge

- **Responsibility**: Load `ReminderKit.framework` at startup; expose `REMReminder` operations for subtasks, flagged, tags, sections.
- **Implementation**: `objc.loadBundle("ReminderKit", bundle_path="/System/Library/PrivateFrameworks/ReminderKit.framework", module_globals=globals())`. Pattern verified in `BRO3886/rem`.
- **Failure mode**: If `loadBundle` raises, the module sets a `REMINDERKIT_AVAILABLE = False` sentinel; the `bridge` facade routes around it (tools that need it return `Error: ReminderKit unavailable`).
- **Satisfies**: spec §Event-driven (subtask + flagged + tag operations), §Unwanted-behavior (load-failure degradation).

### `_native/bridge.py` — Unified facade

- **Responsibility**: Single object that tools talk to. Combines EventKit and ReminderKit; each tool sees one API surface and doesn't know which framework backs each operation.
- **Lifespan-managed**: created once per server process, kept alive across all tool invocations.
- **Satisfies**: spec §State-driven (exactly one `RemindKit` instance via lifespan).

### `tools/` modules — FastMCP decorator style

- **Responsibility**: Each module decorates 4–8 tools with `@mcp.tool()`. Signature: `async def tool(arg1: T, ..., ctx: Context) -> Pydantic`. Context is auto-injected.
- **Migration approach**: tool-by-tool, with bit-for-bit name + schema preservation per spec §Ubiquitous. The 22 existing tools become 22 decorated functions. Phase 1 adds 6–8 more. Phase 3 adds another 8–12.

### `resources/` modules — URI-templated read views (NEW)

- `reminders://list/{id}` — full reminder list at a calendar ID.
- `reminders://default` — the default calendar's reminders.
- `reminders://overdue` — incomplete reminders past due.
- `reminders://today` — reminders due today.
- `agents://current` — the active `Agents-<project>` list (Phase 4).
- **Returns**: structured data (JSON-serialized Pydantic), not text. Clients can pin them as ambient context without round-tripping a tool call.

### `prompts/` modules — Canned workflows (NEW)

- `daily_review` — pull overdue + today + tomorrow, ask user to triage.
- `weekly_retro` — pull Done items from the past 7 days, ask LLM to extract patterns.
- `brain_dump_triage` — given uncategorized items, ask LLM to sort into domain lists.
- `agent_visibility_sync` — mirror `TodoWrite` state into Reminders.
- **Returns**: structured `Prompt` objects that the client surfaces in its UI.

### `models.py` — Pydantic schemas

```python
class Calendar(BaseModel):
    id: str
    name: str
    color: str
    is_default: bool
    owner: str | None = None

class Reminder(BaseModel):
    id: str
    title: str
    due_date: datetime | None
    notes: str | None
    completed: bool
    url: str | None
    priority: int
    list_id: str
    created_date: datetime | None
    modified_date: datetime | None
    flagged: bool
    parent_reminder_id: str | None
    subtasks: list[str]
    tags: list[str]
    completion_date: datetime | None
    start_date: datetime | None

class RecurrenceRule(BaseModel):
    frequency: Literal["daily","weekly","monthly","yearly"]
    interval: int = 1
    end_date: datetime | None = None
    occurrence_count: int | None = None
    # ... (full EKRecurrenceRule mapping)

class Alarm(BaseModel):
    relative_offset_seconds: int | None = None
    absolute_date: datetime | None = None
    location: GeoLocation | None = None
    proximity: Literal["enter","leave"] | None = None
```

## Data model

### `Reminder` field additions (vs current 11-field NamedTuple)

- `parent_reminder_id: str | None` — from ReminderKit `REMReminder.parentIdentifier` (TBD; verify in S1.4).
- `subtasks: list[str]` — child reminder IDs.
- `tags: list[str]` — from ReminderKit `REMReminder.hashtags`.
- `completion_date: datetime | None` — from EventKit `ek_reminder.completionDate()`.
- `start_date: datetime | None` — from EventKit `ek_reminder.startDateComponents()`.

Field set frozen at end of Phase 0.4 (the Pydantic-model slice).

### `Calendar` field additions (none in Phase 0-2)

Phase 3 may add `source_name` (the iCloud account name) and `is_subscribed`.

## API surface

### Existing tools (22) — names and schemas preserved

Migration to FastMCP-decorator form changes the implementation, not the surface. Same 22 names. Same `inputSchema`. Output `text` becomes a structured Pydantic block (which FastMCP renders to text for backwards compatibility AND structured if the client supports it).

### New tools by phase

**Phase 1.2–1.7**: `create_calendar`, `delete_calendar`, `update_calendar`, `get_subtasks`, `set_parent`, `set_flagged`, `set_tags`.
**Phase 2**: no new TOOLS (Resources + Prompts are separate primitives).
**Phase 3.1–3.6**: `set_alarm`, `set_location_alarm`, `set_recurrence`, `bulk_complete`, `bulk_delete_completed`, `bulk_move`, `get_completed_in_range`.
**Phase 4.x**: `bootstrap_agent_list`, optionally `triage_brain_dump` (sampling-driven).

**Total**: 22 + 7 + 7 = 36 tools by end of Phase 3. ~38 by end of Phase 4.

### New resources

`reminders://list/{id}`, `reminders://default`, `reminders://overdue`, `reminders://today`, `agents://current`.

### New prompts

`daily_review`, `weekly_retro`, `brain_dump_triage`, `agent_visibility_sync` — exact templates designed at Phase 2.2.

## Contracts (frozen at end of Phase 0)

```python
# Pydantic field order in models.py is the contract. Additions go AT THE TAIL.

class Reminder(BaseModel):
    # Field order: id, title, due_date, notes, completed, url, priority, list_id,
    # created_date, modified_date, flagged, parent_reminder_id, subtasks, tags,
    # completion_date, start_date.
    # New fields after Phase 0 require an ADR + spec amendment.
```

MCP tool names and inputSchemas frozen at end of Phase 1.

## Error handling

| Condition | Behavior | Where raised |
|---|---|---|
| ReminderKit fails to load | stderr warning at startup; degraded mode | `_native/reminderkit.py` module init |
| Tool needing ReminderKit invoked while unavailable | `Error: ReminderKit unavailable; falling back to public EventKit (degraded)` | `_native/bridge.py` |
| `create_calendar` duplicate name | `ValueError("Calendar named 'X' already exists.")` | `_native/eventkit.py::CalendarManager.create` |
| `delete_calendar` non-empty without force | `ValueError("Calendar 'X' has N reminders; pass force=true to delete.")` | same |
| `delete_calendar` on default | `ValueError("Cannot delete the default calendar.")` | same |
| `create_reminder` parent/calendar mismatch | `ValueError(...)` | `RemindKit.create_reminder` |
| Pydantic validation failure | FastMCP raises; client sees structured error | framework |
| EventKit save failure | `RuntimeError` (existing pattern) | `_save_ek_reminder` |

All errors flow through FastMCP's automatic error translation — handlers raise, the framework renders to MCP error responses.

## Observability

- **Logging**: `Context.debug() / info() / warning() / error()`. Replaces every `print(..., file=sys.stderr)` in current handlers (none after Phase 0.5).
- **Progress**: `Context.report_progress(progress, total, message)` on bulk operations.
- **Sampling diagnostics**: every `ctx.session.create_message()` call logs the prompt summary and result token count at debug level.

## Security considerations

- **stdio transport** is the only deployed transport. Streamable HTTP is Phase 4.3 (optional). The CVE-2025-49596 RCE on stdio is upstream — we don't mitigate by changing transport; we mitigate by trusting only Pierce's own MCP clients.
- **ReminderKit private API access** carries no extra security risk vs EventKit (both operate in-process with the same TCC permission gate).
- **Per-tool kill switch** (Phase 4 cross-cutting): each decorated `@mcp.tool()` checks a feature-flag map populated from `VIBE.yaml::agents.tool_flags`. Disabled tools return immediate `Error: tool disabled by config`.
- **Input validation**: Pydantic on every input. Allowlist for colors, frequencies, proximities. No `eval`, no `shell=True`, no string-interpolated SQL.
- **OWASP MCP guide review**: deliberate pass during Phase 4 (`docs/SECURITY-REVIEW.md`).

## Performance considerations

- **Lifespan-managed RemindKit**: instantiated once per server process. Permission prompt fires at most once.
- **ReminderKit binding latency**: in-process. Negligible.
- **Bulk operations**: progress every 10 items. Cancellation (`Context.session.is_cancelled`) checked between items.
- **`search_reminders`** is still O(N_calendars × N_reminders) — improved later via EventKit predicates if needed.

## Alternatives considered

### AppleScript bridge for ReminderKit-backed features

- **Why considered**: Public, stable, won't break on macOS updates.
- **Why rejected**: Pierce explicitly chose ReminderKit. Cross-process AppleScript adds 50–200ms per call.
- **Kept as fallback**: if ReminderKit binding breaks in a future macOS version, the degraded-mode path (mentioned in §Error handling) can be expanded to AppleScript as needed. Out of initial scope.

### Stay on low-level MCP `Server` class

- **Why considered**: Less refactor work upfront.
- **Why rejected**: Pierce explicitly chose modernize-first. Every additional capability would land on a deprecated foundation, making cleanup harder.

### Split into multiple specs (one per phase)

- **Why considered**: Easier per-PR review, smaller mental footprint.
- **Why rejected**: The phases share substrate (the `_native/` rename, the FastMCP foundation, the Pydantic models, the ReminderKit bindings). Splitting would force mid-program seam adjustments.

## Open design questions

- **`REMReminder.parentIdentifier` vs `REMReminder.subtasks` exact header signatures** — verify at Phase 1.4 implementation time. Header dump exists at `xybp888/iOS-Header/.../ReminderKit.framework/`; binding code uses `objc.classAddMethods` if needed.
- **Sampling-driven `triage_brain_dump` UX** — does the LLM call back happen synchronously (tool returns after triage completes) or asynchronously (tool returns a job ID; resource exposes status)? Decided at Phase 2.5.
