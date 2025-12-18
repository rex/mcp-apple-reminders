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

# Check Python version
PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
REQUIRED_VERSION="3.10"

echo "📋 Checking Python version..."
if ! python3 -c "import sys; exit(0 if sys.version_info >= (3, 10) else 1)"; then
    echo "❌ Error: Python 3.10 or higher is required (found $PYTHON_VERSION)"
    exit 1
fi
echo "✓ Python $PYTHON_VERSION detected"
echo ""

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
    echo "✓ Virtual environment created"
else
    echo "✓ Virtual environment already exists"
fi
echo ""

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "📦 Upgrading pip..."
pip install --upgrade pip --quiet

# Install dependencies
echo "📦 Installing dependencies..."
pip install -r requirements.txt --quiet
echo "✓ Dependencies installed"
echo ""

# Install the package in development mode
echo "📦 Installing mcp-apple-reminders..."
pip install -e . --quiet
echo "✓ Package installed"
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
echo "   See README.md for detailed usage instructions."
