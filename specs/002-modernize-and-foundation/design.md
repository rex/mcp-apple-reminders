# Design — 002-modernize-and-foundation

> How we satisfy `spec.md`. Section references are to spec.md.

## Architecture overview

```
MCP client (Claude Code / Codex / Claude Desktop)
    ↓
src/mcp_apple_reminders/server.py            (FastMCP instance, lifespan, transport)
    ↓
src/mcp_apple_reminders/tools/*.py           (@mcp.tool() decorators)
src/mcp_apple_reminders/resources/*.py       (@mcp.resource() decorators)
src/mcp_apple_reminders/prompts/*.py         (@mcp.prompt() decorators)
src/mcp_apple_reminders/models.py            (Pydantic schemas with `deeplink`)
    ↓
src/mcp_apple_reminders/_native/bridge.py    (unified facade — routes reads to SQLite, writes to helpers)
    ↓                ↓                ↓
   sqlite.py         eventkit.py      reminderkit.py
   (Python)          (Python wrapper) (Python wrapper)
   reads             ↓                ↓
   SQLite db         bin/rem_eventkit bin/rem_reminderkit
                     (Swift binary)   (Obj-C binary)
                     ↓                ↓
                     EventKit         ReminderKit (private)
                     ↓                ↓
                     Apple Reminders.app + iCloud sync
```

**Three tiers**, modeled on `viticci/remctl`:

1. **SQLite reads** (Python, in-process). Source: `~/Library/Group Containers/group.com.apple.reminders/Container_v1/Stores/Data-*.sqlite`. Read-only. Tens of milliseconds for full corpus. Exposes EVERYTHING — sections, subtasks, tags, attachments, alarms metadata, recurrence metadata — without any framework call.
2. **EventKit writes** (Swift subprocess). Helper compiled at build time: `_native/bin/rem_eventkit`. Borrowed from `viticci/remctl::remctl-bridge.swift` with attribution. Handles public-API writes that must round-trip iCloud (create/update/delete reminders, calendar lifecycle, alarms, recurrence). Direct SQLite writes are NOT used — they'd bypass iCloud sync and corrupt the store.
3. **ReminderKit writes** (Objective-C subprocess). Helper compiled at build time: `_native/bin/rem_reminderkit`. Borrowed from `viticci/remctl::remctl-private.m` with attribution. Handles private-API writes (subtasks, tags, sections, flagged, attachments, urgent state, Early Reminders).

`libs/pyremindkit/` directory ELIMINATED in S0.2. `_native/` is the new home.

## Components

### `_native/sqlite.py` — SQLite reader (NEW)

- **Responsibility**: Open the Reminders.app SQLite store read-only; expose Python iterators / fetchers for calendars, reminders, sections, tags, subtask relationships, attachments.
- **Schema introspection** at module load: capture schema version; if unknown, log warning + degrade.
- **Concurrency**: SQLite connections are per-thread; Bridge owns one.
- **Deeplink construction** at read time — extract `ZREMCDOBJECT.ZIDENTIFIER` (or wherever the UUID lives in the schema) and concat with `x-apple-reminderkit://REMCDReminder/`.
- **Satisfies**: spec §Ubiquitous (SQLite-first reads), §Unwanted-behavior (RemindersDBUnavailable on missing file).

### `_native/eventkit.py` — Swift helper wrapper (refactored)

- **Responsibility**: Spawn `_native/bin/rem_eventkit` subprocess; send JSON request on stdin; parse JSON response on stdout. Translate between Python and the helper's protocol.
- **Pattern**: long-lived subprocess (one per Bridge lifetime) OR per-call (decided at S0.6 — long-lived for latency, per-call for simplicity).
- **Failure mode**: Non-zero exit → `EventKitHelperError` raised to caller; surfaces as MCP error.

### `_native/reminderkit.py` — Obj-C helper wrapper (NEW)

- **Responsibility**: Same pattern as eventkit.py but for the private-API helper.
- **Failure mode**: Non-zero exit OR helper not built (binary missing) → `ReminderKitHelperUnavailable`; affected tools return `Error: ReminderKit helper unavailable`.

### `_native/bin/rem_eventkit` (Swift) — borrowed

- **Source**: `viticci/remctl::remctl-bridge.swift`. MIT. Verbatim borrow with inline header attributing.
- **Adaptation**: minimal — adjust the JSON command set to match our tool surface. Document divergences in inline comments.

### `_native/bin/rem_reminderkit` (Objective-C) — borrowed

