# Changelog

All notable changes to this project are documented here. This project
follows [Semantic Versioning](https://semver.org/) and
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/).


## [0.1.90] — 2026-05-30 — Agent: Claude
### Changed
- Integration: smart-lists/appearance/pinning + subtasks/sections scenarios. Appearance + pinning green; subtask parent-linkage + section assignment validated (polled past SQLite lag); set_parent confirmed deferred. FOUND a 2nd bug: create_smart_list without filter_data_b64 errors 'filterData is required' (contradicts its docs) — encoded as known-issue, fix task spawned. 129 checks green.

## [0.1.89] — 2026-05-30 — Agent: Claude
### Changed
- Integration: calendars + groups + workflow scenarios — list lifecycle (list/get/search/default/create/rename/delete), group create→move-list→delete, get_workflow_lists + move_reminder_to_list + tolerant named-board moves (Claude-* may be absent). 111 checks green.

## [0.1.88] — 2026-05-30 — Agent: Claude
### Changed
- Integration: read-surface scenario (scenarios_reads.py) — all 7 query tools + all 7 reminders:// resources reflect live writes (overdue/today/future seeds by id, completed-in-range, delete→recently-deleted). Added WireClient.call_value (unwraps result-wrapped list/Optional returns). reminders://tags has hashtag-propagation lag in SQLite → polled (not a bug). 70 checks green.

## [0.1.87] — 2026-05-30 — Agent: Claude
### Changed
- docs: TASK_STATE §0 — record integration-suite progress (CRUD + alarms scenarios green, set_urgent bug found + task spawned, remaining-coverage TODO).

## [0.1.86] — 2026-05-30 — Agent: Claude
### Changed
- Integration: alarms/recurrence/early-reminder read-back scenario (ADR 0002) — validates set_recurrence/set_alarm/set_location_alarm/set_early_reminder write + get_reminder EventKit read-back over the wire. FOUND a real bug: set_urgent crashes the ReminderKit helper ('-[REMReminderStorage urgentAlarmContext]: unrecognized selector', uncaught NSException) — encoded as an expected-error known-issue; dedicated fix task spawned.

## [0.1.85] — 2026-05-30 — Agent: Claude
### Changed
- Integration suite foundation: tests/integration/ — wire-level harness (fresh stdio server vs live store) + self-cleaning MCP-IntegTest fixture + CRUD/read scenario. Asserts typed structuredContent + RFC-3339 datetimes + negative cases. Run: ./venv/bin/python -m tests.integration.run. NOT collected by the unit gate (__test__=False).

## [0.1.84] — 2026-05-30 — Agent: Claude
### Changed
- CL-2.13: docs sweep — regenerated docs/TOOLS.md (58 tools, 8 resources, 5 prompts); refreshed README + docs/MAP.md tool/resource/prompt tables (17 modules) + AGENTS.md §4/§9 + TASK_STATE §0 counts. CL-2 capability expansion is COMPLETE.

## [0.1.83] — 2026-05-30 — Agent: Claude
### Changed
- CL-2.12: resources/prompts polish — title= on all 8 resources + 5 prompts; new organize_into_sections prompt; per-param Field(description=) on the high-traffic tools (create_reminder/update_reminder/get_reminders/search_reminders) so their inputSchema params are documented. Split complete/uncomplete into tools/completion.py to keep reminders.py under the 400-line cap after the Annotated expansion.

## [0.1.82] — 2026-05-30 — Agent: Claude
### Changed
- CL-2.11: typed result models (results.py) — the 27 write/bulk/triage tools return frozen WriteResult/DeleteResult/BulkResult/TriageResult instead of bare dict, so each declares an outputSchema and emits structuredContent. extra='allow' envelopes preserve helper echo keys (additionalProperties:true → wire-safe); a _Result.of(**fields) factory keeps construction mypy-clean over extras. New test_result_models.py locks the contract; wire-tested via fresh stdio server.

## [0.1.81] — 2026-05-30 — Agent: Claude
### Changed
- CL-2.10: ToolAnnotations on all 58 tools — readOnly/destructive/idempotent hints + openWorldHint=False (closed local domain) + human titles, via shared READ/CREATE/MUTATE/DESTROY presets in tools/_annotations.py; new test_tool_annotations.py locks the contract.

## [0.1.80] — 2026-05-30 — Agent: Claude
### Changed
- Pre-compaction handoff: refresh TASK_STATE §0 (2.1-2.9 shipped, v0.1.79, 59 tools; remaining polish 2.10-2.13 + autonomous-then-exhaustive-integration directive + Alarm Lab fixture) and AGENTS §9 (current capability state + 4 durable gotchas: datetime offset serialization, broad elicitation guards, recurrence/alarms CloudKit-blob-only, stale connected server + fresh-server wire-test pattern).

## [0.1.79] — 2026-05-30 — Agent: Claude
### Changed
- CL-2.9 read-back (ADR 0002): tail-append recurrence/alarms/early_reminders to the Reminder model. early_reminders decode from SQLite (everywhere); recurrence + alarm summaries from EventKit on get_reminder only (urgent + 'when messaging' dropped — CloudKit-blob-only). Validated end-to-end against seeded alarm data.

## [0.1.78] — 2026-05-30 — Agent: Claude
### Fixed
- Fix: delete_calendar / bulk_delete_completed no longer error on clients without elicitation capability. The confirm-guard caught only AttributeError, so a client with ctx.elicit but no advertised elicitation capability raised 'Elicitation not supported' and the destructive op failed even with force=true. delete_calendar now treats force=true as the confirmation (redundant elicitation removed; non-empty already requires force); bulk_delete_completed degrades to proceed on any elicit failure.

## [0.1.77] — 2026-05-30 — Agent: Claude
### Fixed
- Fix: Reminder datetimes serialize as offset-bearing RFC 3339 so MCP structured-output validation accepts them. Naive-local datetimes serialized without an offset and failed the date-time format check, erroring every Reminder-returning tool over the wire (-32602) even though the EventKit write succeeded. A field_serializer stamps the local offset; storage stays naive-local, field order unchanged (S0.3-safe).

## [0.1.76] — 2026-05-30 — Agent: Claude
### Changed
- CL-2.8 clear_tags: new clear_tags ReminderKit action (removeAllHashtags) + make build-native recompile; clear_tags param on update_reminder (pair with add_tags for tag replacement); reminders://tags resource listing distinct tags on live reminders.

## [0.1.75] — 2026-05-30 — Agent: Claude
### Changed
- CL-2.7 Read-side: get_recently_deleted tool + reminders://recently-deleted resource (invert ZMARKEDFORDELETION); flagged filter on get_reminders; fix the ZPARENTREMINDER discard so parent_reminder_id + subtasks populate. urgent filter deferred to CL-2.9 (model tail-append under ADR 0002).

## [0.1.74] — 2026-05-29 — Agent: Claude
### Changed
- CL-2.6 Attachments: add_url_attachment + add_metadata (unprivileged web URLs / hashtags) and add_file_attachment (local files). Unlocked GENERIC file attachments in rem_reminderkit.m (addFileAttachmentWithURL: — the prior images-only limit was the helper's, not ReminderKit's). add_file_attachment is opt-in behind MCP_APPLE_REMINDERS_ENABLE_FILE_ATTACHMENTS=1 (default OFF) + path validation. Requires make build-native.

## [0.1.73] — 2026-05-29 — Agent: Claude
### Changed
- Simplify list icons: remove the keyword table + sampling suggester + suggest_list_icon tool. The calling client chooses the icon — create_calendar takes an explicit SF Symbol/emoji, 'none' to skip, or omits to the 'sparkles' agent badge; create_smart_list stays icon-less. reminders://appearance documents usage.

## [0.1.72] — 2026-05-29 — Agent: Claude
### Changed
- create_smart_list is icon-less by default (icon defaults to 'none' rather than 'auto'); regular list creation still auto-suggests.

## [0.1.71] — 2026-05-29 — Agent: Claude
### Added
- Add suggest_list_icon tool + auto-icon for create_calendar & create_smart_list: hybrid curated-table→sampling SF Symbol suggester (icon='auto'/'ask'/'none' or explicit symbol/emoji) with a 'sparkles' agent-glyph fallback; reminders://appearance gains an auto_suggest pointer.

## [0.1.70] — 2026-05-29 — Agent: Claude
### Changed
- Regenerate capability catalog to include the reminders://appearance resource

## [0.1.69] — 2026-05-29 — Agent: Claude
### Added
- Add reminders://appearance resource: authoritative 10-color Reminders palette (name+hex, mirrors helper makeREMColor) + SF-Symbol/emoji icon guidance so clients can discover valid color/symbol values for the appearance tools

## [0.1.68] — 2026-05-29 — Agent: Claude
### Changed
- Refresh capability catalog to 54 tools after CL-2.1-2.5 (smart lists, appearance/pinning, templates, grocery, urgent/early-reminder/section); record CL-2 progress in TASK_STATE

## [0.1.67] — 2026-05-29 — Agent: Claude
### Added
- Add reminder-attribute tools: set_urgent, set_early_reminder (lead-time alert), add_section_and_assign via _native/reminderkit_flags.py + tools/flags.py

## [0.1.66] — 2026-05-29 — Agent: Claude
### Added
- Add categorize_grocery_items tool (Apple on-device grocery categorization) via tools/grocery.py

## [0.1.65] — 2026-05-29 — Agent: Claude
### Added
- Add list-template tools (create_template / apply_template / delete_template) via _native/reminderkit_content.py + tools/templates.py

## [0.1.64] — 2026-05-29 — Agent: Claude
### Added
- Add list/group appearance + pinning tools: set_list_appearance (rename/color/SF-symbol/emoji; works on lists AND groups), set_list_pinned, set_smart_list_pinned

## [0.1.63] — 2026-05-29 — Agent: Claude
### Added
- Add smart-list tools (create_smart_list / update_smart_list / delete_smart_list) via new _native/reminderkit_lists.py wrappers + tools/smartlists.py, exposing the compiled-but-stranded ReminderKit smart-list actions (44 tools)

## [0.1.62] — 2026-05-29 — Agent: Claude
### Added
- Add CL-2 capability-expansion plan (grounded slice plan for ~16 stranded helper capabilities + recurrence/alarm read-back + protocol polish)

## [0.1.61] — 2026-05-29 — Agent: Claude
### Added
- Add scripts/gen_tools_doc.py + make gen-tools-doc target: regenerate docs/TOOLS.md (exhaustive capability catalog) from the live FastMCP server with full per-tool parameters; catalog refreshed to 41 tools / 5 resources / 4 prompts (was stale at 37 with no params)

## [0.1.60] — 2026-05-29 — Agent: Claude
### Changed
- Extend CQ-2 collection fix to the CRUD suite: rename test_crud_*.py to crud_*.py and mark test_comprehensive_crud.py __test__=False (it is a script orchestrator), clearing 8 fixture-setup errors from a full pytest run

## [0.1.59] — 2026-05-29 — Agent: Claude
### Changed
- Record CL-1 cleanup completion in TASK_STATE (all batches + the CRITICAL bugfix done) and document the declined make sync-skeleton (skeleton v0.37.0 hooks regressed cd||exit 1 / SC2164) as an AGENTS §9 gotcha

