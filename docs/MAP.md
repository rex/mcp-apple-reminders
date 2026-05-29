# MAP

Repo navigation for humans and agents. Update when you add a domain, a module, or a hot path.

## Stack

macOS only · Python 3.10+ · MCP Python SDK 1.27.1 (FastMCP high-level API) ·
Pydantic v2 · PyObjC/EventKit + compiled Swift/Obj-C helper subprocesses.

## Domains / Components

| Component | Purpose | Entry point | Owner |
|---|---|---|---|
| Server | `FastMCP` instance, transport selection, run entry | `src/mcp_apple_reminders/server.py` | @pierce |
| Lifespan | Async lifespan → `AppContext` (SQLite path, helper paths, `open_sqlite()`) | `src/mcp_apple_reminders/lifespan.py` | @pierce |
| Models | Frozen Pydantic v2 (`Reminder`, `Calendar`, …) + deeplinks (CONTRACT FREEZE) | `src/mcp_apple_reminders/models.py` | @pierce |
| Formatting | Datetime / priority parsing helpers | `src/mcp_apple_reminders/formatting.py` | @pierce |
| Tools (10 modules, 41 tools) | `@mcp.tool` functions per domain | `src/mcp_apple_reminders/tools/` | @pierce |
| Resources (4 views) | Read-only SQLite-backed `@mcp.resource` views | `src/mcp_apple_reminders/resources/` | @pierce |
| Prompts (4) | Canned `@mcp.prompt` workflows | `src/mcp_apple_reminders/prompts/workflows.py` | @pierce |
| Native — SQLite reads | Direct CoreData SQLite reader + row→model helpers | `src/mcp_apple_reminders/_native/sqlite.py`, `_sqlite_helpers.py` | @pierce |
| Native — EventKit writes | Python wrapper for the Swift `rem_eventkit` helper (public API) | `src/mcp_apple_reminders/_native/eventkit.py` | @pierce |
| Native — ReminderKit writes | Transport + typed actions for the Obj-C `rem_reminderkit` helper (private fw) | `src/mcp_apple_reminders/_native/reminderkit.py`, `reminderkit_actions.py` | @pierce |
| Native — legacy EventKit | Original PyObjC wrapper, still used on some paths | `src/mcp_apple_reminders/_native/core.py`, `_internal.py`, `calendars.py`, `models.py` | @pierce |
| Native — bulk helpers | Bulk-op helpers | `src/mcp_apple_reminders/_native/bulk.py` | @pierce |

### Tool modules (under `tools/`)

| Module | # | Tools |
|---|---|---|
| `calendars.py` | 8 | create/delete/update/get calendar, get_calendar_by_id, get_default_calendar, list_calendars, search_calendars |
| `reminders.py` | 6 | create/update/delete/complete/uncomplete/get reminder |
| `queries.py` | 6 | get_reminders, get_today_reminders, get_overdue_reminders, get_next_reminder, get_completed_in_range, search_reminders |
| `workflow.py` | 6 | move_reminder_{active,on_deck,blocked,done,to_list}, get_workflow_lists |
| `groups.py` | 4 | create_group, list_groups, delete_group, move_list_to_group |
| `alarms.py` | 3 | set_alarm, set_location_alarm, set_recurrence |
| `bulk.py` | 3 | bulk_complete, bulk_move, bulk_delete_completed |
| `sections.py` | 3 | get_subtasks, set_parent, assign_section |
| `agents.py` | 1 | bootstrap_agent_list |
| `sampling.py` | 1 | triage_brain_dump |

Full per-tool reference: `docs/TOOLS.md`.

### Resources (under `resources/`)

| URI | Module |
|---|---|
| `reminders://default`, `reminders://overdue`, `reminders://today`, `reminders://list/{calendar_id}` | `resources/reminders.py` |
| `agents://current/{project_name}` | `resources/agents.py` |

### Native binaries

`_native/bin/{rem_eventkit, rem_reminderkit}` are compiled from
`_native/src/{rem_eventkit.swift, rem_reminderkit.m}` (borrowed from
viticci/remctl, MIT — see `_native/THIRD_PARTY_NOTICES.md`). Build with
`make build-native`.

