# 04 — Build / config / skeleton-drift audit

**Agent**: general-purpose / Opus.
**Prompt**: "Find broken or stale build / config / tooling artifacts. Skeleton drift specifically called out by session-start hook."

## Findings (verbatim)

### 1. VIBE.yaml — FINE
Lifecycle + stack + gates accurate. `exclude_globs` correctly limited to `_native/src/*.swift|*.m`. `tests.mode: deferred` is correct since `pyproject.testpaths=["tests"]` doesn't match the root-level `test_*.py` files (tests run via explicit paths per AGENTS.md §3).

### 2. `pyproject.toml`
- **HIGH — `[tool.pytest.ini_options].testpaths = ["tests"]`** (line 71). Tests live at repo root (`test_*.py`, 28 files). Running bare `pytest` discovers zero tests. Fix: change to `testpaths = ["."]` with appropriate `python_files` glob, **or** leave it and document — AGENTS.md §3 already requires explicit paths, but `testpaths=["tests"]` is actively misleading (signals a `tests/` dir that doesn't exist).
- **MEDIUM — `authors` line 10**: `"pierce@example.com"` is a placeholder. Fix: real email or drop the field.
- **MEDIUM — `[project.urls]`**: `github.com/yourusername/...` placeholders. Fix: remove or set real URL.
- **MEDIUM — `dev` extras** missing `pre-commit` (used by `make check-precommit`), `pyyaml` (used by scripts), and stub-packages `pyobjc-stubs` (mypy already silenced via `--ignore-missing-imports`). Fix: add to `[project.optional-dependencies].dev`.

### 3. `requirements.txt`
- **MEDIUM — drift from `pyproject.toml`**. `requirements.txt` lacks `pyobjc-framework-Foundation` block ordering, no dev tools, no comment explaining it's a subset. `install.sh` calls `pip install -r requirements.txt` then `pip install -e .` — the latter handles deps anyway, so requirements.txt is redundant. Fix: either delete it (preferred) or regenerate via `pip-compile`.

### 4. `Makefile`
- **MEDIUM — `make lint` paths** (lines 205, 207): `src/ test_*.py test_support/`. This works at repo root via shell glob but breaks if invoked from a subdir, and will rot the moment tests move under `tests/`. Fix: keep shell-expanded glob but plan to switch when relocation lands.
- **MEDIUM — `make test`** runs only the VIBE.yaml mode probe; doesn't actually call pytest. Acceptable while `mode: deferred`, but AGENTS.md §3 says to run 3 specific files — that's not what `make test` does. Fix: add a hidden target `test-actual:` that runs the §3 list explicitly.
- **LOW — Makefile drift** flagged by `check-skeleton` is "advisory" — `build-native` / `clean-native` are project-specific additions. Reconcile by hand isn't urgent.
Otherwise FINE.

### 5. `.pre-commit-config.yaml` — FINE
Local hooks reference live scripts (`scripts/check_architecture.py`, `check_module_rules.py`, `check_version_bumped.py`). All present.

### 6. `install.sh`
- **HIGH** — README snippet `from mcp_apple_reminders import main` (line 84) **fails**: actual export is `cli_main`. `install.sh`'s suggested Claude/Codex configs are correct (`-m mcp_apple_reminders`). Fix is in README §2, not here. `install.sh` itself: FINE.

### 7. `shim_mcp.sh` — FINE
4 lines of bash, points at `./venv/bin/python3 -m mcp_apple_reminders`. Current with S0.4.

### 8. `verify_setup.py` — FINE
Has S0.1 (MCP>=1.27), S0.2 (`_native` package), S0.6 (`rem_eventkit`/`rem_reminderkit` --ping), and S1.4 (ReminderKit availability flag) probes. Solid.

### 9. `.mcp.json` — FINE
Serena, context7, sequential-thinking, github — all current.

### 10. `.env.example` — FINE
Two optional vars, both still consumed.

### 11. `.claude/` tree
- **HIGH — `.claude/session-context.md`** (lines 4–5): `stack: ... vendored pyremindkit ...` and `updated: 2026-05-28T00:00:00`. Stale (pyremindkit renamed to `_native` in S0.2). Fix: update `stack:` line + bump `updated:`.
- **LOW** — `.claude/commands/scaffold.md`, `retrofit.md` reference `CLAUDE.md + GEMINI.md symlinks`. Repo has a real `GEMINI.md` file (not symlink). Cosmetic.
Agents and rules: FINE.

### 12. `.gitignore` — FINE
`src/mcp_apple_reminders/_native/bin/` ignored. `venv/` ignored. `.serena/`, `.claude/serena-initialized`, caches all covered.

### 13. `scripts/`
6 scripts present (`bump_version`, `check_version_bumped`, `check_architecture`, `check_module_rules`, `check_docs`, `sync_skeleton`). All referenced by Makefile/pre-commit. FINE except: **HIGH — 3 of them drift from agentic-skeleton v0.37.0** (see §14).

### 14. Skeleton drift (`make check-skeleton`)
**HIGH** — 3 skeleton-owned files drifted from v0.37.0:
- `.claude/hooks/auto-commit.sh`
- `.claude/hooks/changelog-append.sh`
- `.claude/hooks/stop-gate.sh`

Advisory drift: `Makefile`. Fix: `make sync-skeleton` for the three hooks (verbatim files); reconcile Makefile by hand to preserve `build-native`/`clean-native`.

### 15. `CHANGELOG.md` — FINE
Format consistent, 0.1.41 placeholder was already backfilled in 0.1.42 (the "fix-forward" entry). Bump tooling works (`make bump-patch` exercises `scripts/bump_version.py`).
*(Note: Audit 02 found two earlier placeholders `[0.1.9]` and `[0.1.11]` still unfilled — Audit 04 missed those.)*

### 16. Claude Desktop / Codex / Claude Code snippet integrity
- **HIGH — `README.md` line 84**: `from mcp_apple_reminders import main; print('Installation successful!')` — `main` does NOT exist; only `cli_main` and `mcp` are exported. Confirmed via `./venv/bin/python -c "from mcp_apple_reminders import main"` → `ImportError`. Fix: `from mcp_apple_reminders import cli_main`.
- **HIGH — `README.md` §§Architecture (lines 645–855)**: huge stale block on `libs/pyremindkit/`, `RemindKit (libs/pyremindkit/core.py)`. Renamed in S0.2 to `src/mcp_apple_reminders/_native/`. Fix: rewrite the architecture diagrams + paragraphs (8 lines mention `pyremindkit`).
- **HIGH — `README.md` makes no mention of**: FastMCP (S0.4), Resources (S2.1), Prompts (S2.2), Sampling (S2.5), Alarms / Recurrence / Bulk ops, the visibility-plane / agents://current Resource (S4.1), or streamable-HTTP opt-in (S4.3). The README undersells the server by ~15 tools and 6 capability families. Fix: regenerate from `TOOLS.md` + `docs/TOOLS.md`.
- **MEDIUM — `claude_desktop_config.example.json`** uses bare `python3` — README warns against exactly this. Fix: use `/path/to/.../venv/bin/python3` placeholder, mirroring `install.sh`'s recommended snippet.
- **MEDIUM — stale `FIXES_FOR_CLAUDE_DESKTOP.md` / `TESTING_REPORT.md`** both reference `from .server import main` (broken). Fix: update or delete (low-value historical docs).
- **MEDIUM — pyremindkit doc-string ghosts** in 3 source files (`_native/__init__.py`, `_native/_internal.py`, `_native/models.py`). Just module docstring text — fully cosmetic but lies about the package name. Fix: s/pyremindkit/mcp_apple_reminders._native/.

## Summary by severity

| Severity | Count | Top items |
|---|---|---|
| **CRITICAL** | 0 | — |
| **HIGH** | 6 | `pyproject.testpaths` lies; README `main` ImportError; README architecture section pre-S0.2; README missing 15+ tools / S2/S3/S4 features; `session-context.md` stale; 3 hooks drifted from skeleton v0.37.0 |
| **MEDIUM** | 8 | author/url placeholders; `dev` extras incomplete; `requirements.txt` redundant; `claude_desktop_config.example.json` uses bare python3; `make test` doesn't run §3 tests; stale `FIXES_FOR_CLAUDE_DESKTOP.md` & `TESTING_REPORT.md`; pyremindkit docstring ghosts; Makefile advisory drift |
| **LOW** | 1 | `.claude/commands/*` symlink wording cosmetic |

Gates are not lying — lint/typecheck pass cleanly, architecture gate green, version-bump gate green. The drift is concentrated in user-facing docs (README) and the skeleton-owned hook files.