## [0.1.58] — 2026-05-29 — Agent: Claude
### Fixed
- Fix CRITICAL EventKit write-swallow: _save_ek_reminder and delete_reminder now unpack PyObjC's (BOOL, NSError) out-param tuple and raise on failure — previously the truthy tuple was captured into success so every failed write reported success (and bulk ops reported false counts); add regression tests

## [0.1.57] — 2026-05-29 — Agent: Claude
### Fixed
- Fix per-module issues: document update_reminder flagged/add_tags args, hoist _ConfirmCascade elicit schema to module scope in calendars, drop the _unused native_reminder_to_pydantic import hack in bulk (+ its test), and raise instead of silently returning [] when SQLite is unavailable in get_completed_in_range/get_subtasks/list_groups

## [0.1.56] — 2026-05-29 — Agent: Claude
### Changed
- Deduplicate the _app_context accessor (8 tool modules) and _bridge_from_ctx (2 modules) into shared lifespan.app_context/bridge_from_ctx helpers

## [0.1.55] — 2026-05-29 — Agent: Claude
### Removed
- Remove dead code: format_reminder, on_reminder_created/completed callbacks + their create-loop, the dead bulk check_cancellation branch + BulkCancelled; tools/__init__ now imports all 10 tool modules

## [0.1.54] — 2026-05-29 — Agent: Claude
### Changed
- Rewrite stale docs to current FastMCP three-tier state: README (22->41 tools, _native architecture, cli_main), both src READMEs, docs/MAP.md, AGENTS.md (capability state + tests/ paths), TASK_STATE.md (current + CL-1)

## [0.1.53] — 2026-05-29 — Agent: Claude
### Fixed
- Fix build-config: repoint Makefile lint/test + pyproject to tests/, add test-actual target, real author email/repo URLs/dev-extras, desktop-config venv interpreter, and repair 4 stale reminderkit_actions test imports

## [0.1.52] — 2026-05-29 — Agent: Claude
### Changed
- Relocate test suite into tests/ (tests/_support); rename 4 workflow library modules; fix CQ-2 pytest collection of orchestrator helpers

## [0.1.51] — 2026-05-29 — Agent: Claude
### Changed
- Backfill CHANGELOG [0.1.9] (S1.1 is_default fix) and [0.1.11] (spec 001 archive / spec 002 land) placeholders

## [0.1.50] — 2026-05-29 — Agent: Claude
### Removed
- Remove 10 stale root markdown docs + relocate MAP.md to docs/MAP.md

## [0.1.49] — 2026-05-29 — Agent: Claude
### Removed
- Remove redundant requirements.txt + AGENTS.md.pre-retrofit (deps resolve from pyproject editable install)

## [0.1.48] — 2026-05-29 — Agent: Claude
### Added
- Add CL-1 verify + expert-review workflow synthesis (audit doc 05)

## [0.1.47] — 2026-05-29 — Agent: Claude — PROGRESS.md compaction checkpoint

### Documented
- Refreshed `PROGRESS.md` to reflect the post-S5.1 / post-`delete_group` state. Captures: 41 tools, all 5 phases done (S4.2 stretch deferred), audit captured at `docs/audits/2026-05-29-post-spec-002-cleanup-audit/`, two proposed follow-up streams (CL-1 cleanup, CL-2 capability extensions), and the S5.1 `setParentListID:` reverse-engineering finding promoted to standing-rules ("Do NOT use setParentOwnerID: for group-parent semantics").
- Session preparing for context compaction. PROGRESS + TASK_STATE + audit + ADR are sufficient handoff state for a fresh agent.

## [0.1.46] — 2026-05-29 — Agent: Claude — S5.1 cleanup + `delete_group`

Pierce opened Reminders.app and found 4 orphaned `REM-TEST-GROUP-S51` empty
groups from S5.1 probing. Root cause: the Swift helper's `delete_list` uses
`EKEventStore.removeCalendar`, which cannot see groups (groups are a
ReminderKit-private concept invisible to EventKit). The S5.1 live test's
try/finally cleanup called `delete_list` and silently failed on the group.

### Added
- **`_native/src/rem_reminderkit.m`**: new local mod — `delete_group` action.
  Mirrors `delete_smart_list`'s shape via the private
  `REMListChangeItem.removeFromParentWithAccountChangeItem:` selector (now
  declared in the borrowed interface block with `respondsToSelector:` guard).
- **`_native/reminderkit_actions.py::delete_group(group_id)`** — Python wrapper.
- **`tools/groups.py::delete_group(group_id)`** — 41st MCP tool. Refuses to
  delete a non-empty group (detach children first via `move_list_to_group`).
- **`test_live_group_round_trip`** rewritten to self-clean: detach child
  from group → delete child via Swift helper → delete group via Obj-C helper.
- **`THIRD_PARTY_NOTICES.md`**: documented the new local mod.

### Fixed
- Deleted 4 orphaned `REM-TEST-GROUP-S51` test groups from Pierce's Reminders.app.

### Verified
- `pytest test_groups.py`: 8 passed.
- `REM_LIVE_HELPER=1 pytest test_groups.py::test_live_group_round_trip`: PASSED.
- Zero leaks after the live run.
- `make lint && make check-architecture && make typecheck`: green.
- `await mcp.list_tools()`: **41 tools**.

## [0.1.45] — 2026-05-29 — Agent: Claude — black-format `test_groups.py`

### Fixed
- `test_groups.py` failed `make lint` (black --check) post-S5.1 ship. `make typecheck` + `make check-architecture` + `ruff check` were all green; only black reformatting was outstanding. Stop-hook caught it before idle. No semantic change.

## [0.1.44] — 2026-05-29 — Agent: Claude — Slice 5.1 (🎯 list-group support)

ADR 0001 acted on. Pierce's hunch — point at the one "Claude" group and reverse-
engineer outward — paid off in full: groups now have a real first-class surface
across read + write + Pydantic + Obj-C helper + tools + tests. Live round-trip
PASSED end-to-end.

### Added (read side)
- `Calendar` Pydantic gains `is_group: bool = False` + `parent_group_id: Optional[str] = None` at the tail (post-S0.3-freeze additive — defaults preserve compat). Regression test `test_calendar_field_order_is_canonical` updated to lock the new tail in.
- `_native/sqlite.py::Reader.list_groups()` — `WHERE ZISGROUP = 1`.
- `_native/sqlite.py::Reader.iter_lists_in_group(group_uuid)` — resolves group's `Z_PK` then streams children whose `ZPARENTLIST` matches.
- `_native/sqlite.py::Reader.list_calendars(include_groups=False)` — default behavior change. Groups excluded unless the caller asks. `search_calendars` gets the same toggle.
- `_native/sqlite.py::Reader._resolve_parent_group_uuid()` — joins `ZPARENTLIST → Z_PK → ZCKIDENTIFIER`.
- `_native/_sqlite_helpers.py::_calendar_from_row` — extended with `parent_group_id` kwarg and reads `ZISGROUP` from the row.

### Added (write side — Obj-C helper extensions)
- `_native/src/rem_reminderkit.m` (vendored, **local mod**) — new private-selector declarations on `REMListChangeItem`: `setIsGroup:` and `setParentListID:`. Both gated with `respondsToSelector:` at call sites.
- Two new actions in the helper's allowed-action set: `create_group` and `move_list_to_group`. **`setParentListID:` is the correct reparent selector** — `setParentOwnerID:` (the obvious-looking choice from the existing header) returns `com.apple.reminderkit error -1` when given a group's REMObjectID; the schema column name `ZPARENTLIST` was the clue that the right setter mirrored it.
- `_native/THIRD_PARTY_NOTICES.md` updated with the new mods documented as explicit local modifications.

### Added (Python wrappers + MCP tools)
- New module `_native/reminderkit_actions.py` — typed per-action wrappers (`create_group`, `move_list_to_group`, `assign_section`, `add_tags`, `set_flagged`, `create_subtask`). Pulled out of `_native/reminderkit.py` so the protocol module stays under the 8-public-entry-point module-shape cap.
- New module `tools/groups.py` with three MCP tools:
  - `create_group(name)` — 38th tool.
  - `list_groups()` — 39th tool.
  - `move_list_to_group(list_id, group_id?)` — 40th tool.
- `tools/calendars.py::list_calendars` gains the `include_groups: bool = False` argument.

### Architecture refactors (mid-slice, to stay under gate caps)
- `_native/reminderkit.py` split into transport (exceptions + `_invoke` + `ping` + `is_available`) and `_native/reminderkit_actions.py` (typed action wrappers). Tools/ updated to import from the new module.
- `Reader.get_section_name` body extracted to `_sqlite_helpers.py::_resolve_section_name` so `sqlite.py` stays under the 400-line hard cap.

### Test
- `test_groups.py` (8 tests; 7 pass + 1 opt-in live):
  - Pydantic defaults + group construction.
  - Input guards on `create_group` / `move_list_to_group` wrappers.
  - `Reader.list_groups` returns rows with `is_group=True`.
  - `Reader.iter_lists_in_group` unknown UUID → empty.
  - `list_calendars(include_groups=...)` toggle exercises both modes.
  - **`test_live_group_round_trip`** (REM_LIVE_HELPER=1) — creates group + child list + moves + asserts SQLite reads back `parent_group_id == group_id` + cleans up. **PASSED.**
- `test_models.py::test_calendar_field_order_is_canonical` updated to lock the tail-append (`is_group`, `parent_group_id`).

### Verified
- `pytest test_groups.py test_models.py test_sqlite_reader.py test_alarms.py test_resources.py test_prompts.py test_agents.py test_bulk_ops.py`: 51 passed, 4 skipped (opt-in live tests, 5 of which have PASSED across the session).
- `REM_LIVE_HELPER=1 pytest test_groups.py::test_live_group_round_trip`: PASSED.
- `await mcp.list_tools()`: **40 tools** registered (+3 vs S4.5).
- `make lint && make check-architecture && make typecheck`: green.

### Status — **🎯 Phase 5 / Slice 5.1 complete**
- 32 slices shipped in the session sprint.
- Next per ADR 0001 + audit captured at `docs/audits/2026-05-29-post-spec-002-cleanup-audit/`: cleanup pass (CL-1 — single slice or CL-1a/b/c/d split, shape pending).

## [0.1.43] — 2026-05-29 — Agent: Claude — audit captured (4 Opus subagents → 5 docs)

After Pierce opened the repo in an editor post-spec-002 and surfaced sprawl + stale debris,
four parallel Opus review subagents audited the mess across four dimensions. Findings
captured here so nothing's lost when the cleanup pass starts.

