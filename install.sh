#!/bin/bash

# MCP Apple Reminders Installation Script
# This script sets up a virtual environment and installs all dependencies

set -e  # Exit on error

echo "🍎 MCP Apple Reminders Installation"
echo "===================================="
echo ""

# Check if we're on macOS
if [[ "$OSTYPE" != "darwin"* ]]; then
    echo "❌ Error: This MCP server only works on macOS"
    exit 1
fi

find_python() {
    local candidate
    for candidate in python3.13 python3.12 python3.11 python3.10 python3; do
        if command -v "$candidate" >/dev/null 2>&1 && \
            "$candidate" -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)"; then
            echo "$candidate"
            return 0
        fi
    done

    return 1
}

echo "📋 Checking Python version..."
if ! PYTHON_BIN="$(find_python)"; then
    PYTHON_VERSION="$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))' 2>/dev/null || echo "unknown")"
    echo "❌ Error: Python 3.10 or higher is required (default python3 is ${PYTHON_VERSION})"
    echo "   Install Python 3.10+ and re-run this script, or invoke it with a newer interpreter on PATH."
    exit 1
fi
PYTHON_VERSION="$("$PYTHON_BIN" -c 'import sys; print(".".join(map(str, sys.version_info[:3])))')"
echo "✓ Python $PYTHON_VERSION detected"
echo "  Using interpreter: $(command -v "$PYTHON_BIN")"
echo ""

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    "$PYTHON_BIN" -m venv venv
    echo "✓ Virtual environment created"
else
    echo "✓ Virtual environment already exists"
fi
echo ""

# Activate virtual environment
echo "🔧 Activating virtual environment..."
# shellcheck source=/dev/null
source venv/bin/activate

# Upgrade pip
echo "📦 Upgrading pip..."
python -m pip install --upgrade pip --quiet

# Install the package in development mode (deps resolve from pyproject.toml)
echo "📦 Installing mcp-apple-reminders..."
python -m pip install -e . --quiet
echo "✓ Package installed"
echo ""

# Build the native EventKit + ReminderKit helpers (borrowed from viticci/remctl
# MIT — see src/mcp_apple_reminders/_native/THIRD_PARTY_NOTICES.md). Requires
# Xcode CLI tools (swiftc + clang).
if command -v swiftc >/dev/null 2>&1 && command -v clang >/dev/null 2>&1; then
    echo "🔨 Building native helpers (rem_eventkit + rem_reminderkit)..."
    if command -v make >/dev/null 2>&1 && make build-native >/dev/null 2>&1; then
        echo "✓ Native helpers compiled"
    else
        echo "⚠️  make build-native failed — Reminders writes that need the helpers will degrade."
        echo "   Run \`make build-native\` manually after install to see the compiler error."
    fi
else
    echo "⚠️  swiftc / clang not found — Xcode CLI tools missing."
    echo "   Install with: xcode-select --install"
    echo "   Then run: make build-native"
fi
echo ""

echo "✅ Installation complete!"
echo ""
echo "📝 Next steps:"
echo "   1. Activate the virtual environment:"
echo "      source venv/bin/activate"
echo ""
echo "   2. Configure Claude Desktop by editing:"
echo "      ~/Library/Application Support/Claude/claude_desktop_config.json"
echo ""
echo "   3. Add this configuration:"
echo "      {"
echo "        \"mcpServers\": {"
echo "          \"apple-reminders\": {"
echo "            \"command\": \"$(pwd)/venv/bin/python3\","
echo "            \"args\": [\"-m\", \"mcp_apple_reminders\"]"
echo "          }"
echo "        }"
echo "      }"
echo ""
echo "   4. Restart Claude Desktop"
echo ""
echo "   5. Configure Codex by editing:"
echo "      ~/.codex/config.toml"
echo ""
echo "      [mcp_servers.mcp-apple-reminders]"
echo "      command = \"$(pwd)/venv/bin/python3\""
echo "      args = [\"-m\", \"mcp_apple_reminders\"]"
echo "      cwd = \"$(pwd)\""
echo "      enabled = true"
echo ""
echo "   See README.md for detailed usage instructions."
