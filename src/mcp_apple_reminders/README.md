# mcp_apple_reminders

The MCP server package. Builds a FastMCP server, registers 41 tools, 4 Resources,
and 4 Prompts via decorators at import time, and speaks JSON-RPC over stdio (or
streamable HTTP).

## Status

🟢 Production · Owner: @pierce · No SLO (single-user)

## Why this exists

Apple's Reminders.app is the source of truth for Pierce's personal task system.
This package exposes its operations as MCP tools so Claude / Codex / Claude
Desktop can read and write Reminders directly. Reads come from the on-disk
CoreData SQLite store (fast, no permission prompt); writes go through small
compiled native helper subprocesses.

## Public API

This is a server package, not a library — its "API" is the set of MCP tools,
Resources, and Prompts it registers. The Python surface is:

- `cli_main() -> int` — the console-script entry point (`mcp-apple-reminders`),
  re-exported from `server.py` via `__init__.py`.
- `mcp: FastMCP` — the `FastMCP` instance in `server.py`. Every tool / resource /
  prompt attaches to it through its decorators.
- `python -m mcp_apple_reminders` — the `__main__.py` entry that calls `cli_main`.

The exhaustive tool catalog (names, args, behavior) lives in `docs/TOOLS.md`.

## Architecture

```
stdio JSON-RPC  (or streamable HTTP)
   ↓
server.py::mcp  (FastMCP — transport selection + run entry)
   ↓
lifespan.py::app_lifespan  → yields AppContext (resolved SQLite path,
                              native helper paths, open_sqlite())
   ↓
@mcp.tool / @mcp.resource / @mcp.prompt functions
   ↓                                      ↓
reads: _native/sqlite.py             writes: _native/eventkit.py (public API)
       (+ _sqlite_helpers.py)                _native/reminderkit.py (private fw)
   ↓                                      ↓
CoreData SQLite store                 rem_eventkit / rem_reminderkit subprocesses
   ↓                                      ↓
models.py (frozen Pydantic v2, each carrying a `deeplink`)
```

- Depends on: `mcp` (SDK 1.27.1, FastMCP high-level API), `pydantic` v2,
  `pyobjc-framework-EventKit`, and the compiled helpers in `_native/bin/`.
- Depended on by: MCP clients (Claude Code / Codex / Claude Desktop).

## Files

- `__init__.py` — package metadata + `cli_main` re-export.
- `__main__.py` — `python -m mcp_apple_reminders` entry.
- `server.py` — the `FastMCP` instance, transport selection, `main()` / `cli_main()`.
- `lifespan.py` — async lifespan yielding `AppContext` (resolved SQLite path,
  native helper paths, `open_sqlite()`); injected into tools as `ctx`.
- `models.py` — frozen Pydantic v2 models (`Reminder`, `Calendar`, …) plus the
  EventKit/native → Pydantic converters and `*_deeplink` helpers.
- `formatting.py` — datetime / priority parsing helpers shared across tools.
- `tools/` — 10 modules of `@mcp.tool` functions. See `tools/README.md`.
- `resources/` — `@mcp.resource` views served from SQLite. See below.
- `prompts/` — `@mcp.prompt` canned workflows.
- `_native/` — the three-tier native layer. See below.

### resources/

Four read-only `@mcp.resource` views, all served from the SQLite reader:

- `resources/reminders.py` — `reminders://default`, `reminders://overdue`,
  `reminders://today`, `reminders://list/{calendar_id}`.
- `resources/agents.py` — `agents://current/{project_name}`, the agent
  visibility plane (the `Agents-<project>` list mirrored as JSON).

### prompts/

Four `@mcp.prompt` canned workflows in `prompts/workflows.py` (e.g. daily
review / triage scaffolds) returning prompt messages, no side effects.

### _native/ (three tiers)

1. **SQLite reads** — `sqlite.py` reads the CoreData store directly;
   `_sqlite_helpers.py` maps rows → Pydantic models. Sub-millisecond, no
   permission prompt.
2. **Public-API writes** — `eventkit.py` is the Python transport for the
   compiled Swift helper (`bin/rem_eventkit`); standard EventKit writes.
3. **Private-framework writes** — `reminderkit.py` is the transport for the
   Obj-C ReminderKit helper (`bin/rem_reminderkit`); `reminderkit_actions.py`
   wraps it in typed actions (`create_subtask`, `set_flagged`, `add_tags`,
   `assign_section`, `create_group`, `delete_group`, `move_list_to_group`).
4. **Legacy** — `core.py` + `_internal.py` + `calendars.py` + `models.py` are
   the original EventKit/PyObjC wrapper, still on some paths. `bulk.py` holds
   bulk-op helpers.

Binaries live in `_native/bin/`, compiled from `_native/src/{rem_eventkit.swift,
rem_reminderkit.m}` (borrowed from viticci/remctl, MIT — see
`_native/THIRD_PARTY_NOTICES.md`). Build with `make build-native`.

## Invariants

- **stdio is sacred.** Nothing in this package may write to stdout — stdio IS
  the JSON-RPC transport. Logs / diagnostics → stderr (or the MCP `Context`
  logger) only.
- **Tools are registered by decorator at import time.** `tools/__init__.py`
  imports each tool module so the `@mcp.tool` decorators run; there is no
  `TOOLS`/`HANDLERS` aggregation dict anymore.
- **Tool name + signature are public contracts.** Changing them breaks deployed
  MCP clients. Add new tools rather than mutating existing ones.
- **Model field order is frozen.** `models.py` carries a CONTRACT FREEZE —
  append new fields at the tail only; never reorder. Each model exposes a
  `deeplink`.
- **Shared state flows through `AppContext`.** Tools reach SQLite and the native
  helper paths via the lifespan context, not module globals.

## Common tasks

- **Add a tool to an existing category** — open the right `tools/<category>.py`,
  add a `@mcp.tool(...)`-decorated function. No edits elsewhere.
- **Add a tool category** — create `tools/<name>.py` with decorated functions,
  add one `from . import <name>` to `tools/__init__.py`. See `tools/README.md`.
- **Add a Resource / Prompt** — add a `@mcp.resource` / `@mcp.prompt` function in
  `resources/` / `prompts/` and ensure the package `__init__` imports the module.
- **Change a model's rendering / shape** — edit `models.py` (tail-append only)
  or `formatting.py`. Every tool picks it up.
- **Rebuild native helpers** — edit `_native/src/*`, run `make build-native`.

## Gotchas

- **Reads vs. writes split substrates.** A read uses SQLite; a write shells out
  to a helper subprocess. A value just written may not appear in SQLite until
  CoreData flushes — don't assert read-after-write without a refresh.
- **Helper binaries must exist.** Write tools fail if `_native/bin/` is empty;
  run `make build-native` after a fresh clone.
- **Permission is per-binary.** EventKit writes require the interpreter (and
  helper) binaries to hold a macOS Reminders grant; conda vs. Homebrew Python
  are distinct TCC entries.

## Related

- `_native/THIRD_PARTY_NOTICES.md` — borrowed Swift / Obj-C helper provenance.
- `docs/TOOLS.md` — exhaustive tool catalog.
- `docs/MAP.md` — repo-level navigation.
- `AGENTS.md §9` — broader gotchas list.