## Extension points

- **New MCP tool category** → add `tools/<name>.py` with `@mcp.tool`-decorated
  functions; add `from . import <name>` to `tools/__init__.py` so the decorators run.
- **New tool inside a category** → add one `@mcp.tool`-decorated function to that
  module. Pull state from `ctx.request_context.lifespan_context` (the `AppContext`).
- **New Resource / Prompt** → add a `@mcp.resource` / `@mcp.prompt` function under
  `resources/` / `prompts/` and ensure its module is imported.
- **New read** → add a method to `_native/sqlite.py` (+ `_sqlite_helpers.py`).
- **New write** → use the Swift helper via `_native/eventkit.py`, or the
  ReminderKit helper via `_native/reminderkit_actions.py`. Add native source under
  `_native/src/` and rebuild with `make build-native` if a new helper command is needed.

## Where bodies are buried

- **Reads and writes use different substrates.** Queries read the CoreData SQLite
  store directly; writes shell out to helper subprocesses. A just-written value
  may lag in SQLite until CoreData flushes — don't assert read-after-write blind.
- **Dead callbacks.** `_native/core.py::RemindKit.on_reminder_created` /
  `on_reminder_completed` register callbacks that NEVER fire. No observer wired.
- **EventKit error out-params are broken (legacy path).** `core.py` passes Python
  `None` for the EventKit error pointer; real errors never propagate — failure
  messages literally say `None`. (Tracked fix: CL-bug.)
- **stdio IS the transport.** Never `print()` to stdout from anything the server
  imports — it corrupts the JSON-RPC stream. Diagnostics → stderr / `Context` log.
- **macOS permission is per-binary.** The interpreter and helper binaries must
  each hold a Reminders TCC grant. Conda and Homebrew Python are distinct entries.

## Do not edit without ADR

- Public MCP tool `name=` values or argument signatures — breaks deployed clients.
- `models.py` field order — CONTRACT FREEZE; tail-append only, never reorder.
- `_native/__init__.py` re-export list — breaks the documented import surface.

## Hot paths (watch performance)

- `search_reminders` / `get_reminders` without a calendar filter — scan across
  lists. SQLite-backed now, but still O(N) over the store.

## Cold paths (rarely touched)

- Lifespan startup (`app_lifespan`) — resolves paths once per process.
- `get_default_calendar`, `get_workflow_lists` — not in tight loops.

## Cross-cutting concerns

- **Shared state**: `lifespan.py::AppContext` — resolved SQLite path, native helper
  paths, `open_sqlite()`. Reached via `ctx.request_context.lifespan_context`.
- **Server orchestration**: `server.py` — owns the `mcp` instance, imports
  `tools` to trigger registration, selects transport, runs.
- **Models / formatting**: `models.py` (shapes + deeplinks) and `formatting.py`
  (datetime / priority parsing) are the shared render layer.

## External dependencies

| System | What we call | When | Failure mode |
|---|---|---|---|
| CoreData SQLite store | Direct read via `_native/sqlite.py` | Every query / Resource | Store missing/locked → `RemindersDBUnavailable` |
| Apple EventKit (Swift helper) | `bin/rem_eventkit` subprocess | Public-API writes | Permission denied; missing binary → write fails |
| ReminderKit (Obj-C helper) | `bin/rem_reminderkit` subprocess | Private-fw writes (subtasks, flags, tags, sections, groups) | Framework/API drift; missing binary → write fails |
| macOS TCC | Per-binary Reminders grant | Any EventKit write | Ungranted interpreter/helper → permission error |

## Quick tour (read order for a new contributor)

1. `README.md` — installation / configuration / tool catalog.
2. `AGENTS.md` — agent-readable project contract.
3. This file — where things live.
4. `src/mcp_apple_reminders/server.py` — the `mcp` instance + run entry.
5. `src/mcp_apple_reminders/lifespan.py` — the `AppContext` tools depend on.
6. `src/mcp_apple_reminders/tools/` (+ its `README.md`) — how tools register.
7. `src/mcp_apple_reminders/_native/` — the three-tier read/write substrate.