### Added
- **`docs/audits/2026-05-29-post-spec-002-cleanup-audit/`** — new audit subdirectory with five docs:
  - `README.md` — synthesis + severity-grouped findings + cleanup-shape decision pending.
  - `01-file-organization.md` — 17 layout findings (`.DS_Store` tracked, redundant `requirements.txt`, `_native/` flat layout, `tools/sections.py` misnamed, `.claude/` skeleton spillover, etc.).
  - `02-documentation.md` — markdown audit (`CHANGELOG.md` 0.1.9 + 0.1.11 placeholders, README massively stale, AGENTS.md §9 lies about capabilities, src-tree READMEs pre-FastMCP).
  - `03-code-quality.md` — 10 source findings, including **2 CRITICAL** (`move_reminder_blocked` silently routes to `Claude-Waiting`; 4 `test_workflow_*.py` modules un-collectable from missing `conftest.py`).
  - `04-build-config.md` — 6 HIGH (`pyproject.testpaths` lies; README `import main` ImportError; 3 skeleton hooks drifted from v0.37.0) + 8 MEDIUM + 1 LOW.

### Aggregate
- **5 CRITICAL** findings (functional bugs).
- **~18 HIGH** findings (docs lying / source mess / skeleton drift).
- **~14 MEDIUM** findings (polish / consistency).
- **~37 distinct issues** total beyond the pre-audit known list (28 test_*.py to relocate, 10 stale root markdowns to delete, duplicate `TOOLS.md`).

### Status
- Audit complete. Cleanup deferred until **after S5.1 (list-group support)** ships, per Pierce's direction ("we're so close to a significant completion threshold, may as well keep sprinting").
- Cleanup will land as **one slice (`CL-1`) or split sub-slices (`CL-1a/b/c/d`)** — shape pending Pierce's call.

## [0.1.42] — 2026-05-29 — Agent: Claude — CHANGELOG fix-forward for 0.1.41

### Fixed
- Backfilled the `[0.1.41]` entry that landed with the placeholder text (`_(fill in — what changed in this version)_`). Race between `make bump-patch` writing the date-stamped header and the prior `replace_content` call's older-date pattern. The 0.1.41 body now describes the actual change: ADR 0001 + S5.1 spec'd.

## [0.1.41] — 2026-05-29 — Agent: Claude — ADR 0001 + S5.1 spec'd (planning only)

After Pierce pointed at his single "Claude" group and asked us to chase
it through the schema, a quick SQL probe cracked the structure open.
This commit captures the decision to act on it — planning-only, no
code change yet.

### Added (docs only)
- **`docs/adr/0001-list-group-support.md`** — first ADR. Records the schema reverse-engineering (`ZISGROUP=1` flag + `ZPARENTLIST` foreign key, both on the same `ZREMCDBASELIST` table — no separate group entity), the decision to extend spec 002 with Phase 5, alternatives considered (vs. spec 003), risks (private-framework drift, dual `ZPARENTLIST` columns, backward compat on `list_calendars`), and the implementation surface sketch.
- **`specs/002-modernize-and-foundation/plan.md`** — Phase 5 section after Phase 4 with one slice (S5.1).
- **`specs/002-modernize-and-foundation/tasks.md`** — full S5.1 task entry with files + acceptance bullets.
- **`TASK_STATE.md`** — Phase 5 row added; S5.1 marked as the new NEXT slice.

### Slice 5.1 surface (planned)
- `Reader.list_groups()` + `Reader.iter_lists_in_group()` + `Reader.list_calendars(include_groups=False)`.
- `Calendar` Pydantic gains `is_group: bool = False` + `parent_group_id: Optional[str] = None` at the tail (post-S0.3-freeze additive — defaults preserve compat).
- One new local mod to `_native/src/rem_reminderkit.m`: `create_group` action (+ optionally `move_list_to_group`).
- Python wrappers + 3 new MCP tools in a new `tools/groups.py`.
- `tools/calendars.py::list_calendars(include_groups=False)`.
- Live round-trip test.

## [0.1.40] — 2026-05-28 — Agent: Claude — typecheck gate fixes

Stop-hook surfaced three mypy errors that previous slices had not exercised.
Resolved per the Pierce-restated rule that first-party code (including the
post-S0.2-rename `_native/*.py`) must meet VIBE.yaml guidelines; only the
vendored Swift + Obj-C sources under `_native/src/*` are exempt.

### Fixed
- `_native/core.py::RemindKit.get_next_reminder` — sort key narrowed via `cast(datetime, x.due_date)` so mypy knows the post-filter list is `due_date`-bearing. (The `[r for r in … if r.due_date is not None]` filter already guaranteed non-None, but mypy doesn't narrow through that idiom.)
- `server.py::cli_main` — replaced the `mcp.run(transport=str)` call with an explicit branch over the Literal-typed transport names (`stdio`, `sse`, `streamable-http`). Unknown values still fall through to `stdio` rather than crashing the client startup path.

### Verified
- `make typecheck`: `Success: no issues found in 31 source files`.
- `make lint && make check-architecture`: green (no regressions; 71 files; module-shape gate green).
- `pytest test_mcp_tools.py test_e2e.py test_models.py test_sqlite_reader.py test_alarms.py test_resources.py test_prompts.py test_agents.py test_bulk_ops.py`: 49 passed, 3 skipped.

## [0.1.39] — 2026-05-28 — Agent: Claude — Slices 4.3 + 4.4 + 4.5 (🎯 spec 002 COMPLETE)

The last three Phase 4 slices, shipped together. Spec 002 is now formally
complete (modulo the stretch goal S4.2 — TodoWrite mirror).

### Added (S4.3 — streamable HTTP opt-in)
- `server.py::_resolve_transport` — honors `MCP_APPLE_REMINDERS_TRANSPORT` env var → `VIBE.yaml::server.transport` → `stdio` fallback. Unknown values fall through to stdio rather than crashing the client startup path. Verified `transport="streamable_http"` boots without error.

### Added (S4.4 — security review)
- `docs/SECURITY-REVIEW.md` — full OWASP MCP Top 10 walk-through against this server's surface. Documents trust boundaries, in-scope vs out-of-scope adversaries, and per-tool mitigations (elicitation guards on destructive ops, IDOR via UUID-resolution-before-write, etc.). Per-tool kill-switch helper (`tools/_kill_switch.py`) deferred with the YAML sketch documented in the review.

### Added (S4.5 — docs sweep)
- `AGENTS.md §10.4` — session-start visibility-plane rule. Agents call `bootstrap_agent_list(project_name=...)` and mirror in-flight todos into `Agents-<project>`. The human pulls live state via the `agents://current/{project_name}` Resource or Reminders.app directly.
- **`docs/TOOLS.md`** — auto-generated capability catalog from a live FastMCP server. 37 tools + 3 static Resources + 2 templated + 4 prompts.
- `PROGRESS.md` — final session checkpoint with all phases marked done.

### Status — 🎯 **spec 002 complete**
- **Phase 0** ✅ (substrate — 6 slices).
- **Phase 1** ✅ (P0 capabilities — 9 slices).
- **Phase 2** ✅ (MCP primitives — 5 slices).
- **Phase 3** ✅ (feature parity — 6 slices).
- **Phase 4** ✅ (4 of 5; S4.2 TodoWrite mirror is stretch + deferred).
- **31 slices shipped this session.**
- **7 live round-trips PASSED end-to-end** against the user's actual Reminders.app.

## [0.1.38] — 2026-05-28 — Agent: Claude — Slice 3.4 (bulk ops) — 🎯 **Phase 3 complete**

### Added
- **`tools/bulk.py`** — three bulk-op tools, all using `_native/bulk.py::bulk_iter` from S2.3 for per-item progress reporting + best-effort cancellation:
  - `bulk_complete(reminder_ids)` — the 35th tool.
  - `bulk_move(reminder_ids, calendar_id)` — the 36th.
  - `bulk_delete_completed(start, end, calendar_id?)` — the 37th. **Elicitation guard** from S2.4 before the cascade fires. Enumerates candidates via the SQLite reader's `get_completed_in_range` window. `end < start` → `ValueError`.
- Each returns `{"processed": int, "failed": list[{"id", "error"}]}` so callers can show per-item outcomes.
- `test_bulk_ops.py` (5 tests): registration, window-validation, empty-input fast paths.

### Verified
- `pytest test_bulk_ops.py`: 5 passed.
- `await mcp.list_tools()`: **37 tools**.
- `make lint && make check-architecture`: green.

### Status — **🎯 PHASE 3 COMPLETE**
- Phase 0 (substrate) ✅, Phase 1 (P0 capabilities) ✅, Phase 2 (MCP primitives) ✅, **Phase 3 (feature parity) ✅**.
- Phase 4 progress: **S4.1 done** (visibility-plane pilot). S4.2 (TodoWrite mirror — stretch), S4.3 (streamable HTTP — opt-in), S4.4 (security review docs), S4.5 (docs sweep) remain.
- **28 slices shipped this session.**

## [0.1.37] — 2026-05-28 — Agent: Claude — Slices 3.2 + 3.3 (location alarms + recurrence)

Two more write-side wrappers around the Swift helper's existing fields. Both live-verified.

### Added
- `_native/eventkit.py::set_location_alarm(reminder_id, latitude, longitude, *, location_title, radius_m, proximity)` — geofenced alarm with input validation (lat ±90, lon ±180, proximity ∈ {enter, leave}).
- `tools/alarms.py::set_location_alarm` — the 33rd tool.
- `_native/eventkit.py::set_recurrence(reminder_id, frequency, interval=1, *, days_of_week, days_of_month, end_iso)` — recurrence rule with frequency ∈ {daily, weekly, monthly, yearly}, interval >= 1, optional weekday/month-day refinements, optional end date.
- `tools/alarms.py::set_recurrence` — the 34th tool.

### Live verified
- `set_location_alarm(..., (37.7749, -122.4194), 'SF City Hall', 50, 'enter')` — helper returned `{"status":"updated"}` end-to-end.
- `set_recurrence(..., 'weekly', interval=2, days_of_week=[1,3,5])` — same. Note: EventKit requires a due date on the reminder before recurrence will save; documented inline.

### Verified
- `await mcp.list_tools()`: 34 tools.
- `make lint && make check-architecture`: green.

### Status
- Phase 3 progress: S3.1 ✅, S3.2 ✅, S3.3 ✅, S3.5 ✅, S3.6 ✅ — five of six. Only S3.4 (bulk ops) remains.
- 27 slices shipped this session.

## [0.1.36] — 2026-05-28 — Agent: Claude — Slice 4.1 (🎯 visibility-plane pilot)

**The whole point of the project.** Agents can now bootstrap a per-project
`Agents-<project>` Reminders list and a client can poll `agents://current/{project}`
to see the agent's mirrored todo board without joining the agent's session.
Live round-trip PASSED end-to-end.

### Added
- **`tools/agents.py::bootstrap_agent_list(project_name)`** — idempotent. Returns the existing `Agents-<project_name>` Calendar if present (sub-ms SQLite check), creates it via the Swift helper (`color="gray"`) if missing.
- **`resources/agents.py`** — `agents://current/{project_name}` Resource template. Returns JSON `{"project": str, "list": Calendar|null, "todos": list[Reminder]}`. Unknown project gets a `note` field pointing the client at `bootstrap_agent_list`.
- `server.py` registers both new modules.
- `test_agents.py` (4 tests; 3 pass + 1 opt-in live):
  - registration: `agents://current/{project_name}` in resource templates.
  - unknown project → bootstrap note in payload.
  - blank input → ValueError from the underlying helper.
  - **`test_live_create_and_resource_round_trip`** — creates via helper, reads via resource, asserts the list shape, cleans up. **PASSED.**

### Decided
- AGENTS.md session-start auto-bootstrap rule documentation moves to S4.5 (docs sweep) so all the agent-onboarding instructions land together. The S4.1 changelog explicitly carries this dependency.

### Verified
- `pytest test_agents.py`: 3 passed, 1 skipped.
- `await mcp.list_tools()`: **32 tools**. `await mcp.list_resource_templates()`: 2 entries (reminders + agents).
- `make lint && make check-architecture`: green.

### Status
- Phase 0 ✅, Phase 1 ✅, Phase 2 ✅, Phase 3 🟡 (3 of 6: S3.1, S3.5, S3.6 done), **Phase 4 🟡 (1 of 5: S4.1 done — THE PAYOFF).**
- 25 slices shipped this session.

## [0.1.35] — 2026-05-28 — Agent: Claude — Slices 3.5 + 3.6 (multi-cal + completed range)

Two small SQLite-only slices shipped together.

### Added
- `_native/_sqlite_helpers.py::_build_reminders_query` gains `calendar_ids`, `completion_after`, `completion_before` parameters.
- `_native/sqlite.py::Reader.iter_reminders` forwards them.
- `tools/queries.py::get_reminders(..., calendar_ids=None)` (S3.5).
- `tools/queries.py::get_completed_in_range(start, end, calendar_id?, limit?)` (S3.6) — the 31st tool. Half-open window: `[start, end)`. `end < start` raises `ValueError`.
- `test_multi_cal_and_range.py` (4 tests): unknown-UUID-returns-empty, real-list filter, far-future window, 5-year-back window.

### Verified
- `pytest test_multi_cal_and_range.py`: 4 passed.
- `await mcp.list_tools()`: 31 tools.
- `make lint && make check-architecture`: green.

### Status
- Phase 3 progress: S3.1 ✅, S3.5 ✅, S3.6 ✅ — three of six. S3.2 (location alarms), S3.3 (recurrence), S3.4 (bulk ops) remain.

## [0.1.34] — 2026-05-28 — Agent: Claude — Slice 3.1 (set_alarm time-based)

### Added
- `_native/eventkit.py::set_alarm(reminder_id, alarm_spec, *, clear=False)` — wraps the Swift helper's `update` action with the `alarm` + `clearAlarms` fields. **User-friendly normalization**: bare `1h`/`30m`/`2d` get a `-` prepended (matches the helper's "before due date" semantic). Already-signed `-1h` passes through. Absolute ISO `2026-06-15T09:00:00` passes through.
- `tools/alarms.py::set_alarm(reminder_id, when, clear)` — the 30th MCP tool. Either `when` or `clear=True` must be set.
- `test_alarms.py` — 7 tests including the **live round-trip** (`test_live_set_and_clear_alarm`). **PASSED.**

