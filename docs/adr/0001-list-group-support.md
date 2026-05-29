# ADR 0001 — Extend spec 002 with list-group support

- **Status**: Accepted
- **Date**: 2026-05-28
- **Decider**: Pierce (explicit approval after live schema reverse-engineering)
- **Spec impact**: amends `specs/002-modernize-and-foundation/` with **Phase 5 (Slice 5.1)**.

## Context

Spec 002 was authored before we'd reverse-engineered the Reminders.app
"Group" object — the collapsible folder in the sidebar that contains
multiple lists. As of the spec 002 ship (2026-05-28), the entire 31-slice
plan made no mention of groups: every tool and resource operated on
flat lists.

Pierce asked whether the server exposed a tool for creating groups. After
investigation, the surface didn't exist anywhere in the borrowed code
or the spec. **Pierce's lookup hunch** — point at his single existing
"Claude" group and reverse-engineer outward — collapsed the unknown
into a few minutes of SQL:

- Groups are **not** a distinct CoreData entity. They live in the same
  `ZREMCDBASELIST` table as regular lists.
- The discriminator is **one boolean column**: `ZISGROUP = 1`. Regular
  lists leave it null/0.
- Membership is one foreign-key column: child lists set `ZPARENTLIST =
  <group's Z_PK>`. The hierarchy is one level deep; groups don't nest.
- Groups are scoped to an account via `ZACCOUNT` + `ZPARENTACCOUNT`.

The reverse-engineering work that was originally assumed to be
"spec-and-a-half" of investigation is essentially done. What remains is
production code.

## Decision

Add **Phase 5** to spec 002 with **one slice**: `S5.1 — List-group
support (read + write)`. Phase 5 sits after Phase 4 because:

1. The visibility-plane work (Phase 4) is the original spec's payoff and
   should ship before this addendum.
2. Group support is a meaningful capability extension, not a finish
   line — promoting it to its own phase makes the lineage clear in
   `TASK_STATE.md`.
3. Spec 003 would be premature: the new work shares architecture,
   helpers, and tests with everything spec 002 already shipped.

## Consequences

### Positive

- Pierce can mirror his `Claude` group structure (and any future agent
  organization) directly through the MCP surface, instead of via
  Reminders.app UI.
- `list_calendars` becomes more useful by default — group rows can be
  filtered out instead of cluttering the list-by-name workflow.
- The borrowed Obj-C helper gains one more action; the same patch
  pattern that landed `set_flagged` / `add_tags` / `assign_section`
  applies.

### Risks

- **Private-framework drift.** ReminderKit's `REMListChangeItem` (or
  whichever class actually carries the `setIsGroup:` / `setParentList:`
  setters) may change name across macOS releases. Mitigation: same
  fallback the rest of the helper relies on — feature degrades to
  "groups are read-only" if the private API moves.
- **Two `ZPARENTLIST` columns.** The schema has `ZPARENTLIST` and
  `ZPARENTLIST1`. The investigation showed Apple uses the former for
  the active link and the latter appears to be a CoreData inverse-relation
  artifact. We write to `ZPARENTLIST` only; if a future macOS swaps
  semantics, the read path will mis-identify membership. Mitigation:
  the read path queries both, preferring the populated one.
- **Backward compat on `list_calendars`.** Adding `include_groups=False`
  default trims output for existing callers — strictly speaking a tool
  surface change. Mitigation: the parameter is opt-in additive; calling
  without it returns *fewer* results than before (specifically: existing
  group rows would have leaked through as if they were regular lists).
  This is a bug fix in the same shape as S1.1's `is_default`.

### Neutral

- The `Calendar` Pydantic gains two optional fields: `is_group: bool` and
  `parent_group_id: Optional[str]`. **Per S0.3 contract freeze, additions
  go at the tail with defaults** — this is allowed by the existing
  freeze rule. No reorder; no ADR-on-the-ADR required.

## Alternatives considered

1. **Start spec 003.** Rejected — would splinter shared design and
   force a re-statement of the architecture/borrow notices.
2. **Add the slice silently to Phase 1.** Rejected — Phase 1 is closed,
   and "no re-planning without an ADR" is explicit standing rule. This
   ADR is the bookmark.
3. **Defer to a future iteration where upstream RemCTL adds groups.**
   Rejected — schema reverse-engineering already done; cost to ship is
   small; Pierce's use case (mirroring `Agents-<project>` lists under a
   single `Agents` group) is the visibility-plane finish line.

## Implementation surface (sketch — implemented at S5.1)

- `_native/sqlite.py::Reader.list_groups()` — `WHERE ZISGROUP = 1`.
- `_native/sqlite.py::Reader.iter_lists_in_group(group_uuid)` — `WHERE
  ZPARENTLIST = (group's Z_PK)`.
- `_native/sqlite.py::Reader.list_calendars(include_groups=False)` —
  filter the existing call.
- `_native/reminderkit.py::create_group(name)` — new helper action.
- `_native/reminderkit.py::move_list_to_group(list_id, group_id|None)`
  — `None` detaches the list back to the account root.
- `tools/groups.py::create_group`, `tools/groups.py::list_groups`,
  `tools/groups.py::move_list_to_group` — three new MCP tools (38th–40th).
- `models.py::Calendar` gains `is_group: bool = False`,
  `parent_group_id: Optional[str] = None` at the tail (post-freeze
  addition, allowed by S0.3 contract).
- One new Obj-C helper action: `create_group` (and possibly
  `move_list_to_group`). Both are small extensions to the borrowed
  `_native/src/rem_reminderkit.m` — documented as a new local
  modification in `_native/THIRD_PARTY_NOTICES.md`.
- Live round-trip test: create a `REM-TEST-GROUP-S51` group, add a
  list to it, assert SQLite reports `ZPARENTLIST` pointing at the
  group, clean up.
