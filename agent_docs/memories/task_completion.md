# Task Completion

Before declaring a task complete:

1. `ruff check src/ libs/pyremindkit/src/` — must pass.
2. `black --check src/ libs/pyremindkit/src/` — must pass.
3. `make check-architecture` — must pass (line limits + module shape).
4. If code changed: smoke-test affected MCP tools manually (e.g. `list_calendars`, `create_reminder`, then `delete_reminder` to clean up).
5. If permission-sensitive code changed (`_grant_permission`, EventKit access): re-run `verify_setup.py`.
6. `make bump-patch` (or appropriate bump level) — `bump_required_per_commit: true`.
7. `git commit -S` — signed commit required.
8. `git push` — leave the work landed remotely; un-pushed signed commits don't count as "done" per `AGENTS.md::Git Workflow Requirements`.

## Tests

- Test runner: `./venv/bin/python -m pytest <explicit test files>`. Root is NOT on `testpaths`; auto-discovery from `tests/` won't find anything.
- Tests are `mode: deferred` in `VIBE.yaml` — running is optional but recommended for changes touching `core.py` or `server.py`. Flip to `required` after the test suite is stabilized.

## Final completion gate (when run)

- `make check-if-the-agent-can-consider-this-task-completed` — runs lint + typecheck + architecture + version-bumped + check-docs + check-precommit + test.
- Lint and typecheck stubs CURRENTLY FAIL (no lang-mcp overlay yet); they print red "fail closed" messages. Until lang-mcp is overlaid (or stubs are filled in), run `ruff` and `black` directly to satisfy the spirit of those gates.

## Docs gate

- `make check-docs` enforces `docs.*_required` from VIBE.yaml. Currently AGENTS.md, CLAUDE.md (symlink), VIBE.yaml required. After PR4: also TASK_STATE.md.
- If you touch behavior, update AGENTS.md §9 (gotchas) AND the relevant Serena memory in the same task — both staying current is part of "done."
