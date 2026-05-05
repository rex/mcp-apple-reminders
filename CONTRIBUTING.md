# Contributing

Thanks for your interest in `mcp-apple-reminders`. This is a small project, so
guidelines are short.

## Ground rules

- Be kind. See [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md).
- Bug reports and feature requests are welcome via [GitHub Issues](https://github.com/rex/mcp-apple-reminders/issues).
- For non-trivial changes, open an issue first to discuss the approach.
- Security issues: see [`SECURITY.md`](SECURITY.md).

## Development setup

```bash
git clone https://github.com/rex/mcp-apple-reminders.git
cd mcp-apple-reminders
./install.sh
source venv/bin/activate
pre-commit install
```

`install.sh` installs the package in editable mode with `[dev,test]` extras.

## Running checks

```bash
ruff check .
black --check .
mypy src/
pytest tests/unit/                                       # hermetic, no Reminders
MCP_APPLE_REMINDERS_LIVE_TESTS=1 pytest tests/integration/  # macOS only
```

The integration suite mutates your real Reminders database under a uniquely-
prefixed test list and cleans up after itself. Don't run it against a Reminders
account you care about.

## Commit & PR conventions

- Conventional Commits in subject lines (`feat:`, `fix:`, `docs:`, `refactor:`,
  `test:`, `chore:`).
- One logical change per PR.
- Update `CHANGELOG.md` under `[Unreleased]` for user-visible changes.
- Add or update tests for behavior changes.
- Run `pre-commit run --all-files` before pushing.

## Releasing (maintainers)

1. Bump `version` in `pyproject.toml` and `__version__` in `src/mcp_apple_reminders/__init__.py`.
2. Move `[Unreleased]` notes in `CHANGELOG.md` under a new dated heading.
3. `git tag vX.Y.Z && git push --tags`. The release workflow builds and publishes to PyPI.

## Project structure

```
src/mcp_apple_reminders/   Python package
  server.py                FastMCP server, tool/resource/prompt handlers
  _models.py               Pydantic input/output models
  resources.py             apple-reminders:// URI handlers
  prompts.py               ADHD workflow prompt templates
tests/
  unit/                    Hermetic, mock pyremindkit
  integration/             Live macOS Reminders, gated by env var
docs/
  tools.md                 Tool reference (auto-generated)
.github/                   CI, issue templates, dependabot
```
