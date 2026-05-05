# AGENTS.md

## Purpose

This repository contains a macOS-only Model Context Protocol (MCP) server for Apple Reminders.
It exposes Apple Reminders operations to MCP clients such as Codex and Claude Desktop through
Python, EventKit, and the vendored `pyremindkit` library.

Agents working in this repository must treat it as:

- A production MCP integration repository, not a throwaway experiment.
- A macOS/EventKit bridge where runtime behavior depends on OS permissions and stdio correctness.
- A repository whose documentation is part of the deliverable, not an afterthought.

## Repository Layout

- `src/mcp_apple_reminders/`
  - Main Python package.
  - `server.py` — FastMCP server, tool handlers, lazy pyremindkit connection.
  - `_helpers.py` — pure parsing utilities (datetime, priority).
  - `_models.py` — Pydantic input/output models.
  - `_workflow.py` — kanban list resolution, prefix config.
  - `resources.py` — `apple-reminders://` URI handlers.
  - `prompts.py` — ADHD workflow prompts.
  - `__main__.py` / `__init__.py` — entrypoints.
- `tests/unit/`
  - Hermetic, mock pyremindkit. Runs on Linux + macOS.
- `tests/integration/`
  - Live macOS Reminders, gated by `MCP_APPLE_REMINDERS_LIVE_TESTS=1`.
- `docs/tools.md`
  - User-facing tool reference.
- `verify_setup.py`, `install.sh`, `shim_mcp.sh`
  - Operational scripts for installation, verification, permissions bootstrap, and local launch.
- `pyremindkit` is a real PyPI dependency (declared in `pyproject.toml`),
  not a vendored library. Do not reintroduce a `libs/` shim.

## Platform And Runtime Assumptions

- This project targets macOS only.
- Apple Reminders access depends on EventKit permissions.
- The system `python3` on macOS may be too old. Do not assume `python3` is acceptable.
- Prefer the repo runtime at `./venv/bin/python3`.
- Use dynamic path resolution derived from the repository structure. Do not hardcode personal absolute paths.

## Primary Goals For Agents

- Keep the MCP server stable for Codex and Claude Desktop.
- Preserve clean stdio MCP behavior.
- Improve correctness, safety, testability, and documentation together.
- Leave the repository in a state that another engineer or agent can understand without reverse engineering.

## MCP Safety Rules

- Never write diagnostic logs, debug prints, or status messages to stdout from the MCP server.
- If runtime logging is necessary for MCP execution, write to stderr only.
- Preserve stdin/stdout transport semantics. Do not add wrappers that emit non-JSON protocol output on stdout.
- Be careful with first-run permission flows. If modifying bootstrap behavior, keep `shim_mcp.sh` safe for permission prompting.
- Maintain compatibility with Codex configuration via `~/.codex/config.toml` and with Claude Desktop configuration via `claude_desktop_config.json`.

## Coding Standards

- Use Python 3.10+ compatible code unless the repo is explicitly migrated to a newer minimum version.
- Follow the style implied by `pyproject.toml`:
  - `black` line length: 120
  - `ruff` line length: 120
  - type-hinted Python where practical
- Prefer explicit, readable code over clever compression.
- Avoid introducing hidden control flow or magical helpers unless they materially improve maintainability.
- Keep business logic and MCP tool definitions consistent. If one changes, verify the other.
- Preserve or improve error messages. Errors should help the operator fix the problem.
- Avoid breaking public tool names, input schemas, or documented behavior without updating documentation and validation coverage.

## Path And Environment Standards

- Do not hardcode developer-specific paths such as `/Users/<name>/...`.
- Derive repo-local paths with `Path(__file__).resolve()` and related logic.
- When invoking local scripts or the package, prefer:
  - `./venv/bin/python3 -m mcp_apple_reminders`
  - `./venv/bin/python -m pip ...`
- If you update install or verification flows, ensure they still work when the repo is moved to a different absolute path.

## Documentation Requirements

Documentation is mandatory. Future agents must treat documentation updates as part of the code change, not optional follow-up.

### File-Level Documentation

- Every source file must start with a meaningful module/file docstring describing:
  - purpose
  - major responsibilities
  - important external dependencies
  - side effects or operational constraints if relevant
- Shell scripts must include a clear header comment describing:
  - why the script exists
  - expected inputs
  - important safety assumptions

