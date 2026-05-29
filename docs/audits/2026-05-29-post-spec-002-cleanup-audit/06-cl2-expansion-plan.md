# CL-2 Capability Expansion — plan (2026-05-29)

> Approved by Pierce 2026-05-29: **full autonomous build** (commit+push per slice,
> like CL-1) + **recurrence/alarm read-back via tail-append + ADR**. Grounded in
> the actual compiled `_native/src/rem_reminderkit.m` action surface (verified by
> reading the dispatch), not audit hearsay.

## Helper actions: compiled vs exposed

The Obj-C ReminderKit helper already implements these; **bold = no Python surface yet**:
create_list✅, create_group✅, delete_group✅, move_list_to_group✅, add_tags✅,
assign_section✅, set_flagged✅, create_subtask✅ — and unexposed:
**create_smart_list, update_smart_list, delete_smart_list, set_list_appearance,
set_list_pinned, set_smart_list_pinned, create_template, apply_template,
delete_template, categorize_grocery_items, set_urgent, set_early_reminder,
add_subtasks, add_section_and_assign, add_attachments, add_url_attachments,
add_private_metadata**. `clear_tags` is NOT implemented (needs a new `.m` action).

## Module / cap strategy (8 public entry points per module)

`reminderkit_actions.py` is already at 7 — cannot absorb 16 more. New wrapper modules:
- `_native/reminderkit_lists.py` — smart-list + appearance + pinning wrappers
- `_native/reminderkit_content.py` — templates + grocery + attachments wrappers
- `_native/reminderkit_flags.py` — urgent / early-reminder / add_subtasks / add_section_and_assign
New tool modules: `tools/{smartlists,appearance,templates,grocery,flags,attachments}.py`
(each ≤8). All registered via `tools/__init__.py`. Watch `check_module_rules` after each.

## Slices (ordered; each = wrapper(s) + tool(s) + test + gates + signed commit + push)

- **CL-2.1 Smart lists** — create/update/delete_smart_list + set_smart_list_pinned tools; `reminders://smartlists` resource.
- **CL-2.2 List appearance & pinning & groups** — set_list_appearance (color/icon/symbol), set_list_pinned; `update_group` (rename/appearance for groups).
- **CL-2.3 Templates** — create/apply/delete_template tools; `plan_from_template` prompt.
- **CL-2.4 Grocery** — categorize_grocery_items tool; `grocery_capture` prompt.
- **CL-2.5 Reminder flags & extras** — set_urgent, set_early_reminder, add_subtasks (batch), add_section_and_assign tools.
- **CL-2.6 Attachments** — add_url_attachment + add_metadata tools; file-path add_attachment behind the S4.4 kill-switch + path validation.
- **CL-2.7 Read-side** — get_recently_deleted (invert ZMARKEDFORDELETION) + `reminders://recently-deleted`; flagged/urgent query filters on get_reminders; fix the ZPARENTREMINDER discard so parent_reminder_id/has_subtasks populate.
- **CL-2.8 clear_tags** — new `clear_tags` action in `rem_reminderkit.m` (+ `make build-native` recompile) + wrapper + tool; `reminders://tags` resource.
- **CL-2.9 Read-back (ADR 0002)** — tail-append recurrence/has_alarm/alarm-summary fields to `Reminder` (S0.3 freeze tail-add) + read ZREMCDRECURRENCERULE/ZREMCDALARM in `_sqlite_helpers`; update field-order lock test.
- **CL-2.10 ToolAnnotations** — readOnly/destructive/idempotent/openWorld hints + human titles on every tool.
- **CL-2.11 Typed result models** — DeleteResult/BulkResult/MoveResult/AlarmResult/etc. (frozen, tail-safe) → the 12 bare `-> dict` tools emit structuredContent.
- **CL-2.12 Resources + Prompts polish** — Context-injection + titles on existing; new `organize_into_sections` prompt; per-param `Field(description=...)` on high-traffic tools.
- **CL-2.13 Regenerate catalog + docs sweep** — `make gen-tools-doc`; refresh README/AGENTS/TASK_STATE counts; CHANGELOG.

## Standing constraints

Signed commit + VERSION bump + push per slice; four gates green each (ruff/black, mypy,
check-architecture, the §3 trio). Models are tail-append only (S0.3 freeze). Attachments
file-paths are privileged — gate behind the kill-switch, never escalate access silently.
