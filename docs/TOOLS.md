# mcp-apple-reminders — capability catalog

Auto-generated from a live FastMCP server. **37 tools**, **3 static resources + 2 templated**, **4 prompts**.

## Tools

- `assign_section` — Move a reminder into a section within its parent list.
- `bootstrap_agent_list` — Idempotently ensure the `Agents-<project_name>` reminder list exists.
- `bulk_complete` — Mark a list of reminder IDs as completed.
- `bulk_delete_completed` — Permanently delete every completed reminder whose completion_date falls in [start, end).
- `bulk_move` — Move a list of reminder IDs to a target calendar.
- `complete_reminder` — Mark a reminder as completed.
- `create_calendar` — Create a new reminder calendar (list) in Apple Reminders.
- `create_reminder` — Create a new reminder in Apple Reminders.
- `delete_calendar` — Delete a reminder calendar (list).
- `delete_reminder` — Permanently delete a reminder.
- `get_calendar` — Get a specific calendar (list) by name.
- `get_calendar_by_id` — Get a specific calendar (list) by its unique ID.
- `get_completed_in_range` — Return reminders whose completion_date falls in [start, end).
- `get_default_calendar` — Get the default calendar (list) for new reminders.
- `get_next_reminder` — Get the next upcoming incomplete reminder based on due date.
- `get_overdue_reminders` — Get all incomplete reminders that are overdue (due date is in the past).
- `get_reminder` — Get a specific reminder by its unique ID.
- `get_reminders` — Get reminders with optional filters.
- `get_subtasks` — Get the subtasks of a reminder.
- `get_today_reminders` — Get all reminders due today (both completed and incomplete).
- `get_workflow_lists` — Get all workflow lists (calendars starting with 'Claude-').
- `list_calendars` — List all available reminder calendars (lists).
- `move_reminder_active` — Move a reminder to the 'Claude-Active' workflow list.
- `move_reminder_blocked` — Move a reminder to the 'Claude-Waiting' workflow list.
- `move_reminder_done` — Move a reminder to the 'Claude-Done' workflow list.
- `move_reminder_on_deck` — Move a reminder to the 'Claude-On-Deck' workflow list.
- `move_reminder_to_list` — Move a reminder to a different calendar/list.
- `search_calendars` — Search for calendars (lists) by partial name match.
- `search_reminders` — Search for reminders by text query.
- `set_alarm` — Set or clear time-based alarm(s) on a reminder.
- `set_location_alarm` — Add a geofenced (location-based) alarm to a reminder.
- `set_parent` — Reassign or detach a reminder's parent.
- `set_recurrence` — Set a recurrence rule on a reminder.
- `triage_brain_dump` — Triage the brain-dump list using the client's LLM via MCP Sampling.
- `uncomplete_reminder` — Mark a reminder as incomplete/not done.
- `update_calendar` — Rename an existing reminder calendar (list).
- `update_reminder` — Update an existing reminder.

## Resources

- `reminders://default` — Default list
- `reminders://overdue` — Overdue reminders
- `reminders://today` — Today's reminders

## Resource templates

- `agents://current/{project_name}` — Agents visibility plane
- `reminders://list/{calendar_id}` — Specific list

## Prompts

- `agent_visibility_sync(project_name)` — Surface the `Agents-<project>` reminder list so the agent can sync its current todos there.
- `brain_dump_triage(list_name)` — Pull every reminder from the `Claude-Brain-Dump` list and propose where each one should go (active / on-deck / waiting / done)..
- `daily_review()` — Quick AM/PM review prompt: surfaces today's reminders + everything overdue, plus a brief agenda for triage.
- `weekly_retro(window_days)` — Weekly retro: last 7 days of completed work + still-open items.