### Function And Method Documentation

- Every non-trivial function and method must have a docstring.
- Docstrings must document, where applicable:
  - purpose
  - parameters
  - return value
  - raised exceptions
  - side effects
  - important invariants or edge cases
- If a function is intentionally simple enough to omit a longer docstring, it still needs at least a short descriptive docstring.

### Class Documentation

- Every class must have a docstring explaining its role, lifecycle, and key collaborators.
- Public methods on public classes must be documented.

### Variable Documentation

- All module-level constants, configuration values, and non-obvious variables must be documented with nearby comments.
- Complex local variables must be named clearly and documented when intent is not immediately obvious.
- Publicly meaningful fields, state containers, and schema fragments should be explained in code comments or surrounding docstrings.
- If a variable exists only because of a platform or framework quirk, document that quirk.

### User-Facing Documentation

- Any change to behavior, setup, configuration, testing workflow, or supported tools must be reflected in the appropriate docs.
- Keep `README.md` and `QUICKSTART.md` aligned with the real setup.
- If a change affects Codex, Claude Desktop, installation, verification, or permissions, update the relevant operational docs in the same task.

## Testing And Validation Standards

- Validate the smallest relevant surface first, then broader flows.
- Prefer the repo interpreter and explicit commands.
- Tests live in `tests/unit/` (hermetic) and `tests/integration/` (live macOS).
- `pytest tests/unit/` runs everywhere and should always pass.
- `MCP_APPLE_REMINDERS_LIVE_TESTS=1 pytest tests/integration/` requires
  macOS and a granted Reminders permission; integration tests are skipped
  by default.
- For install/runtime verification, use:
  - `python3 verify_setup.py`
  - `./venv/bin/python3 -m mcp_apple_reminders`
- If a change affects packaging or entrypoints, verify both module execution and installed script behavior when practical.
- If a change affects MCP behavior, prefer at least one real MCP smoke check.
- If you cannot run a meaningful validation step, state exactly what was not run and why.

## Documentation And Testing Coupling

- No code change is complete until:
  - the relevant docs are updated
  - the relevant validation has been run or explicitly explained
- If behavior changed but docs did not, the task is incomplete.
- If docs changed but the real workflow was not sanity-checked, the task is incomplete.

## Integration Standards

### Codex

- Keep Codex instructions accurate for `~/.codex/config.toml`.
- Prefer the repo venv interpreter in examples.
- If the Reminders permission bootstrap matters, keep `shim_mcp.sh` documented and working.

### Claude Desktop

- Keep Claude Desktop configuration examples accurate.
- Do not assume Claude Desktop and Codex use identical config formats.

### pyremindkit

- `pyremindkit` is a PyPI dependency, not vendored. Bumps live in
  `pyproject.toml`. If server changes depend on a specific pyremindkit
  release, pin the lower bound and explain why in CHANGELOG.

## Change Management Rules

- Make focused changes with clear intent.
- Do not leave partially migrated patterns behind.
- If you touch an operational workflow, update the docs in the same change.
- If you discover a misleading or stale instruction while working, fix it as part of the current task when reasonable.
- Do not silently ignore broken tooling or broken docs that are directly in the path of your task.

## Git Workflow Requirements

These rules are mandatory for every future agent working in this repository.

- After all requested work for a task or phase is complete, create a signed commit.
- Use `git commit -S` for signed commits.
- After the signed commit succeeds, push the current branch to `origin`.
- Do not leave completed work uncommitted locally.
- Do not declare a task fully complete until the signed commit and push have both succeeded.
- If signing or pushing fails, treat that as an unresolved blocker and report the exact failure.
- If the repository contains unrelated user changes, do not overwrite them. Stage and commit only the intended changes.

### Required Completion Sequence

1. Finish the implementation.
2. Update all relevant documentation.
3. Run relevant validation.
4. Review the diff for accuracy.
5. Create a signed commit with `git commit -S`.
6. Push to `origin`.
7. Only then report the task as complete.

## What Good Work Looks Like Here

- MCP tools remain stable and discoverable.
- Runtime scripts work after the repo moves to a new path.
- Docs match reality.
- Tests or verification steps are explicit and reproducible.
- Code is documented enough that another agent can continue safely.
- The final state is committed with a signed commit and pushed to `origin`.