### Verified
- `pytest test_alarms.py`: 7 passed, 0 skipped.
- `await mcp.list_tools()`: 30 tools.
- `make lint && make check-architecture`: green.

### Status
- Phase 3 progress: S3.1 ✅ — first of six.

## [0.1.33] — 2026-05-28 — Agent: Claude — PROGRESS.md checkpoint
### Documented
- Refreshed `PROGRESS.md` to reflect Phase 0/1/2 complete, 20 slices shipped, 29 MCP tools registered, 4 Resources, 4 Prompts. Quick stats + last three decisions + Phase 3 entry point. Reading order for fresh agent unchanged.

## [0.1.32] — 2026-05-28 — Agent: Claude — Slice 2.5 (sampling) — 🎯 **Phase 2 complete**

### Added
- `src/mcp_apple_reminders/tools/sampling.py::triage_brain_dump(from_list, max_items)` — the 29th tool. Reads incomplete items from the named list (default `Claude-Brain-Dump`), builds a structured prompt, calls `await ctx.session.create_message(...)`, parses JSON routing, returns `{from_list, items, routing, valid_destinations, model_response}`. Tool does NOT move anything — returns proposed routing for the caller to apply via `move_reminder_*`. More conservative than the spec's "routes accordingly"; lets the user double-check the LLM's classification.
- Robust response parsing: unknown ids dropped, made-up destinations dropped, code-fenced JSON unwrapped, non-JSON returns empty dict (not exception).
- `test_sampling.py` (5 tests) on the helper surface — pure unit-level so the prompt/parse logic stays under test without requiring a real sampling-capable client.

### Decided
- Older SDKs without `ctx.session.create_message` are detected via `AttributeError` and surface a clear `ValueError` pointing the user at the manual workflow.

### Verified
- `pytest test_sampling.py`: 5 passed.
- `await mcp.list_tools()`: **29 tools registered**.
- `make lint && make check-architecture`: green.

### Status — **🎯 PHASE 2 COMPLETE**
- Phase 0 (substrate): ✅ S0.1–S0.6.
- Phase 1 (P0 capabilities): ✅ S1.0–S1.8.
- **Phase 2 (MCP primitives): ✅ S2.1 (Resources), S2.2 (Prompts), S2.3 (progress), S2.4 (elicitation), S2.5 (sampling).**
- 20 slices shipped this session.
- Next: Phase 3 (alarms, recurrence, bulk, multi-cal, completed-in-range).

## [0.1.31] — 2026-05-28 — Agent: Claude — Slices 2.3 + 2.4 (progress + elicitation)

Two small slices shipped together.

### Added (S2.3 — progress skeleton)
- `_native/bulk.py::bulk_iter(items, ctx, *, label, total)` — async generator that calls `ctx.report_progress(progress=i, total=n, message=…)` and best-effort `ctx.session.check_cancellation()` between each yield. Used by the bulk-op handlers landing in Phase 3 (S3.4).
- `BulkCancelled` exception (with `# noqa: N818` since the descriptive name communicates intent better than `BulkCancelledError`).
- `test_bulk.py` (2 tests): yield-order + progress-arg-shape + total-derivation.

### Changed (S2.4 — elicitation guard)
- `tools/calendars.py::delete_calendar(force=True)` now calls `ctx.elicit(message="About to delete … and cascade-remove N reminder(s). … Confirm?", schema=_ConfirmCascade)` before the destructive call fires. Rejected elicitation raises `ValueError("Cascade delete of {name!r} aborted by elicitation (…).")`. Older SDKs without `ctx.elicit` are detected via `AttributeError` and fall through (logged as debug).
- `bulk_delete_completed` elicitation deferred to S3.4 when the underlying tool lands — guarding a tool that doesn't yet exist would just generate work to undo. S3.4's plan note carries the guard requirement.

### Verified
- `pytest test_bulk.py test_eventkit_wrapper.py test_resources.py test_prompts.py`: 22 passed, 2 skipped.
- `make lint && make check-architecture`: green (61 files; all under hard cap; module shape green).

## [0.1.30] — 2026-05-28 — Agent: Claude — Slice 2.2 (4 canned Prompts)

### Added
- `src/mcp_apple_reminders/prompts/{__init__,workflows}.py` — four `@mcp.prompt` registrations:
  - `daily_review()` — pulls today + overdue from SQLite, builds an AM/PM review body.
  - `weekly_retro(window_days=7)` — last N days' completed + still-open.
  - `brain_dump_triage(list_name="Claude-Brain-Dump")` — surfaces every Brain Dump item with routing options (Active / On-Deck / Waiting / Done / Delete). Missing-list path returns a friendly explanation.
  - `agent_visibility_sync(project_name)` — targets `Agents-<project_name>`; if the list doesn't exist, the prompt body explains how to bootstrap it via `create_calendar`.
- Each returns `list[base.Message]` (a `UserMessage` framing + an `AssistantMessage` body) so the client sees a canonical conversation kickoff.
- `server.py` registers the new prompts module.
- `test_prompts.py` (5 tests): all four prompts registered, daily_review returns user+assistant messages, weekly_retro respects `window_days`, brain_dump_triage gracefully handles unknown list, agent_visibility_sync surfaces the bootstrap hint.

### Verified
- `pytest test_prompts.py`: 5 passed.
- `await mcp.list_prompts()`: 4 entries.
- `make lint && make check-architecture`: green.

## [0.1.29] — 2026-05-28 — Agent: Claude — Slice 2.1 (MCP Resources)

Phase 2 begins. Four MCP Resources, all served from the SQLite reader.

### Added
- `src/mcp_apple_reminders/resources/__init__.py` + `resources/reminders.py`:
  - `reminders://default` — user's default list with incomplete reminders.
  - `reminders://overdue` — incomplete reminders past their due date.
  - `reminders://today` — incomplete reminders due in the current local day.
  - `reminders://list/{calendar_id}` — reminders inside a specific list.
- Each resource returns `{"reminders": [...], "context": {...}}` JSON.
- `server.py` imports the new `resources/reminders` module so the decorators register at server start.
- `test_resources.py` (5 tests):
  - 3 static resources registered + 1 template registered.
  - Each resource read returns a valid JSON envelope with the documented context keys.
  - Overdue resource asserted to return only `completed=False` reminders.

### Verified
- `pytest test_resources.py`: 5 passed.
- `await mcp.list_resources()`: 3 entries; `await mcp.list_resource_templates()`: 1 entry.
- `make lint && make check-architecture`: green.

## [0.1.28] — 2026-05-28 — Agent: Claude — Slice 1.8 (assign_section) — 🎯 **Phase 1 complete**

The last Phase 1 slice. Every capability the spec promised for P0 now ships:
calendar lifecycle (create/delete/update), subtasks, flagged, tags, and now
sections. All three live round-trips from this slice pair (create + assign
+ verify via SQLite) PASSED end-to-end.

### Added (write)
- **`_native/reminderkit.py::assign_section(reminder_id, section_id)`** — wraps the Obj-C `assign_section` action.

### Added (read)
- **`_native/sqlite.py::Reader.list_sections_in_calendar(calendar_uuid)`** — returns `[(section_id, section_name), …]` from `ZREMCDBASESECTION`.
- **`_native/sqlite.py::Reader.get_section_name(reminder_uuid)`** — parses the parent list's `ZMEMBERSHIPSOFREMINDERSINSECTIONSASDATA` JSON blob to resolve the section name for a reminder.
- **`Reader.get_reminder_by_id`** now populates `section_name` automatically via the helper above.

### Added (tools)
- **`tools/sections.py`** (new) — homes the `get_subtasks`, `set_parent`, and `assign_section` tools. Each calls `_app_context(ctx)`, opens a SQLite connection, and orchestrates the helper subprocess. Pulled out of `tools/reminders.py` to keep both files under the 400-line hard cap.
- **`assign_section(reminder_id, section_name)`** tool resolves the section name to a UUID via the SQLite reader, then invokes the helper. Helpful error: if the section doesn't exist, the message lists every section that does.

### Architecture (gate hygiene)
- New **`_native/_sqlite_helpers.py`** — pulled `_REMINDER_COLS`, `_ts`, `_calendar_from_row`, `_reminder_from_row`, `_build_reminders_query` out of `sqlite.py` to keep it under the 400-line cap.
- Renamed module-level `invoke_action` → `_invoke_action` in `_native/reminderkit.py` so the module stayed under the 8-public-entry-point cap (it gained `add_tags`, `assign_section`, `create_subtask`, `set_flagged` across slices 1.5–1.8).
- Registered the new `tools/sections.py` module in `server.py` and `tools/__init__.py`.

