# MAP

Repo navigation for humans and agents. Update when you add a domain, a module, or a hot path.

## Domains

| Domain | Purpose | Entry point | Owner |
|---|---|---|---|
| Calendar tools | List / look up reminder calendars | `src/mcp_apple_reminders/tools/calendars.py` | @pierce |
| Reminder CRUD | Create / update / complete / delete reminders | `src/mcp_apple_reminders/tools/reminders.py` | @pierce |
| Query tools | Filter, search, overdue / today / next | `src/mcp_apple_reminders/tools/queries.py` | @pierce |
| Workflow lanes | `Claude-*` move-between-lists pipeline | `src/mcp_apple_reminders/tools/workflow.py` | @pierce |
| EventKit bridge | PyObjC ↔ EventKit ↔ Reminders.app | `src/mcp_apple_reminders/_native/core.py` | @pierce |
| Server orchestration | sys.path bootstrap, dispatcher, RemindKit init | `src/mcp_apple_reminders/server.py` | @pierce |

## Extension points

- **New MCP tool category** → add `tools/<name>.py` exporting `TOOLS: list[Tool]` and `HANDLERS: dict[str, Callable]`; add one import + spread in `tools/__init__.py`.
- **New tool inside an existing category** → add the `Tool` schema to that category's `TOOLS` list and a `_handle_<name>` function to `HANDLERS`. Handler signature: `(arguments: dict, remind: RemindKit) -> list[TextContent]`.
- **New EventKit-backed operation** → add the method to `_native/core.py::RemindKit` (or `_native/calendars.py` for calendar-scoped ops). Wire through to a new MCP tool.
- **New `Claude-*` workflow lane** → add a `_handle_move_reminder_<state>` in `tools/workflow.py` using the shared `_move_to_named_list` helper.

## Where bodies are buried

- **`Calendar.is_default` is wrong.** `calendars.py::CalendarManager.list()` uses `EKCalendar.isImmutable()` as the proxy. `isImmutable` means "user can't modify the calendar," NOT "is the default list." Every list reports `Default: No`. P0 fix.
- **Dead callbacks.** `_native/core.py::RemindKit.on_reminder_created` and `on_reminder_completed` register callbacks that NEVER fire. No EventKit observer is wired up.
- **EventKit error out-params are broken.** `_save_ek_reminder` and `delete_reminder` pass Python `None` for the EventKit error pointer; actual EventKit errors never propagate. Failure messages always literally say `None`.
- **stdio IS the transport.** Never `print()` to stdout from any code the MCP server imports — it corrupts the JSON-RPC stream. All diagnostics → stderr.
- **macOS permission is per-binary.** The exact path of the Python interpreter must be in the TCC table. Conda Python and Homebrew Python are different binaries and each need their own grant.

## Do not edit without ADR

- Public MCP tool names or `inputSchema` shapes — breaks deployed clients.
- `_native/__init__.py` re-export list — breaks the documented import surface.
- `Reminder` NamedTuple field set — downstream code unpacks positionally in places.

## Hot paths (watch performance)

- `search_reminders` — fetches every reminder from every calendar via EventKit, then filters in Python. O(N_calendars × N_reminders).
- `get_reminders` without `calendar_id` — iterates every calendar's predicate. Same N×M shape.

## Cold paths (rarely touched)

- `_grant_permission` — runs once at startup.
- `get_default_calendar` — EventKit-cached.
- `get_workflow_lists` — searches `Claude-*` once per call; not in a tight loop.

## Cross-cutting concerns

- **Permission gate**: `src/mcp_apple_reminders/_native/_internal.py::_grant_permission`. Single point of authority.
- **Server orchestration**: `src/mcp_apple_reminders/server.py`. Imports tools, dispatches, owns the centralized try/except.
- **Formatting**: `src/mcp_apple_reminders/formatting.py`. Every handler that renders a `Reminder` goes through `format_reminder`.
- **Error handling**: `server.py::call_tool`. Handlers raise; the dispatcher renders. Do not duplicate try/except in handlers.

## External dependencies

| System | What we call | When | Failure mode |
|---|---|---|---|
| Apple EventKit | EKEventStore + EKReminder + EKCalendar via PyObjC | Every reminder/calendar op | macOS permission denied → `PermissionError`; iCloud sync miss → stale data |
| `osascript` (Reminders.app) | `tell application "Reminders" ...` | Only in `shim_mcp.sh` for first-run permission prompt | Silent fail (intentional, `|| true`) |
| macOS TCC | Permission grants per binary | Server startup | `requestFullAccessToRemindersWithCompletion_` times out → permission error |

## Quick tour (read order for a new contributor)

1. `README.md` — installation / configuration / tool catalog.
2. `AGENTS.md` — agent-readable project contract.
3. This file — where things live.
4. `src/mcp_apple_reminders/server.py` — the orchestrator (~95 lines).
5. `src/mcp_apple_reminders/tools/__init__.py` — see how the categories assemble.
6. (removed in S0.2) — `libs/pyremindkit/VENDOR.md` deleted alongside the rename to `_native/`. The wrapper is now first-party.
