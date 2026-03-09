#!/bin/bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="${SCRIPT_DIR}/venv/bin/python3"

if [[ ! -x "${PYTHON_BIN}" ]]; then
    echo "Error: expected Python runtime at ${PYTHON_BIN}" >&2
    echo "Run ./install.sh first, or update your MCP config to point at a valid interpreter." >&2
    exit 1
fi

# This attempts to talk to Reminders so macOS can surface the permission prompt
# before the MCP stdio server starts speaking JSON.
osascript -e 'tell application "Reminders" to name of default list' > /dev/stderr 2>&1 || true

exec "${PYTHON_BIN}" -m mcp_apple_reminders