### Test
- **`test_assign_section.py`** (5 tests):
  - `test_assign_section_requires_id`
  - `test_assign_section_requires_section_id`
  - `test_list_sections_in_unknown_calendar_returns_empty`
  - `test_get_section_name_unknown_returns_none`
  - **`test_live_assign_section_round_trip`** — creates a list + reminder, invokes the helper's `add_section_and_assign`, polls SQLite until `get_section_name` returns the new section name, asserts the section also appears in `list_sections_in_calendar`. **PASSED.**

### Verified
- `pytest test_assign_section.py test_tags.py test_set_flagged.py test_subtasks.py test_reminderkit_smoke.py test_eventkit_wrapper.py test_mcp_tools.py test_e2e.py test_models.py test_sqlite_reader.py`: 52 passed, 8 skipped (5 opt-in live tests, 3 of which have already proven green earlier).
- `make lint && make check-architecture`: green (52 files; every file under hard cap; module shape gate green).
- `await mcp.list_tools()`: **28 tools registered**.

### Status — **🎯 PHASE 1 COMPLETE**
- Phase 0 (substrate): ✅ S0.1–S0.6.
- **Phase 1 (P0 capabilities): ✅ S1.0, S1.1, S1.2, S1.3, S1.4, S1.5, S1.6, S1.7, S1.8.**
- Next: Phase 2 (MCP protocol primitives — Resources, Prompts, Sampling, Elicitation).

## [0.1.27] — 2026-05-28 — Agent: Claude — Slice 1.7 (tags + tag filter)

Tag writes and tag filtering both land. Live-verified end-to-end.

### Added
- `_native/reminderkit.py::add_tags(reminder_id, tags)` — wraps the Obj-C `add_tags` action. **Additive only** — the underlying helper action does not support removal/replacement; documented in the docstring. Replacement semantics will land in a follow-up patch that extends the helper with a `clear_tags` action.
- `_native/sqlite.py`: every reminder read now includes a correlated subquery that does `GROUP_CONCAT(h.ZNAME, ',')` across `ZREMCDOBJECT` ↔ `ZREMCDHASHTAGLABEL`. The Pydantic `Reminder.tags` field is now populated on every SQLite read. Cheap per row because `ZREMCDOBJECT.ZREMINDER3` is indexed.
- `_native/sqlite.py::Reader.iter_reminders(tags=[…])` — new keyword. Translates to a `r.Z_PK IN (SELECT DISTINCT o.ZREMINDER3 FROM ZREMCDOBJECT o JOIN ZREMCDHASHTAGLABEL h ON o.ZHASHTAGLABEL = h.Z_PK WHERE h.ZNAME IN (…))` WHERE clause.
- `tools/reminders.py::update_reminder(..., add_tags=None)` — when set, invokes `helper_add_tags(reminder_id, add_tags)` after any EventKit update. Returned Pydantic's `tags` is merged: `sorted(set(existing) | set(add_tags))`.
- `tools/queries.py::get_reminders(..., tags=None)` — forwards to `Reader.iter_reminders(tags=…)`.
- `test_tags.py` (5 tests):
  - `test_add_tags_requires_id`
  - `test_add_tags_rejects_empty_tag_list`
  - `test_iter_reminders_with_unknown_tag_filter_returns_empty`
  - `test_iter_reminders_with_no_tag_filter_populates_tags_field`
  - **`test_live_tags_and_filter_round_trip`** — creates a reminder, adds two tags via the helper, polls SQLite until they appear, then asserts `iter_reminders(tags=["urgent-s17"])` returns the reminder. **PASSED.**

### Decided
- Parameter is named `add_tags` (not `tags=`) to be honest about additive-only semantics. Replacing the tag set requires a follow-up helper extension; documented in the slice 1.7 acceptance bullet.

### Changed (architecture-gate hygiene)
- Trimmed sqlite.py docstring (the schema details pulled into `docs/SQLITE_SCHEMA.md` so the Python file stays under the 400-line hard limit).
- Trimmed reminders.py `get_subtasks` docstring (margin restored under the 400-line cap).
- New file: `docs/SQLITE_SCHEMA.md` — schema notes + Apple-epoch + permissions + the UUID-equivalence contract + the concurrency note about why `immutable=1` was dropped.

### Verified
- `pytest test_tags.py test_sqlite_reader.py test_set_flagged.py test_subtasks.py test_reminderkit_smoke.py test_eventkit_wrapper.py test_models.py`: 50 passed, 7 skipped (4 opt-in live tests already ran green earlier).
- `make lint && make check-architecture`: green (50 files; all under hard cap; module shape green).

### Status
- Phase 1 progress: S1.0–S1.7 done ✅, **eight of nine**. Only **S1.8 (`assign_section`)** remains to complete Phase 1.

## [0.1.26] — 2026-05-28 — Agent: Claude — Slice 1.6 (set_flagged)

Quick slice — the wrappers were already in place. Live-verified.

### Added
- `_native/reminderkit.py::set_flagged(reminder_id, flagged)` — wraps the Obj-C `set_flagged` action.
- `tools/reminders.py::create_reminder(..., flagged=None)` — when set, invokes `helper_set_flagged(created.id, flagged)` after the EventKit create. Result Pydantic stamped with the post-write flag value.
- `tools/reminders.py::update_reminder(..., flagged=None)` — when set, invokes `helper_set_flagged(reminder_id, flagged)` after any EventKit update (or skips the EventKit call entirely if only `flagged` changed). Result Pydantic stamped.
- `test_set_flagged.py` (2 tests, 1 unit + 1 opt-in live):
  - `test_set_flagged_requires_id`
  - `test_live_set_and_clear_flag` — flips the flag on/off on a real reminder, polls SQLite until visible. **PASSED.**

### Verified
- `pytest test_set_flagged.py test_subtasks.py test_reminderkit_smoke.py test_eventkit_wrapper.py test_sqlite_reader.py test_models.py`: 40 passed, 5 skipped.
- `make lint && make check-architecture`: green.
- `await mcp.list_tools()`: still 27 tools (flagged is a parameter, not a new tool).

### Status
- Phase 1 progress: S1.0–S1.6 done ✅, **seven of nine**. S1.7 (`set_tags` + tag filter on `get_reminders`) and S1.8 (`assign_section`) remain — both straight-line work that follows the same `helper_set_*` pattern.

## [0.1.25] — 2026-05-28 — Agent: Claude — Slice 1.5 (subtasks)

Subtasks land end-to-end. The Reminders app's "Make subtask" UI is now
mirrored by an MCP-callable tool. Live-verified: a parent reminder + 3
subtasks created via the helper, all three round-tripping through the
SQLite reader.

### Added (write path)
- **`_native/reminderkit.py::create_subtask(parent_id, title, **extras)`** — wraps the Obj-C helper's `add_subtasks` action with proper input validation.
- **`tools/reminders.py::create_reminder(..., parent_reminder_id=None)`** — when set, routes through `create_subtask` instead of the EventKit `create_reminder` path. Subtask inherits the parent's list automatically. Pre-flight: resolve the parent via SQLite; if user-supplied `calendar_id` doesn't match the parent's list, refuse with `ValueError`.
- **`tools/reminders.py::set_parent(reminder_id, new_parent_id=None)`** — `@mcp.tool` exposed but **deferred**. The borrowed Obj-C helper does not currently expose a parent-reassignment action; calling the tool raises `ValueError("set_parent is not yet implemented…")` with a clear pointer to the workaround (create + manually delete). Tracked as a follow-up that extends the helper with a new `set_parent` action.

