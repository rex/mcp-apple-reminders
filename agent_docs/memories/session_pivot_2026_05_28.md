# Session pivot — 2026-05-28

> One-session capture of the research + architectural pivot that produced
> spec 002 in its current (RemCTL three-tier) form. Read this if the
> spec's "why" isn't clear from the spec/design files alone.

## What changed direction

The session started with `001-visibility-foundation` (PyObjC-for-everything
plan, 4 slices, scoped to `is_default` + `create_calendar` + subtasks).
It ended with `002-modernize-and-foundation` (RemCTL three-tier, 25
slices, four phases). The pivot happened in three jumps:

1. **Gold-standard MCP research** revealed the current Python SDK (1.27.1)
   has FastMCP, Resources, Prompts, Sampling, Elicitation, lifespan, and
   structured outputs — we were using none of them. Scope grew to "modernize
   first." Pierce confirmed all four phases (modernize → P0 → MCP primitives
   → feature parity + visibility-plane).
2. **EventKit reality check** revealed public EventKit doesn't expose
   subtasks/tags/sections on macOS 26 — they live in private `ReminderKit.framework`.
   Verified on disk at `/System/Library/PrivateFrameworks/ReminderKit.framework`
   (Reminders.app links it via `otool -L`). I initially proposed PyObjC binding.
3. **RemCTL architecture deep-dive** revealed the proven pattern is THREE tiers,
   not one. Direct SQLite reads (Python in-process), Swift subprocess for public
   EventKit writes, Obj-C subprocess for private ReminderKit writes. SQLite
   reads expose sections/subtasks/tags/attachments/alarms metadata FOR FREE
   without framework calls. Pierce confirmed pivot to three-tier with borrowed
   RemCTL code (MIT, attribution).

## Why the pivot is worth the cost

- **Reads**: tens of milliseconds for full corpus via SQLite vs hundreds of
  milliseconds (or worse) via EventKit predicate iteration. `search_reminders`
  becomes one indexed SQL query.
- **Capability coverage**: SQLite reader gives us sections, subtasks, tags,
  attachments, alarms metadata, recurrence metadata FREE. Phase 3 "feature
  parity" work shrinks because reads come automatically; only writes need
  fresh work.
- **Battle-tested writes**: RemCTL's `remctl-private.m` already binds
  `REMReminder` operations correctly across macOS 26.x. We borrow with MIT
  attribution, no need to re-derive private-framework signatures.
- **Subprocess isolation**: a private-API breakage crashes a ~50 LOC helper,
  not the whole MCP server.
- **Cost paid**: native build pipeline (Slice 0.6 — ~1 day) plus marshalling
  JSON over stdin/stdout to two compiled helpers. Pierce has Xcode CLI tools.

## Three-tier architecture (locked)

| Tier | Tech | Path | Purpose |
|---|---|---|---|
| 1. Reads | Python → SQLite | `_native/sqlite.py` reading `~/Library/Group Containers/group.com.apple.reminders/Container_v1/Stores/Data-*.sqlite` | Calendars, reminders, sections, subtasks, tags, attachments, alarms metadata, recurrence metadata |
| 2. Public writes | Swift subprocess | `_native/bin/rem_eventkit` (compiled from `_native/src/rem_eventkit.swift`, borrowed from RemCTL) | Create/update/delete reminders, calendar lifecycle, alarms, recurrence |
| 3. Private writes | Obj-C subprocess | `_native/bin/rem_reminderkit` (compiled from `_native/src/rem_reminderkit.m`, borrowed from RemCTL) | Subtasks, tags, sections, flagged, attachments, Early Reminders |

`_native/bridge.py` is the unified facade; tools never see the tier split.
Lifespan owns the Bridge instance.

## Reference implementations

- **RemCTL** (`viticci/remctl`, MIT, 40★, last push 2026-05-26): the proven
  three-tier reference. We borrow `remctl-bridge.swift` and `remctl-private.m`
  with attribution in `_native/THIRD_PARTY_NOTICES.md`. RemCTL is 83.4% Python,
  9.6% Obj-C, 5.8% Swift, 1.2% Shell.
- **FradSer/mcp-server-apple-events** (122★, 16 releases, 533 commits): the
  feature-parity bar. TypeScript+Swift MCP wrapping EventKit; ships subtasks,
  alarms, recurrence, tags, 4 prompts.
- **BRO3886/rem** (Swift CLI): another prior art demonstrating ReminderKit
  flagged/hashtags binding.
- **xybp888/iOS-Header/.../ReminderKit.framework/**: scraped headers for the
  private framework's class layout.

## Standing decisions (locked, do not re-litigate)

- Spec 002 is canonical; spec 001 archived at `specs/_archive/001-visibility-foundation/`.
- All four phases approved (modernize / P0 / MCP primitives / feature parity + pilot).
- Subtask backend: ReminderKit helper subprocess (not PyObjC, not AppleScript).
- Modernize-first ordering (Phase 0 before Phase 1 new work).
- ALL subagents on Opus — global policy at `mem:global/agent_model_policy`.
- Trunk strategy (no feature branches).
- No grandfathering in architecture gate.
- Pydantic field order frozen after S0.3.
- MCP tool name + inputSchema preservation across the FastMCP migration (S0.4).
- Borrowed code carries inline attribution headers + `_native/THIRD_PARTY_NOTICES.md`.

## Discovered gotchas worth burning in

- `bash-guard.sh` blocks tool calls whose body matches its deny patterns,
  including commit messages that quote them. Write commit messages with
  HEREDOC to a file, then `git commit -F /tmp/msg.txt`. The hook itself is
  fine — the issue is the Bash-tool inspection of the command-line.
- `detect-secrets` false-positives on the literal word "secrets" in YAML;
  inline `# pragma: allowlist secret` comment is the fix.
- `make bump-patch` is mandatory before every commit. Each commit needs a
  unique VERSION + matching CHANGELOG entry.
- Pre-commit auto-fix hooks (trailing whitespace, end-of-file-fixer) WILL
  modify staged files mid-commit; you must `git add` again and retry.
- `_native/` doesn't exist yet — created in S0.2. Until then, vendored code
  is at `libs/pyremindkit/src/pyremindkit/`.
- macOS 26.1 verified as the dev box. ReminderKit, ReminderKitInternal,
  ReminderKitUI all present at `/System/Library/PrivateFrameworks/`.
- pyremindkit upstream is dead (9 commits, 27 stars, no movement since
  Dec 2025). The vendored fork is the project now; treat it as ours.

## What was already shipped this session

- Slice 1.1 (`is_default` fix) — commit `117cc8a`. Acceptance bullets all
  passed. Test 6 in `test_crud_calendars.py` enforces "exactly one
  Default: Yes." Do NOT redo this slice.

## What's next

Slice 0.1: bump `mcp>=1.27,<2` in `pyproject.toml`, pin PyObjC, confirm via
`verify_setup.py`. Smallest possible Phase 0 kickoff.

Then S0.2 (rename `libs/pyremindkit` → `_native`), S0.3 (Pydantic models
with deeplinks — CONTRACT FREEZE), S0.4 (FastMCP migration — biggest slice),
S0.5 (Context logging), S0.6 (native build pipeline — borrows RemCTL code),
S1.0 (SQLite reader), then standard slice cadence through Phase 1.

See `specs/002-modernize-and-foundation/tasks.md` for full acceptance bullets.