- **Source**: `viticci/remctl::remctl-private.m`. MIT. Verbatim borrow with inline header attributing.
- **Adaptation**: same approach. The Obj-C runtime is the substrate; we don't need to touch the internals.

### `_native/bridge.py` — Unified facade

- **Responsibility**: Single object that tools talk to. Routes reads to `sqlite.py`, public writes to `eventkit.py`, private writes to `reminderkit.py`.
- **Lifespan-managed**: created once per server process; owns the SQLite connection and helper subprocess(es).
- **Satisfies**: spec §State-driven (exactly one `Bridge` instance via lifespan).

### `_native/THIRD_PARTY_NOTICES.md` — Attribution (NEW)

- MIT license text for `viticci/remctl`.
- File-by-file mapping of borrowed code with original paths and commit SHAs.
- Re-sync procedure mirrored from the (now-defunct) pyremindkit VENDOR.md.

### `tools/`, `resources/`, `prompts/` — FastMCP decorators (NEW + refactored)

- Each module decorates tools / resources / prompts. Signature: `async def thing(arg1: T, ..., ctx: Context) -> Pydantic`. Context auto-injected.
- Tool registration: 22 existing tools migrated in S0.4 with bit-for-bit name + schema preservation.

### `models.py` — Pydantic schemas (NEW)

```python
class Calendar(BaseModel):
    id: str
    name: str
    color: str
    is_default: bool
    owner: str | None = None
    deeplink: str        # NEW — x-apple-reminderkit://REMCDList/{id}

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
    section_name: str | None     # NEW — from SQLite read
    completion_date: datetime | None
    start_date: datetime | None
    deeplink: str                # NEW — x-apple-reminderkit://REMCDReminder/{id}

class RecurrenceRule(BaseModel):
    frequency: Literal["daily","weekly","monthly","yearly"]
    interval: int = 1
    end_date: datetime | None = None
    occurrence_count: int | None = None

class Alarm(BaseModel):
    relative_offset_seconds: int | None = None
    absolute_date: datetime | None = None
    location: GeoLocation | None = None
    proximity: Literal["enter","leave"] | None = None
```

## Data model

### `Reminder` field additions

vs. current 11-field NamedTuple: append `parent_reminder_id`, `subtasks`, `tags`, `section_name`, `completion_date`, `start_date`, `deeplink`. Total: 18 fields. Frozen at end of S0.3.

### `Calendar` field additions

vs. current 5-field dataclass: append `deeplink`. Total: 6 fields. Frozen at end of S0.3.

### Deeplink construction

```python
def reminder_deeplink(uuid: str) -> str:
    return f"x-apple-reminderkit://REMCDReminder/{uuid}"

def calendar_deeplink(uuid: str) -> str:
    return f"x-apple-reminderkit://REMCDList/{uuid}"
```

The UUID is taken from the SQLite `ZIDENTIFIER` column (or, in the EventKit path, from `EKReminder.calendarItemIdentifier()` which is the same value). Verified at S0.3 model time.

## API surface

### Existing tools (22) — names + schemas preserved

Migration to FastMCP-decorator form in S0.4 changes implementation, not the surface.

### New tools by phase

**Phase 1.2–1.7**: `create_calendar`, `delete_calendar`, `update_calendar`, `get_subtasks`, `set_parent`, `set_flagged`, `set_tags`.
**Phase 1.8** (NEW): `assign_section` (move reminder into a section via ReminderKit helper).
**Phase 2**: no new tools (Resources + Prompts are separate primitives).
**Phase 3.1–3.6**: `set_alarm`, `set_location_alarm`, `set_recurrence`, `bulk_complete`, `bulk_delete_completed`, `bulk_move`, `get_completed_in_range`.
**Phase 4.x**: `bootstrap_agent_list`, optionally `triage_brain_dump`.

**Total**: 22 + 8 + 7 + 1 = 38 tools by end of Phase 3.

### New resources

`reminders://list/{id}`, `reminders://default`, `reminders://overdue`, `reminders://today`, `agents://current`.

### New prompts

`daily_review`, `weekly_retro`, `brain_dump_triage`, `agent_visibility_sync` — exact templates designed at S2.2.

## Contracts (frozen at end of Phase 0)

```python
# Pydantic field order in models.py is the contract. Additions go AT THE TAIL.
# Field count: 18 for Reminder, 6 for Calendar. Frozen at S0.3 close.
# New fields after Phase 0 require an ADR + spec amendment.
```

MCP tool names and inputSchemas frozen at end of Phase 1.

## Error handling

