# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.0] - 2026-05-05

First public release.

### Added
- MCP **Resources** (`apple-reminders://list/{id}`, `apple-reminders://reminder/{id}`)
  so agents can browse without spending tool turns.
- MCP **Prompts** for ADHD workflows: `plan_my_day`, `triage_inbox`,
  `weekly_review`, `quick_capture`, `snooze`, `defer_to_someday`.
- Server `instructions` field — Claude reads this on initialize and learns the
  `Claude-On-Deck` / `Claude-Active` / `Claude-Done` / `Claude-Blocked`
  workflow conventions automatically.
- New tools: `batch_create_reminders`, `batch_update_reminders`,
  `batch_delete_reminders`, `create_subtask`, `list_subtasks`, `set_flagged`.
- `MCP_APPLE_REMINDERS_LIST_PREFIX` environment variable to customize the
  workflow list naming convention (defaults to `Claude-`).
- Structured logging via Python `logging` + the MCP `logging` capability.
- Unit-test layer with mocked `pyremindkit`; integration tests gated behind
  `MCP_APPLE_REMINDERS_LIVE_TESTS=1`.
- Continuous integration on `ubuntu-latest` and `macos-latest` for Python
  3.10/3.11/3.12/3.13.
- `py.typed` marker — downstream type checkers now see this package as typed.
- `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `SECURITY.md`, `CHANGELOG.md`.
- GitHub issue templates, PR template, Dependabot.
- Pre-commit hooks (ruff, black, end-of-file-fixer).

### Changed
- **Server architecture**: rewrote on top of `mcp.server.fastmcp.FastMCP` with
  Pydantic input/output models. Hand-written JSON Schema (~370 lines) replaced
  by type-driven generation.
- README now leads with the conversational ADHD task management framing,
  includes a client compatibility matrix, badges, and a quickstart above the
  fold.
- Default install path is now `uvx mcp-apple-reminders`; the local-checkout flow
  is documented as a development convenience.
- Workflow list lookups extracted to a single helper; calendar resolution is
  cached per request.
- `claude_desktop_config.example.json` now uses `uvx` instead of bare `python3`.

### Fixed
- RFC 3339 datetimes with a trailing `Z` (e.g. `2024-01-15T14:30:00Z`) are now
  parsed correctly. Previously the server crashed on the most common LLM-emitted
  format.
- `update_reminder` no longer silently drops falsy values like `notes=""` or
  `priority=0` — these now correctly clear the field.
- Priority parsing is unified across `create_reminder`, `update_reminder`, and
  `get_reminders` (single `_parse_priority` helper).
- Race condition between workflow-calendar lookup and `move_reminder` now fails
  with a useful error if the target list disappears.
- `get_overdue_reminders` now passes `limit` to the underlying query rather
  than fetching everything and slicing client-side.
- `get_today_reminders` end-of-day boundary is now exclusive (next-day midnight
  minus one microsecond) instead of `999999`-microsecond padding.
- Generic `except Exception` swallow at the top of the dispatcher is gone;
  user errors and server errors are now distinguished and reported via MCP
  error types.

### Removed
- `requirements.txt` — superseded by `pyproject.toml`.
- Hard-coded `/Users/pierce/...` paths from `QUICKSTART.md`.
- `sys.path` shim that pointed at a gitignored `libs/pyremindkit/` —
  `pyremindkit` is now declared as a proper PyPI dependency.
- Dev-journal markdown files moved out of repo root (now under `.archive/`,
  gitignored).

### Security
- macOS TCC permission flow now returns a structured initialize error instead
  of a hard `sys.exit(1)`, allowing the client to surface a useful message.

## [0.1.0]

Internal pre-release. Not published.

[Unreleased]: https://github.com/rex/mcp-apple-reminders/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/rex/mcp-apple-reminders/releases/tag/v0.2.0
