# mcp_apple_reminders

The MCP server package. Bootstraps `pyremindkit`, registers 22 tools across 4
categories, and speaks JSON-RPC over stdio.

## Status

🟢 Production · Owner: @pierce · No SLO (single-user)

## Why this exists

Apple's Reminders.app is the source of truth for Pierce's personal task system.
EventKit gives macOS apps programmatic access; this package wraps EventKit (via
the vendored `pyremindkit`) and exposes the operations as MCP tools so Claude /
Codex / Claude Desktop can read and write Reminders directly.

## Public API

This is a server package, not a library — its "API" is the set of MCP tools it
registers. The Python surface is:

- `cli_main() -> int` — the console-script entry point (`mcp-apple-reminders`).
- `main()` — async entry point (`python -m mcp_apple_reminders`).
- `app: Server` — the `mcp.server.Server` instance with `list_tools` and
  `call_tool` decorators applied.
- `remind: RemindKit` — the module-level `RemindKit` instance, instantiated at
  import time (triggers permission prompt on first run).

## Architecture

```
stdio JSON-RPC
   ↓
server.py::call_tool (dispatch + central try/except)
   ↓
tools/__init__.py::ALL_HANDLERS  (name → handler)
   ↓
tools/<category>.py::_handle_<name>(arguments, remind)
   ↓
formatting.py::format_reminder  ←  pyremindkit.RemindKit
                                       ↓
                          libs/pyremindkit/src/pyremindkit/...
                                       ↓
                                  EventKit (PyObjC)
                                       ↓
                              Apple Reminders.app
```

- Depends on: `pyremindkit` (vendored), `mcp` (PyPI), `pyobjc-framework-EventKit`.
- Depended on by: MCP clients (Claude Code / Codex / Claude Desktop) over stdio.

## Files

- `__init__.py` — package metadata + `cli_main` re-export.
- `__main__.py` — `python -m mcp_apple_reminders` entry.
- `server.py` — orchestrator: sys.path bootstrap, `RemindKit()` init, `app` instance, `list_tools` / `call_tool` decorators, `main()` / `cli_main()`.
- `formatting.py` — `format_reminder`, `parse_datetime`, `parse_priority`. Shared by every handler.
- `tools/` — per-category tool modules. See `tools/README.md`.

## Invariants

- **stdio is sacred.** Nothing in this package may write to stdout. Logs / diagnostics → stderr only.
- **`remind` is module-global.** It exists as a singleton because `RemindKit.__init__` triggers a permission dialog; doing that once at import is intentional. Handlers MUST receive `remind` as a parameter, not import it directly, to keep them testable.
- **Handlers raise; the dispatcher renders.** Do not duplicate the `try/except ValueError / except Exception` wrapper inside handlers — it lives in `server.py::call_tool`.
- **Tool name + `inputSchema` are public contracts.** Changing them breaks every deployed MCP client. Add new tools rather than mutating existing ones.

## Common tasks

- **Add a new tool to an existing category** — pick the right `tools/<category>.py`, add the `Tool` schema to `TOOLS`, add `_handle_<name>` to `HANDLERS`. No edits elsewhere.
- **Add a new tool category** — create `tools/<name>.py` with `TOOLS` and `HANDLERS`, then add one import + spread to `tools/__init__.py`. See `tools/README.md`.
- **Change rendering of `Reminder`** — edit `formatting.py::format_reminder`. Every handler picks it up.
- **Change permission behavior / startup** — edit `_grant_permission` in `libs/pyremindkit/src/pyremindkit/_internal.py`, then the catch-block in `server.py` if needed.

## Gotchas

- `server.py` does a `sys.path.insert` for the vendored `pyremindkit` BEFORE the import. Reordering imports or removing the bootstrap will break the package at import time.
- `from pyremindkit import RemindKit` works because of that bootstrap — there is no `pyremindkit` on PyPI to fall back to.
- Module-level `remind = RemindKit()` will exit the process on permission failure. By design — better than a half-broken server.

## Related

- `libs/pyremindkit/VENDOR.md` — pyremindkit upstream provenance and local-mods record.
- `AGENTS.md §9` — broader gotchas list.
- `MAP.md` — repo-level navigation.