| Condition | Behavior | Where raised |
|---|---|---|
| SQLite file missing | `RemindersDBUnavailable`; tools fall back to EventKit reads | `_native/sqlite.py` |
| Schema version unknown | stderr warning at module load; degraded mode | same |
| Swift EventKit helper subprocess fails | `EventKitHelperError`; tool returns structured error | `_native/eventkit.py` |
| Obj-C ReminderKit helper subprocess fails | `ReminderKitHelperUnavailable`; tool returns degraded error | `_native/reminderkit.py` |
| `create_calendar` duplicate name | `ValueError(...)` | EventKit helper |
| `delete_calendar` non-empty without force | `ValueError(...)` | EventKit helper |
| `delete_calendar` on default | `ValueError("Cannot delete the default calendar.")` | EventKit helper |
| `create_reminder` parent/calendar mismatch | `ValueError(...)` | bridge.py before dispatch |
| Pydantic validation failure | FastMCP raises; client sees structured error | framework |

## Observability

- **Logging**: `Context.debug() / info() / warning() / error()`. Replaces every `print(..., file=sys.stderr)` in current handlers (none after S0.5).
- **Progress**: `Context.report_progress(progress, total, message)` on bulk operations.
- **Helper-process diagnostics**: each subprocess invocation logs the command + duration at debug level. Errors include the stderr buffer.

## Security considerations

- **stdio transport** only (CVE-2025-49596 mitigated by trust boundary — Pierce's own clients).
- **Swift / Obj-C helper subprocesses** run with the same TCC permissions as the parent (Reminders access). No additional attack surface beyond what RemCTL already exposes.
- **SQLite read-only mode** — open with `?mode=ro&immutable=1`. Even if the helper subprocess crashes, we can't corrupt the store.
- **Per-tool kill switch** (Phase 4 cross-cutting): each `@mcp.tool()` consults a feature-flag map populated from `VIBE.yaml::agents.tool_flags`.
- **OWASP MCP guide review**: deliberate pass during Phase 4 (`docs/SECURITY-REVIEW.md`).

## Performance considerations

- **Lifespan-managed Bridge**: instantiated once. SQLite connection persists. Helper subprocesses are either long-lived (low-latency) or per-call (simpler) — decided at S0.6.
- **SQLite reads**: tens of milliseconds for full corpus. `search_reminders` becomes a single indexed query.
- **Helper subprocess overhead**: ~5-50ms per call. Acceptable for user-driven operations.
- **Bulk operations**: progress every 10 items. Cancellation (`Context.session.is_cancelled`) checked between items.

## Alternatives considered

### Single Swift subprocess for everything (Google's recommendation)

- **Why considered**: Suggested by Pierce's external research.
- **Why rejected**: Doesn't match RemCTL's actual architecture, which is the proven reference. RemCTL uses TWO compiled helpers (Swift + Obj-C) plus direct SQLite reads. The Swift-for-everything pattern would lose the SQLite-read performance win.

### PyObjC for everything (my original recommendation)

- **Why considered**: Pure Python toolchain, no native build step.
- **Why rejected**: Doesn't match the proven RemCTL pattern. PyObjC private-framework bindings are less battle-tested than the Obj-C subprocess approach RemCTL uses. The SQLite-read path also makes more sense than EventKit-iterated reads regardless of how writes happen.

### Submodule pyremindkit instead of vendor

- **Why considered**: Easier upstream sync.
- **Why rejected**: pyremindkit upstream is dead (9 commits, no activity since Dec 2025). Vendored — and now refactored — substrate is ours. `_native/` rename makes that explicit.

### AppleScript bridge for ReminderKit features

- **Why considered**: Public, stable, immune to private-API changes.
- **Why rejected**: 50-200ms per call (cross-process AppleScript), and Pierce explicitly chose ReminderKit. Kept conceptually as a future degraded-mode option if Apple breaks the private surface.

### Stay on low-level MCP `Server` class

- **Why considered**: Less refactor work upfront.
- **Why rejected**: Pierce explicitly chose modernize-first. Every additional capability would land on a deprecated foundation, making cleanup harder.

## Open design questions

- **SQLite schema column names** — confirmed at S1.0 implementation time. Schema dump in `_native/sqlite.py` as a comment.
- **Helper subprocess lifetime** (long-lived vs per-call) — decided at S0.6.
- **`x-apple-reminderkit://` UUID resolution** — verify EventKit's `calendarItemIdentifier` matches SQLite `ZIDENTIFIER`. Verified at S0.3.
- **Sampling-driven `triage_brain_dump` UX** (sync vs async) — decided at S2.5.