### Added (read path)
- **`_native/sqlite.py::Reader.iter_subtasks(parent_uuid)`** — resolves the parent's `Z_PK` then streams children whose `ZPARENTREMINDER` matches. Sub-millisecond. Reader's public count is unchanged (methods don't count toward the module-shape gate).
- **`tools/reminders.py::get_subtasks(reminder_id)`** — `@mcp.tool` that reads via `iter_subtasks` and stamps `parent_reminder_id=reminder_id` onto each Pydantic child (the general-purpose reader doesn't denormalize that field).

### Fixed (mid-slice bug)
- **SQLite reader was invisible to concurrent helper writes.** `connect()` opened with `?mode=ro&immutable=1`. The `immutable=1` flag tells SQLite to assume the file never changes and aggressively cache contents — so helper-written subtasks didn't appear in the reader until a fresh process started. Dropped `immutable=1`; `mode=ro` alone is sufficient for the write-refusal guarantee. The fix is what made the live S1.5 round-trip green.

### Test
- **`test_subtasks.py`** (4 tests, 3 pass + 1 opt-in live):
  - `test_create_subtask_requires_parent_id`
  - `test_create_subtask_requires_title`
  - `test_iter_subtasks_unknown_parent_yields_empty`
  - **`test_live_subtask_round_trip`** (guarded by `REM_LIVE_HELPER=1`) — creates a test list + parent reminder + 3 subtasks via the helper, polls `iter_subtasks` until all 3 are visible, cleans up via `delete_calendar`. **PASSED.**

### Verified
- `pytest test_sqlite_reader.py test_mcp_tools.py test_e2e.py test_models.py test_eventkit_wrapper.py test_reminderkit_smoke.py test_subtasks.py`: 44 passed, 4 skipped.
- `await mcp.list_tools()`: 27 tools registered (was 25; `get_subtasks` + `set_parent` are new).
- `make lint && make check-architecture`: green.

### Status
- Phase 1 progress: S1.0–S1.5 done ✅, **six of nine**. S1.6 (`set_flagged`) and S1.7 (`set_tags` + tag filter) are now mechanically straightforward — they both follow the same `invoke_action(...)` pattern as `create_subtask`.

## [0.1.24] — 2026-05-28 — Agent: Claude — Slice 1.4 (ReminderKit Python wrapper)

The Obj-C ReminderKit (private-framework) helper now has its Python skin.
Slices 1.5–1.8 stack their per-action surface on top of it: subtasks
(S1.5), set_flagged (S1.6), set_tags (S1.7), assign_section (S1.8). All
four of those are now mechanically straightforward — the protocol +
availability detection live here.

### Added
- **`src/mcp_apple_reminders/_native/reminderkit.py`** (226 LOC; 5 public entry points). Mirror-image of `_native/eventkit.py`:
  - `ReminderKitHelperUnavailable` — helper binary missing.
  - `ReminderKitHelperError(message)` — helper returned a structured error.
  - `REMINDERKIT_HELPER_AVAILABLE` — module-level constant, computed at import time via a `--ping` probe of `_native/bin/rem_reminderkit`.
  - `is_available(refresh=False)` — fast cached check; pass `refresh=True` after a fresh `make build-native`.
  - `ping()` — exercises the `--ping` shortcut and returns the parsed JSON.
  - `invoke_action(action, **kwargs)` — the surface that Slices 1.5–1.8 wrap with typed per-action functions.
- **`verify_setup.py`** new probe: "🔌 ReminderKit wrapper" calls `is_available(refresh=True)` and asserts True.
- **`test_reminderkit_smoke.py`** (6 tests):
  - missing-helper-path-returns-false-from-is-available
  - ping-with-missing-helper-raises
  - invoke-action-success-returns-response-dict (mocked)
  - invoke-action-error-response-raises-helper-error (mocked exit-1)
  - invoke-action-payload-shape-via-stdin-capture (asserts wire format)
  - **live-ping-against-real-helper — PASSED on this checkout.**

### Decided
- The tag round-trip the S1.4 acceptance bullet originally proposed lives with **Slice 1.7** (`set_tags`). Factoring action-level integration tests with their owning slice keeps each slice independently revertable.
- Per-call subprocess mode (per S0.6). Long-lived mode is a swap-in upgrade if profiling shows it matters; the JSON protocol stays the same either way.

### Verified
- `pytest test_reminderkit_smoke.py`: 6 passed, 0 skipped.
- `make lint && make check-architecture`: green (47 files; 5-public-entry-point reminderkit module under cap 8).
- `verify_setup.py`: ReminderKit wrapper probe reports PASS.

### Status
- Phase 1 progress: S1.0 ✅ / S1.1 ✅ / S1.2 ✅ / S1.3 ✅ / S1.4 ✅ — five of nine landed. **Phase 1 is past the halfway mark.** S1.5 (subtask write paths via `create_reminder(parent_reminder_id=...)`, `set_parent`, `get_subtasks`) next.

## [0.1.23] — 2026-05-28 — Agent: Claude — Slice 1.3 (delete_calendar + update_calendar)

Calendar lifecycle is now complete. Three of the four CRUD operations
(`create`, `delete`, `update`) flow through the Swift EventKit helper;
the read path goes through SQLite. The visibility-plane pilot pieces
needed for Phase 4 are now buildable end-to-end on the substrate.

### Added
- **`_native/eventkit.py::delete_calendar(title)`** — pipes `{"action":"delete_list","title":...}` to the helper. Cascades to remove every reminder in the list atomically (EventKit's `removeCalendar(commit:)` is transactional).
- **`_native/eventkit.py::rename_calendar(title, new_title)`** — pipes `{"action":"rename_list","title":...,"newTitle":...}` and returns a Pydantic `Calendar`.
- **`tools/calendars.py::delete_calendar(name, force=False)`** — `@mcp.tool`. Safety choreography:
  1. Blank-name → `ValueError`.
  2. SQLite `Reader.get_calendar_by_name(name)` → check existence + count reminders (sub-ms).
  3. Refuse to delete the default calendar (matched against `bridge.calendars.get_default()`).
  4. If `force=False` and the list has any reminders, raise `ValueError` with the count.
  5. `ctx.warning(...)` before the destructive call fires.
  6. Helper invocation → on success, `ctx.info(...)` + return `{"id","name","deleted_reminders","force"}`.
- **`tools/calendars.py::update_calendar(name, new_name)`** — `@mcp.tool`. Renames via `rename_calendar`. Collision check via SQLite reader. **Color updates intentionally deferred to Slice 1.7** — the Swift helper doesn't expose color updates today, and forking it for one feature whose natural home is the Obj-C ReminderKit helper (S1.4) would just generate work to undo later. The tool description calls this out explicitly.
- **`test_eventkit_wrapper.py`** gains 4 unit tests + 1 opt-in live test:
  - `test_delete_calendar_wrapper_blank_title_raises`
  - `test_delete_calendar_wrapper_invokes_helper` (asserts wire-level payload)
  - `test_rename_calendar_wrapper_invokes_helper_and_returns_calendar` (asserts wire-level payload + Pydantic shape)
  - `test_rename_calendar_wrapper_blank_titles_raise`
  - `test_live_create_rename_and_delete_round_trip` (guarded by `REM_LIVE_HELPER=1`) — **PASSED live**.

### Verified
- `pytest test_eventkit_wrapper.py`: 10 passed + 2 skipped (the live tests).
- `REM_LIVE_HELPER=1 pytest test_eventkit_wrapper.py::test_live_create_rename_and_delete_round_trip test_eventkit_wrapper.py::test_live_create_and_cleanup_round_trip`: **both PASSED**.
- `await mcp.list_tools()`: 25 tools registered (was 23; `delete_calendar` + `update_calendar` are new).
- `make lint && make check-architecture`: green.

### Status
- Phase 1 progress: S1.0 ✅, S1.1 ✅, S1.2 ✅, S1.3 ✅ — four of nine slices landed. S1.4 (ReminderKit helper Python wrapper) next — that wrapper unlocks subtasks, flagged-via-API, tags, and sections.

## [0.1.22] — 2026-05-28 — Agent: Claude — Slice 1.2 (create_calendar)

The first write tool that goes through the Swift EventKit helper subprocess.
End-to-end-verified live: an `REM-TEST-AUTODELETE-S12` list was created in
the user's Reminders.app and cleaned up via the helper's `delete_list`
action, all within a pytest run.

### Added
- **`src/mcp_apple_reminders/_native/eventkit.py`** (new) — Python wrapper around `_native/bin/rem_eventkit`. Per-call subprocess mode (per S0.6 decision). Sends JSON on stdin, reads JSON on stdout. Public surface: `create_calendar()`, exceptions `EventKitHelperUnavailable` and `EventKitHelperError`, `DEFAULT_HELPER_PATH` constant. Helper-not-built and structured-error paths cleanly distinguished.
- **`tools/calendars.py::create_calendar`** (`@mcp.tool`) — the 23rd tool. Takes `name` + optional `color`; returns the new `Calendar` Pydantic model with deeplink. Order of operations:
  1. Blank-name guard → `ValueError`.
  2. **Duplicate-name guard** via SQLite `Reader.get_calendar_by_name` (sub-ms); falls back to an EventKit list scan when SQLite is unavailable.
  3. `helper_create_calendar(name, color)` invokes the Swift helper.
  4. `EventKitHelperUnavailable` → `ValueError` with the "run `make build-native`" hint.
  5. `EventKitHelperError` → `ValueError` carrying the helper's own message.
  6. Success → `ctx.info(...)` + return Pydantic Calendar.
- **`test_eventkit_wrapper.py`** (new) — 7 tests (6 unit + 1 opt-in live):
  - `test_missing_helper_raises_unavailable`
  - `test_blank_title_raises_value_error`
  - `test_success_response_returns_calendar_with_deeplink` (mocked helper)
  - `test_error_response_raises_helper_error_with_message` (mocked exit-1 helper)
  - `test_non_json_stdout_raises_helper_error`
  - `test_color_argument_is_passed_to_helper` — captures stdin and asserts the wire-level JSON shape (`action`, `title`, `color`)
  - `test_live_create_and_cleanup_round_trip` (guarded by `REM_LIVE_HELPER=1`) — creates `REM-TEST-AUTODELETE-S12` and cleans up via the helper's `delete_list`. **Confirmed passing live on this checkout.**

### Verified
- `pytest test_sqlite_reader.py test_mcp_tools.py test_e2e.py test_models.py test_eventkit_wrapper.py`: 31 passed, 2 skipped (the 2 opt-in live tests).
- `REM_LIVE_HELPER=1 pytest test_eventkit_wrapper.py::test_live_create_and_cleanup_round_trip`: PASSED — round-trip actually works.
- `await mcp.list_tools()`: 23 tools registered (was 22; `create_calendar` is new).
- `make lint && make check-architecture`: green.

### Status
- Phase 1 progress: S1.0 ✅, S1.1 ✅, S1.2 ✅ — three of nine slices landed. S1.3 (`delete_calendar` + `update_calendar`) and S1.4 (ReminderKit helper Python wrapper) next.

## [0.1.21] — 2026-05-28 — Agent: Claude — Slice 1.0 (SQLite reader)

### Added (read path)
- **`src/mcp_apple_reminders/_native/sqlite.py`** — direct read-only access to the Reminders.app CoreData store. Opens the largest `Data-*.sqlite` in `~/Library/Group Containers/group.com.apple.reminders/Container_v1/Stores/` with `file:...?mode=ro&immutable=1`. Module exports: `Reader` (the facade class with all read methods), `RemindersDBUnavailable` exception, `connect()`, `find_db_path()`, and the `APPLE_EPOCH_OFFSET` constant. Module-shape gate green: 4 public entry points (cap 8).
- **`Reader` class** methods: `schema_summary`, `list_calendars`, `get_calendar_by_id`, `get_calendar_by_name`, `search_calendars`, `iter_reminders`, `get_reminder_by_id`, `search_reminders`. All return Pydantic models with populated deeplinks.
- **`src/mcp_apple_reminders/lifespan.py`** updated: `AppContext` now carries `sqlite_db_path` resolved once at startup, and `open_sqlite()` returns a fresh read-only connection per call. Store-not-found is NOT server-fatal — logs to stderr at startup and the per-tool fallback kicks in.
- **`test_sqlite_reader.py`** (10 tests): `find_db_path` happy path + missing-dir-raises, `schema_summary` required-tables-present, `list_calendars` deeplinks + at-most-one-default, **latency assertion `< 100 ms`** (measured ~0.6 ms on this machine's 27-cal / 2200-reminder store), `iter_reminders` deeplinks + completed filter, `search_reminders` substring round-trip, `get_reminder_by_id` round-trip + missing-returns-None.

### Changed (tool handlers — SQLite-first, EventKit-fallback)
- `tools/calendars.py`: `list_calendars`, `get_calendar`, `get_calendar_by_id`, `search_calendars` route through the SQLite `Reader` first; `RemindersDBUnavailable` triggers `ctx.warning(...)` + `app.bridge.calendars.*` fallback. `get_default_calendar` stays on EventKit (source of truth for "which list is default").
- `tools/queries.py`: `get_reminders`, `search_reminders`, `get_next_reminder`, `get_overdue_reminders`, `get_today_reminders` all SQLite-first. Priority bucket filter applied client-side (SQLite stores raw int 0–9; EventKit's named-bucket semantics don't map cleanly to a WHERE clause).
- `tools/reminders.py::get_reminder`: SQLite-first; EventKit fallback if the SQLite path is unavailable OR the UUID isn't found in the cache.

### Decided
- The reader is exposed as a single `Reader` class rather than a flat collection of module-level functions to keep the public-entry-point count under the module-shape cap of 8. Connection lifetime stays with the caller (a `with` block around `connect()` in lifespan), which lets tools use the SQLite connection as a short-lived resource.

### Verified (closes S0.3 open question)
- **Deeplink UUID equivalence** — `EKReminder.calendarItemIdentifier()` matches SQLite `ZCKIDENTIFIER` for the same reminder; same for `EKCalendar.calendarIdentifier()` vs `ZREMCDBASELIST.ZCKIDENTIFIER`. Verified live against this machine's store on 2026-05-28. The `x-apple-reminderkit://REMCDReminder/{id}` and `x-apple-reminderkit://REMCDList/{id}` deeplinks generated by either path resolve to the same entity.

### Tested
- `pytest test_sqlite_reader.py test_mcp_tools.py test_e2e.py test_models.py`: 25 passed, 1 skipped.
- `make lint && make check-architecture`: green (43 files; 6 soft warnings, no hard limits exceeded; module-shape gate green).

## [0.1.20] — 2026-05-28 — Agent: Claude — Slice 0.6 (Phase 0 complete)

### Added (native build pipeline — borrowed from viticci/remctl @ baaa57b, MIT)
- **`src/mcp_apple_reminders/_native/src/rem_eventkit.swift`** — Swift / EventKit JSON-over-stdio helper. Borrowed verbatim from `viticci/remctl::remctl-bridge.swift`. Will back `create_calendar`, `delete_calendar`, `update_calendar`, alarms, recurrence in slices 1.2 / 1.3 / 3.1–3.3.
- **`src/mcp_apple_reminders/_native/src/rem_reminderkit.m`** — Obj-C / ReminderKit (private framework) JSON-over-stdio helper. Borrowed verbatim from `viticci/remctl::remctl-private.m`. Will back subtasks, set_flagged, set_tags, assign_section in slices 1.4–1.8.
- **`src/mcp_apple_reminders/_native/THIRD_PARTY_NOTICES.md`** — verbatim upstream MIT license + file-by-file mapping + upstream commit SHA + full description of the two local modifications (attribution header block, `--ping` argv shortcut). Re-sync instructions documented.
- **`Makefile::build-native`** — `swiftc` for the Swift helper, `clang -F/System/Library/PrivateFrameworks` for the Obj-C helper. Output goes to `_native/bin/{rem_eventkit,rem_reminderkit}`. Also runs `--ping` on each binary at end of build for sanity. New companion target `clean-native`.
- **`install.sh`**: invokes `make build-native` after the pip install. Degrades gracefully (warns, doesn't fail) if `swiftc` or `clang` are missing.
- **`verify_setup.py`**: probes each binary via `--ping` and asserts the `{"status":"ok","helper":"<name>"}` payload.

### Changed (policy — Pierce-approved exception)
- **`VIBE.yaml::architecture.exclude_globs`** gains `src/mcp_apple_reminders/_native/src/*.swift` and `*.m` with explicit documentation that these are vendored upstream sources (not grandfathered project code). Approved 2026-05-28 per the spec 002 borrow plan. Re-sync flow + audit trail live in `_native/THIRD_PARTY_NOTICES.md`.
- **`.gitignore`** ignores compiled `_native/bin/` artifacts.

### Decided (S0.6 design point)
- **Per-call subprocess mode** for the helper binaries. Each tool invocation spawns the helper, pipes one JSON command, reads one JSON response, exits. ≈50–200 ms per call, acceptable for user-scale interactive ops. The long-lived mode (one persistent helper subprocess, multiplexed) is a swap-in upgrade — same JSON protocol — that can land in `_native/bridge.py` at S1.4 if profiling shows it matters.

### Verified
- `make build-native`: both binaries compile clean, --ping returns ok for both.
- `verify_setup.py`: all probes green (including the two new binary probes).
- `pytest test_mcp_tools.py test_e2e.py test_models.py`: 15 passed, 1 skipped.
- `make lint && make check-architecture`: green (vendored upstream sources excluded; 41 Python files scanned).

### Status
- **Phase 0 substrate is COMPLETE.** All six slices (S0.1–S0.6) have landed:
  - S0.1 `mcp>=1.27` + PyObjC pins
  - S0.2 rename `libs/pyremindkit` → `_native`
  - S0.3 Pydantic models (CONTRACT FREEZE)
  - S0.4 FastMCP migration (all 22 tools)
  - S0.5 Context logging
  - S0.6 native build pipeline
- **Phase 1 starts next at Slice 1.0** (direct SQLite reader).

## [0.1.19] — 2026-05-28 — Agent: Claude — Slice 0.5

### Added (observability)
- `tools/reminders.py`: `await ctx.info(...)` on create/update/complete/uncomplete/delete; `await ctx.warning(...)` before delete fires; `await ctx.error(...)` on delete failure.
- `tools/queries.py`: `await ctx.debug(...)` reports match counts on `get_reminders`, `get_overdue_reminders`, `get_today_reminders`; `await ctx.warning(...)` when `search_reminders` finds nothing; `await ctx.info(...)` when `get_next_reminder` returns None.
- `tools/workflow.py`: `await ctx.info(...)` on every move; `await ctx.warning(...)` when `get_workflow_lists` finds no `Claude-*` lists; `await ctx.error(...)` before the helper raises when a sugar move target is missing.

### Unchanged
- `tools/calendars.py`: pure read tools — no state changes worth logging at handler level.
- `lifespan.py`: pre-session `PermissionError`/init-error path keeps writing to `sys.stderr` (correct: no MCP session exists yet to log through `Context`).

### Verified
- `pytest test_mcp_tools.py test_e2e.py test_models.py`: 15 passed, 1 skipped.
- `grep -rn 'print(' src/mcp_apple_reminders/tools/`: zero hits.
- `make lint && make check-architecture`: green.

## [0.1.18] — 2026-05-28 — Agent: Claude — Slice 0.4 (FastMCP migration)

### Changed (substrate)
- **Server rewritten on `FastMCP`** (`mcp>=1.27`). The pre-S0.4 low-level `Server` + `@app.list_tools()` / `@app.call_tool()` dispatch with a manual handler dict (`ALL_TOOLS`, `ALL_HANDLERS`) is gone. `server.py` is now 50 LOC; tool registration is decorator-driven and happens at import time.
- New **`src/mcp_apple_reminders/lifespan.py`** owns the single `RemindKit` bridge via an `@asynccontextmanager` returning an `AppContext` dataclass. All tools access it through `ctx.request_context.lifespan_context.bridge`. The pre-session `PermissionError` path stays on stderr (no MCP session yet to log through).
- **All 22 tools migrated to `@mcp.tool` decorators** across `tools/calendars.py`, `tools/reminders.py`, `tools/queries.py`, `tools/workflow.py`. Each handler is `async def …(arg1, …, ctx: Context) -> Pydantic`.
- Output shape moved from `list[TextContent]` (a hand-formatted human-readable block) to **structured Pydantic models**. FastMCP serializes them as structured output AND renders a text-content fallback for clients that don't surface structured output.
- `tools/__init__.py` no longer aggregates an `ALL_TOOLS` / `ALL_HANDLERS` registry — FastMCP owns the registry directly.
- `__init__.py`: `from .server import cli_main, mcp` (was `cli_main, main`).

### Added (converters)
- `models.py::native_calendar_to_pydantic(_native.Calendar)` and `native_reminder_to_pydantic(_native.Reminder)` — transitional adapters that let the FastMCP tools wrap the existing `_native` data-access surface without forcing a simultaneous rewrite of `_native` to return Pydantic. They go away in S1.0 when the SQLite reader returns Pydantic directly.

### Preserved (acceptance criterion: bit-for-bit tool surface)
- Tool **names** and descriptions: verbatim. All 22 names confirmed via `await mcp.list_tools()`.
- **Semantic** input schemas: identical parameter sets and `required` lists per tool. FastMCP normalizes optional params to `anyOf [type, null]` (vs the old `properties` + omit-from-`required` shape) — semantic equivalence; the diff is syntactic. The migration was an explicit Pierce-approved trade for Resources/Prompts/Sampling/Elicitation in Phase 2.

### Verified
- `pytest test_mcp_tools.py test_e2e.py test_models.py`: 15 passed, 1 skipped (the opt-in deeplink open round-trip).
- `make lint && make check-architecture`: green (41 files; ⚠ 5 soft warnings at 258–291 LOC; under hard cap 400).
- `./venv/bin/python -m mcp_apple_reminders` boots cleanly and blocks on stdio as expected.
- `verify_setup.py`: all probes green.

## [0.1.17] — 2026-05-28 — Agent: Claude — Slice 0.3 (CONTRACT FREEZE)

### Added
- **`src/mcp_apple_reminders/models.py`** — Pydantic v2 public schemas for every MCP response surface. Locked field orders (the contract freeze for spec 002):
  - `Calendar` (6 fields): `id, name, color, is_default, owner, deeplink`.
  - `Reminder` (18 fields): `id, title, due_date, notes, completed, url, priority, list_id, created_date, modified_date, flagged, parent_reminder_id, subtasks, tags, section_name, completion_date, start_date, deeplink`.
  - Both `frozen=True` + `extra="forbid"`. ReminderKit-only fields (parent_reminder_id, subtasks, tags, section_name) default to None / [] so EventKit-only paths construct cleanly.
- Deeplink helpers `reminder_deeplink(uuid)` and `calendar_deeplink(uuid)` (constants `REMINDER_DEEPLINK_SCHEME`, `CALENDAR_DEEPLINK_SCHEME` exported for tests).
- EventKit converters `eventkit_reminder_to_pydantic(ek_reminder)` and `eventkit_calendar_to_pydantic(ek_calendar, *, is_default, owner=None)`. Both derive the deeplink from `calendarItemIdentifier()` / `calendarIdentifier()`.
- **`test_models.py`** — 11 tests (10 pass + 1 opt-in skip):
  - Deeplink helper format
  - Calendar + Reminder construction with defaults
  - Pydantic `frozen=True` mutation guard
  - **Field-order regression tests** (`test_calendar_field_order_is_canonical`, `test_reminder_field_order_is_canonical`) — these are the locking mechanism. Drifting the field order without an ADR fails CI.
  - Priority validation (ge=0, le=9)
  - EventKit→Pydantic integration against the real default calendar + a real reminder (skips cleanly if Reminders permission absent or the calendar is empty).
  - Opt-in `subprocess.run(["open", deeplink])` round-trip guarded by `REM_DEEPLINK_SMOKE=1`.

### Verified
- `pytest test_models.py`: 10 passed, 1 skipped.
- `make lint && make check-architecture`: green (`models.py` 203 lines / `test_models.py` 258 lines — both under hard cap 400; `test_models.py` triggers a soft warning at 258).
- Real-EventKit converter exercises `calendarItemIdentifier()` end-to-end; the asserted `pydantic_r.deeplink` matches `x-apple-reminderkit://REMCDReminder/{id}` exactly.

### Decided
- Converters live in `models.py` (gated via `TYPE_CHECKING` for EventKit types) rather than in `_native/_internal.py`. Keeps the EventKit dependency out of the public model module's import graph; lets the models be imported from docs-gen, tests, or any non-macOS host without dragging PyObjC.
- The SQLite half of the deeplink-UUID equivalence (`EKReminder.calendarItemIdentifier() == SQLite ZIDENTIFIER`) is verified at S1.0 when the direct reader lands. EventKit half locked here.

## [0.1.16] — 2026-05-28 — Agent: Claude — Slice 0.2

### Changed
- **Renamed `libs/pyremindkit/` → `src/mcp_apple_reminders/_native/`.** Drops the vendored-dep narrative; the EventKit wrapper is now first-party. Five module files moved via `git mv` (history preserved): `__init__.py`, `_internal.py`, `calendars.py`, `core.py`, `models.py`. Internal module names unchanged (transitional aliases until S0.3+0.4 reshape further).
- `src/mcp_apple_reminders/server.py`: dropped `sys.path` mutation; imports `RemindKit` via `from ._native import RemindKit`. File shortened 95 → 89 lines.
- `src/mcp_apple_reminders/formatting.py` + `src/mcp_apple_reminders/tools/queries.py`: re-imported `from mcp_apple_reminders._native`.
- All test orchestrators (`test_comprehensive_crud.py`, `test_workflow_tools.py`, `test_e2e.py`, `test_mcp_tools.py`): dropped `sys.path` insert; switched to `from mcp_apple_reminders._native import ...`.
- `verify_setup.py`: replaced the pyremindkit-on-sys.path probe with a direct `from mcp_apple_reminders import _native` probe.
- `Makefile`: lint/black targets no longer reference `libs/pyremindkit/src/`.

### Removed
- `libs/` directory entirely: `LICENSE`, `MANIFEST.in`, `Makefile`, `README.md`, `README.upstream.md`, `VENDOR.md`, `examples/`, `requirements/`, `setup.py`, `pyproject.toml`, `.gitignore`, `.pre-commit-config.yaml`.

### Documented
- `AGENTS.md` + `MAP.md` swept: references to `libs/pyremindkit/`/`pyremindkit/` replaced with `_native/` throughout (paths, gotchas, decision-log entries).

### Verified
- `make lint && make check-architecture` green (38 source files; ⚠ 3 soft warnings unchanged from pre-slice).
- `pytest test_mcp_tools.py test_e2e.py`: 5 passed.
- `verify_setup.py`: all probes green against the renamed package.

## [0.1.15] — 2026-05-28 — Agent: Claude — Slice 0.1

### Changed
- `pyproject.toml` + `requirements.txt`: pinned `mcp>=1.27,<2` (was `>=0.1.0`), pinned `pyobjc-core>=12.0,<13`, `pyobjc-framework-EventKit>=12.0,<13`, `pyobjc-framework-Foundation>=12.0,<13`. Added explicit `pydantic>=2.10,<3` dep (was transitively pulled by mcp).
- Installed: mcp 1.24.0 → 1.27.1; pydantic 2.12.5 → 2.13.4.

### Added
- `verify_setup.py`: three new probes — Pydantic v2 importability, MCP SDK version `>=1.27` (via `importlib.metadata.version`), PyObjC deprecation-warning-free import of `objc + EventKit` on macOS 26.1.

### Verified
- `verify_setup.py` exits 0 across all checks against the upgraded venv.
- `./venv/bin/python -m mcp_apple_reminders` starts cleanly (blocks on stdio as expected for an MCP server).
- `make lint && make check-architecture` green.
- Pre-existing pytest fixture-resolution errors in `test_workflow_*.py` confirmed unrelated to S0.1 (reproduce on bare `main` via `git stash`). Spawned side task to restore fixtures.

## [0.1.14] — 2026-05-28 — Agent: Claude
### Changed
- `TASK_STATE.md` §6 Handoff rewritten with detailed compaction-survival summary: every commit landed this session (10+), standing rules to not re-litigate, three live open questions tied to specific slices, and reading order for a fresh agent.

### Documented (Serena memories)
- `mem:session_pivot_2026_05_28` (NEW) — full narrative of the research pass and the three-jump pivot (modernize-first → ReminderKit-via-PyObjC → RemCTL three-tier). Read this if the spec's "why" isn't clear from the spec/design files alone.
- `mem:core` (UPDATED) — source map now distinguishes current state (libs/pyremindkit/) from post-S0.2 target (_native/). Roadmap reflects spec 002's 25-slice four-phase plan. `is_default` bug marked FIXED.

## [0.1.13] — 2026-05-28 — Agent: Claude
### Changed
- **Spec 002 pivoted to RemCTL's actual three-tier architecture**: direct SQLite reads + Swift EventKit helper subprocess + Objective-C ReminderKit helper subprocess. Replaces the earlier "PyObjC for everything" approach after surfacing RemCTL's real implementation (Python 83.4% / Obj-C 9.6% / Swift 5.8% / Shell 1.2%, three compiled helpers + direct SQLite reads).
- Added **Slice 0.6** (native build pipeline) and **Slice 1.0** (SQLite reader) to plan + tasks. Phase 0 grows from 5 to 6 slices; Phase 1 grows from 7 to 9 slices (adding S1.0 SQLite reader and S1.8 `assign_section`).
- `Reminder` Pydantic model gains `deeplink: str` field (`x-apple-reminderkit://REMCDReminder/{id}`); `Calendar` model gains the same (`x-apple-reminderkit://REMCDList/{id}`). Surfaces on every response.
- `Reminder` model also gains `section_name: str | None` (from SQLite read).
- Total scope: 25 slices, ~13-14 days focused capacity. SQLite-reader win means many Phase 3 reads come for free.

### Documented
- Borrow plan: `viticci/remctl::remctl-bridge.swift` → `_native/src/rem_eventkit.swift`; `viticci/remctl::remctl-private.m` → `_native/src/rem_reminderkit.m`. MIT-licensed. Attribution in `_native/THIRD_PARTY_NOTICES.md` + inline file headers (created in S0.6).
- Verified RemCTL is open source (github.com/viticci/remctl), MIT-licensed, actively maintained (last push 2026-05-26), 40 stars.

## [0.1.12] — 2026-05-28 — Agent: Claude
### Added
- `specs/002-modernize-and-foundation/{spec,design,plan,tasks}.md` — new 4-phase spec replacing the archived `001-visibility-foundation` after gold-standard research surfaced significant scope expansion (FastMCP, MCP 1.27+, ReminderKit private API for subtasks/flagged/tags, MCP Resources/Prompts/Sampling/Elicitation, alarms, recurrence, bulk ops, visibility-plane pilot).
- `mem:global/agent_model_policy` (Serena global memory) — Pierce-explicit: ALL subagents run on Opus, always.

### Changed
- `specs/001-visibility-foundation/` → `specs/_archive/001-visibility-foundation/` (preserves the original planning artifacts; `README.md` explains the retirement reason).
- `TASK_STATE.md`, `PROGRESS.md` — updated to point at spec 002. Phase 0 / Slice 0.1 is next. Slice 1.1 (is_default) preserved as already-done in commit 117cc8a.

### Research findings
- Public EventKit (macOS 26.1) does NOT expose subtasks / tags / sections. Those live in `/System/Library/PrivateFrameworks/ReminderKit.framework`.
- MCP Python SDK current PyPI version: 1.27.1. Current pin (`mcp>=0.1.0`) is ancient.
- Competitor `FradSer/mcp-server-apple-events` (122★, 533 commits, TypeScript+Swift) covers subtasks + alarms + recurrence + tags + 4 prompts. The bar.

## [0.1.11] — 2026-05-28 — Agent: Claude
### Changed
- Archived spec 001-visibility-foundation and landed spec 002-modernize-and-foundation — the pivot to the RemCTL three-tier native architecture (direct SQLite reads + Swift EventKit helper subprocess + Obj-C ReminderKit helper subprocess) plus FastMCP / MCP 1.27 modernization (Resources, Prompts, Sampling, Elicitation, deeplinks on every Reminder + Calendar).

## [0.1.10] — 2026-05-28 — Agent: Claude
### Fixed
- CHANGELOG [0.1.9] entry was left as a placeholder by the implementer subagent; filled in with the actual S1.1 change description.

## [0.1.9] — 2026-05-28 — Agent: Claude
### Changed
- Corrected `is_default` detection in `CalendarManager.list()` (slice S1.1): the default calendar is now identified by comparing each calendar against `EKEventStore.defaultCalendarForNewReminders()` instead of the prior logic that never flagged one (the change the [0.1.10] note claimed it had already filled).

## [0.1.8] — 2026-05-28 — Agent: Claude
### Changed
- Adopted trunk-strategy: `VIBE.yaml::project.branch_strategy: trunk`. Pierce-explicit (2026-05-28) — sole-author repo, no PR review dance. All work commits directly to `main`.
- `TASK_STATE.md` and `PROGRESS.md` updated to reflect the trunk-strategy and the now-deleted `chore/seed-agents-md` feature branch (retrofit + first spec landed; branch was merged fast-forward into main and deleted both locally and on origin).

## [0.1.7] — 2026-05-28 — Agent: Claude
### Added
- `make lint` now runs `ruff check` + `black --check` against `src/`, `libs/pyremindkit/src/`, `test_*.py`, and `test_support/`. Stub eliminated.
- `make typecheck` now runs `mypy` on `src/mcp_apple_reminders/` with `--ignore-missing-imports` (PyObjC has no type stubs). Stub eliminated.
- `mypy>=1.13` added to `pyproject.toml::dev` dependencies; `ruff` pin bumped to `>=0.8`.

### Changed
- Removed `TCH` (typing-imports) from `[tool.ruff.lint].select` — its TYPE_CHECKING-block recommendations add ceremony without value here. Other rule families (`E`, `F`, `I`, `N`, `W`, `B`, `C4`, `PT`, `SIM`) remain active.
- Auto-formatted 9 files with `black` to bring them into compliance.

### Fixed
- 27 ruff violations across the refactored modules, broken into three classes:
  - **File-level `# ruff: noqa: E402`** on `test_comprehensive_crud.py` and `test_workflow_tools.py` (orchestrators must mutate `sys.path` before importing the per-domain test modules; the noqa is localized to that legitimate pattern).
  - **Per-line `# noqa: F401`** on the import-availability probes in `test_mcp_tools.py::test_imports()` (the imports ARE the test).
  - **Real fixes** elsewhere: `B904` (`raise ... from err`) in `formatting.py::parse_datetime`; `SIM108` (ternary refactor) in `core.py::RemindKit.create_reminder`; `E712` (`is True/False`) and `E722` (`except Exception`) in pre-existing `test_e2e.py`.

### Notes
- Resolves the Stop-hook lint-gate failure that was blocking session completion.
- `quality_gates.lint.required: true` and `quality_gates.typecheck.required: true` both now pass.

## [0.1.6] — 2026-05-28 — Agent: Claude
### Added
- `.claude/agents/` — 7 subagents (planner, implementer, test-runner, reviewer, debugger, terraform-reviewer, research-agent).
- `.claude/commands/` — 10 slash commands (/plan, /implement-slice, /ship, /review, /debug, /scaffold, /retrofit, /adr, /sync-skills, /terraform-plan).
- `.claude/rules/` — 5 path-scoped rules (serena, python, security, terraform, ansible).
- `.claude/hooks/` — 9 executable hooks (bash-guard, session-start, serena-required, serena-gate, inject-state, auto-lint, auto-commit, stop-gate, changelog-append).
- `.claude/settings.json` — hook wire-up + tool deny-list.
- `.pre-commit-config.yaml` — independent enforcement layer mirroring `make validate`.
- This `CHANGELOG.md` file (auto-created by `scripts/bump_version.py`).

### Changed
- `.gitignore` — added `.claude/session-context.md` to ignored set.
- `.claude/settings.local.json` — un-tracked (now gitignore-only); previously committed by accident.

### Notes
- Final commit of the 5-PR brownfield retrofit. Branch ready to merge to main.
- Operator follow-up after first clone: `pre-commit install`; ensure `jq` is on PATH.
