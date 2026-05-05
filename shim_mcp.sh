#!/bin/bash
# Pre-flight launcher for first-time use:
# triggers the macOS Reminders TCC permission prompt before the MCP stdio server starts.
# Use this only on first launch if your MCP client doesn't surface the prompt;
# afterwards, point the client at the Python interpreter directly.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="${SCRIPT_DIR}/venv/bin/python3"

if [[ ! -x "${PYTHON_BIN}" ]]; then
    echo "Error: expected Python runtime at ${PYTHON_BIN}" >&2
    echo "Run ./install.sh first, or update your MCP config to point at a valid interpreter." >&2
    exit 1
fi

# Trigger the Reminders permission prompt without polluting stderr (MCP clients
# treat stderr noise as errors).
osascript -e 'tell application "Reminders" to name of default list' >/dev/null 2>&1 || true

exec "${PYTHON_BIN}" -m mcp_apple_reminders
