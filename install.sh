#!/bin/bash
# MCP Apple Reminders — local development installer
# Sets up a virtual environment and installs the package in editable mode.
# End users should prefer `uvx mcp-apple-reminders` or `pipx install mcp-apple-reminders`.

set -euo pipefail

echo "MCP Apple Reminders — dev installer"
echo "===================================="

if [[ "$OSTYPE" != "darwin"* ]]; then
    echo "Error: this MCP server is macOS-only (it depends on EventKit)." >&2
    exit 1
fi

find_python() {
    local candidate
    for candidate in python3.13 python3.12 python3.11 python3.10 python3; do
        if command -v "$candidate" >/dev/null 2>&1 && \
            "$candidate" -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)" 2>/dev/null; then
            echo "$candidate"
            return 0
        fi
    done
    return 1
}

echo "Looking for Python 3.10+..."
if ! PYTHON_BIN="$(find_python)"; then
    echo "Error: Python 3.10 or newer is required." >&2
    echo "Install via Homebrew: brew install python@3.12" >&2
    exit 1
fi
PYTHON_VERSION="$("$PYTHON_BIN" -c 'import sys; print(".".join(map(str, sys.version_info[:3])))')"
echo "Using $(command -v "$PYTHON_BIN") (Python $PYTHON_VERSION)"

if [[ ! -d "venv" ]]; then
    echo "Creating venv/"
    "$PYTHON_BIN" -m venv venv
fi

# shellcheck disable=SC1091
source venv/bin/activate

echo "Upgrading pip"
python -m pip install --upgrade pip

echo "Installing mcp-apple-reminders (editable, with dev + test extras)"
python -m pip install -e ".[dev,test]"

echo
echo "Installation complete."
echo
echo "Recommended Claude Desktop / Codex config: use 'uvx mcp-apple-reminders'"
echo "(install uv via 'brew install uv' or 'curl -LsSf https://astral.sh/uv/install.sh | sh')"
echo
echo "For development with this checkout, point your client at:"
echo "  command: $(pwd)/venv/bin/python3"
echo "  args:    [\"-m\", \"mcp_apple_reminders\"]"
