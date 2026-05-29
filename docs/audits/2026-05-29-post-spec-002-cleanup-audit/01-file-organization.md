# 01 — File-organization audit

**Agent**: general-purpose / Opus.
**Prompt**: "Audit file organization and layout. Find what's badly placed."
**Already known going in** (excluded from this report):
- 28 `test_*.py` at repo root → `tests/`.
- 10 stale root markdowns from Dec 2025 / March 2026.
- Duplicate `TOOLS.md` (root, stale) + `docs/TOOLS.md` (new auto-gen).

## Findings (verbatim)

### Root-level

1. **Tracked `.DS_Store` files at 4 paths** — `./.DS_Store`, `./src/.DS_Store`, `./src/mcp_apple_reminders/.DS_Store`, `./images/.DS_Store`. `.gitignore` covers `.DS_Store` but these were committed before. Untracked from git, also `git rm --cached`.

2. **`mcp-server-apple-reminders.log` at repo root** (1.6 K, last touched Dec 17 2025, pre-retrofit). `*.log` is ignored — was added before. `git rm` it; it's stale and stdout-leak forensic noise from before the FastMCP migration.

3. **`requirements.txt` is redundant** — `pyproject.toml` declares the same `mcp>=1.27,<2`, `pydantic>=2.10`, and `pyobjc-*>=12.0,<13` pins under `[project.dependencies]`. Two sources of truth → drift risk. Delete `requirements.txt`; install path is editable-install via `pyproject.toml`.

4. **`AGENTS.md.pre-retrofit`** (205 lines, preserved manually) — git history already preserves it (commit `afd56ac^`). Delete; the comment in `AGENTS.md` claims it's "preserved for reference" but it's just dead weight.

5. **`GEMINI.md` is an identical 85-line duplicate of `CLAUDE.md`/`AGENTS.md`.** All three are symlinks-or-copies of the same content. Verify symlink status; if duplicate file, replace `GEMINI.md` with symlink → `AGENTS.md`.

6. **`PROGRESS.md` (71 lines) is superseded by `TASK_STATE.md` (179 lines).** Both committed PR2/PR4. CLAUDE.md references PROGRESS only as historical context. Merge any unique content into TASK_STATE.md and delete PROGRESS.md.

7. **`MAP.md` at root (70 lines)** — overview doc, belongs alongside the rest of the architecture docs. Move to `docs/MAP.md`.

### Source tree (`src/mcp_apple_reminders/`)

8. **`tools/sections.py` grouping is misleading** — file is named "sections" but houses `get_subtasks` + `set_parent` + `assign_section`. Subtasks aren't sections; they're a parent-child relationship. Module docstring already admits "Lives apart from `tools/reminders.py` so each file stays under the 400-line limit." Rename to `tools/relationships.py` (or split: subtasks → `tools/subtasks.py`, sections stays in `tools/sections.py` as only `assign_section`).

9. **`_native/` mixes Python wrappers, Swift/Obj-C source, and compiled binaries flatly** — 11 `.py` files at the same depth as `src/` and `bin/`. Split: keep Python modules at `_native/`, move sources under `_native/src/` (already done), but the Python is messy. `core.py` + `calendars.py` + `models.py` are the legacy pyremindkit-era `RemindKit`/`Calendar` dataclass layer (per docstrings); `eventkit.py` + `reminderkit.py` + `sqlite.py` + `bulk.py` are the new three-tier wrappers. Group as `_native/legacy/` (core, calendars, models, _internal) and `_native/wrappers/` (eventkit, reminderkit, sqlite, _sqlite_helpers, bulk). Or — if `core.py`/`calendars.py`/`models.py`/`_internal.py` are unused dead code post-S0.4 — delete them entirely (`grep -r "from .*_native.core import\|from .*_native.calendars import"` will tell you).

10. **`_native/THIRD_PARTY_NOTICES.md`** belongs at `docs/` or root next to LICENSE, not buried in an underscore-prefixed package dir where attribution is invisible to a casual reader.

### test_support/

11. **`test_support/` is fine in principle, but lives at repo root next to the to-be-relocated `tests/`** — when `test_*.py` move into `tests/`, move `test_support/` to `tests/_support/` (or `tests/support/`) so imports become `from tests._support.harness`. Currently `from test_support.harness` only resolves because cwd is the repo root.

### scripts/

12. **No issues.** All 6 scripts are `uv run --script` single-file tools with PEP 723 inline metadata, all touched in PR1 (`afd56ac`). `sync_skeleton.py` is for `/sync-skills`, `check_*.py` are gate enforcers wired into Makefile. Clean.

### specs/

13. **`specs/_archive/001-visibility-foundation/`** has all 5 spec files (spec, plan, design, tasks + README). Parked correctly; no action.

14. **`specs/002-modernize-and-foundation/` is missing a README.md** — the `_archive/001/` has one, the in-flight 002 doesn't. Add a one-pager pointing to `spec.md`.

### .claude/

15. **`.claude/agents/terraform-reviewer.md` + `.claude/commands/terraform-plan.md` + `.claude/rules/terraform.md` + `.claude/rules/ansible.md`** — all 4 dead in a Python-only macOS MCP repo. Delete; they're skeleton spillover.

16. **`.claude/commands/scaffold.md` + `retrofit.md`** — these greenfield/brownfield bootstrap commands are inside an already-retrofitted repo. No project use; delete.

17. **`.claude/session-context.md`** — frozen at `2026-05-28`, describes mode/stack/autonomy. Either auto-update or delete; current content is stale (says "vendored pyremindkit" which was renamed in S0.2).

---

**Total**: 17 distinct findings beyond the 3 already known.
