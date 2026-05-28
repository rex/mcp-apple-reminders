# tools/

Per-category MCP tool registry. Each module here owns 5–6 tools in one logical
domain (calendars, reminders, queries, workflow); `__init__.py` aggregates them
into the two flat collections the server dispatcher consumes.

## Status

🟢 Production · Owner: @pierce

## Why this exists

The original `server.py` registered all 22 tools in two giant functions
(`list_tools` and `call_tool`) — ~960 lines, impossible to navigate. Splitting
by category gives each domain its own ~150-line module with both the tool
schemas and their handlers side-by-side. Adding a new tool means finding the
right category and adding two lines (one schema, one handler).

## Public API

Each `tools/<category>.py` exports exactly two module-level symbols:

- `TOOLS: list[Tool]` — the MCP `Tool` schemas (name, description, inputSchema).
- `HANDLERS: dict[str, Callable]` — name → handler. Handler signature:
  `(arguments: dict, remind: RemindKit) -> list[TextContent]`.

`__init__.py` exports:

- `ALL_TOOLS: list[Tool]` — concatenation of every category's TOOLS in category order.
- `ALL_HANDLERS: dict[str, Callable]` — merged dict of every category's HANDLERS.

## Architecture

```
server.py::list_tools()  → tools/__init__.py::ALL_TOOLS
server.py::call_tool()   → tools/__init__.py::ALL_HANDLERS[name](arguments, remind)
                                                                  ↓
                                                  tools/<category>.py::_handle_<name>
                                                                  ↓
                                              pyremindkit / formatting helpers
```

- Depends on: `pyremindkit` (the EventKit wrapper), `..formatting` (shared rendering).
- Depended on by: `..server.py` only.

## Files

| File | Tools | Lines |
|---|---|---|
| `__init__.py` | aggregator (`ALL_TOOLS`, `ALL_HANDLERS`) | 27 |
| `calendars.py` | `list_calendars`, `get_calendar`, `get_calendar_by_id`, `search_calendars`, `get_default_calendar` (5) | 120 |
| `reminders.py` | `create_reminder`, `update_reminder`, `complete_reminder`, `uncomplete_reminder`, `get_reminder`, `delete_reminder` (6) | 168 |
| `queries.py` | `get_reminders`, `search_reminders`, `get_next_reminder`, `get_overdue_reminders`, `get_today_reminders` (5) | 184 |
| `workflow.py` | `get_workflow_lists`, `move_reminder_to_list`, `move_reminder_on_deck`, `move_reminder_active`, `move_reminder_done`, `move_reminder_blocked` (6) | 151 |

22 tools total. Each category file stays under the 250-line soft limit.

## Invariants

- **Handler signature is uniform**: `(arguments: dict, remind: RemindKit) -> list[TextContent]`. Don't deviate; the dispatcher passes only those two args.
- **Handlers raise; never catch**: bare `raise` for unexpected errors, `raise ValueError(...)` for user-input mistakes. The central `try/except` in `server.py::call_tool` translates those to MCP responses.
- **`TOOLS` and `HANDLERS` must agree on keys**: every `Tool.name` must have a matching entry in `HANDLERS`. The `tools/__init__.py` test (verify before commit) catches mismatches.
- **No I/O at import time** in the category modules. Only `server.py` does the `remind = RemindKit()` singleton — category modules are pure registries.

## Common tasks

- **Add a new tool to an existing category** —
  1. Add `_handle_<name>(arguments, remind) -> list[TextContent]` function above `TOOLS` in the category file.
  2. Append a `Tool(name=..., description=..., inputSchema=...)` to `TOOLS`.
  3. Add `"<name>": _handle_<name>` to `HANDLERS`.
  No edits in `server.py` or `__init__.py`.

- **Add a new category** (rare — only if no existing category fits) —
  1. Create `tools/<name>.py` with the two exports.
  2. Add `from . import <name>` to `__init__.py`.
  3. Spread its `TOOLS` and `HANDLERS` into the aggregators (one line each).

- **Reorder tools in the catalog** — reorder the lists; the dict merge order doesn't matter since dispatch is by key lookup.

## Gotchas

- `formatting.py` lives one level up (`from ..formatting import ...`). Don't accidentally do a flat-relative import.
- The `Claude-*` move sugars in `workflow.py` all share `_move_to_named_list` — keep it that way to avoid divergent error messages.
- `get_reminders` and `get_today_reminders` both build filter kwargs but slightly differently — `get_reminders` uses the shared `_build_filter_kwargs`; `get_today_reminders` overrides date bounds. Don't refactor them together without thinking about the today-edge-cases.

## Related

- `../server.py` — the dispatcher that consumes this registry.
- `../formatting.py` — the shared rendering helpers every handler uses.
- `MAP.md` — extension points and the full mental model.
