# tools/

Per-category MCP tool modules. Each file owns the tools for one logical domain
and registers them by decorating plain functions with `@mcp.tool`. There is no
aggregation dict — registration happens as a side effect of import.

## Status

🟢 Production · Owner: @pierce

## Why this exists

Splitting tools by domain keeps each module small and navigable, and keeps the
architecture line-limit gate happy (hard cap 400 lines/file). Adding a tool means
finding the right module and writing one decorated function.

## How registration works

FastMCP registers a tool the moment its module is imported:

```python
from ..server import mcp

@mcp.tool(name="create_reminder", description="Create a new reminder …")
def create_reminder(ctx: Context, title: str, ...) -> Reminder:
    app = ctx.request_context.lifespan_context   # the AppContext
    ...
```

`tools/__init__.py` does nothing but `from . import calendars, reminders, …` for
every module below, so importing the `tools` package runs all the decorators.
`server.py` imports `tools` once at startup; FastMCP then exposes the registry
over MCP automatically.

Shared state — the resolved SQLite path, native helper paths, and `open_sqlite()`
— reaches each tool through the **lifespan `AppContext`**, retrieved from the
injected `Context` (`ctx.request_context.lifespan_context`). Tools do not import
module globals for state.

## Public API

- Each module: a set of `@mcp.tool`-decorated functions (the tools themselves).
- `__init__.py`: imports every tool module so the decorators run. No exports.

## Architecture

```
server.py imports `tools` package
   ↓
tools/__init__.py imports each module → @mcp.tool decorators register on `mcp`
   ↓
tool fn(ctx, …):  ctx.request_context.lifespan_context  →  AppContext
                  reads  → _native/sqlite.py
                  writes → _native/eventkit.py / reminderkit.py
                  shapes → ../models.py, ../formatting.py
```

- Depends on: `..server.mcp`, `..models`, `..formatting`, the `.._native` layer.
- Depended on by: `..server` (imports the package to trigger registration).

## Modules (10 · 41 tools)

| Module | # | Tools |
|---|---|---|
| `calendars.py` | 8 | `create_calendar`, `delete_calendar`, `update_calendar`, `get_calendar`, `get_calendar_by_id`, `get_default_calendar`, `list_calendars`, `search_calendars` |
| `reminders.py` | 6 | `create_reminder`, `update_reminder`, `delete_reminder`, `complete_reminder`, `uncomplete_reminder`, `get_reminder` |
| `queries.py` | 6 | `get_reminders`, `get_today_reminders`, `get_overdue_reminders`, `get_next_reminder`, `get_completed_in_range`, `search_reminders` |
| `workflow.py` | 6 | `move_reminder_active`, `move_reminder_on_deck`, `move_reminder_blocked`, `move_reminder_done`, `move_reminder_to_list`, `get_workflow_lists` |
| `groups.py` | 4 | `create_group`, `list_groups`, `delete_group`, `move_list_to_group` |
| `alarms.py` | 3 | `set_alarm`, `set_location_alarm`, `set_recurrence` |
| `bulk.py` | 3 | `bulk_complete`, `bulk_move`, `bulk_delete_completed` |
| `sections.py` | 3 | `get_subtasks`, `set_parent`, `assign_section` |
| `agents.py` | 1 | `bootstrap_agent_list` |
| `sampling.py` | 1 | `triage_brain_dump` |

41 tools total. Full per-tool argument/behavior reference: `docs/TOOLS.md`.

## Invariants

- **One tool = one decorated function.** The `@mcp.tool(name=..., description=...)`
  decorator IS the registration. Don't reintroduce a `TOOLS`/`HANDLERS` dict.
- **`name=` is a public contract.** Every deployed client binds to it. Add new
  tools; never silently rename or reshape an existing one.
- **State via `AppContext`, not globals.** Pull SQLite / helper paths from
  `ctx.request_context.lifespan_context`.
- **Reads → SQLite; writes → native helpers.** Query tools go through
  `_native/sqlite.py`; mutating tools shell out via `_native/eventkit.py` or
  `_native/reminderkit_actions.py`.
- **Return models, not strings.** Return `Reminder` / `Calendar` (frozen Pydantic
  v2, each with a `deeplink`); FastMCP serializes them.

## Common tasks

- **Add a tool to an existing category** — write a `@mcp.tool`-decorated function
  in the matching module. No edits in `server.py` or `__init__.py`.
- **Add a new category** (rare) — create `tools/<name>.py` with decorated
  functions, then add `from . import <name>` to `tools/__init__.py`.

## Gotchas

- **A module that isn't imported registers nothing.** If a new module's tools
  don't appear, confirm `tools/__init__.py` imports it.
- `models.py` and `formatting.py` live one level up — `from ..models import …`,
  `from ..formatting import …`. Don't do a flat-relative import.
- The `move_reminder_*` lane tools in `workflow.py` share one move helper — keep
  them on it so error messages stay consistent.

## Related

- `../server.py` — owns the `mcp` instance and imports this package.
- `../models.py`, `../formatting.py` — shapes / rendering tools rely on.
- `docs/TOOLS.md` — exhaustive tool catalog.
- `docs/MAP.md` — repo-level navigation.
