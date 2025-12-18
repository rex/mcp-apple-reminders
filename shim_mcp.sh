#!/bin/bash

# 1. The "Wake Up" Call
# This attempts to talk to Reminders. macOS will pause this script
# and show you the "Allow" pop-up on your screen.
# We redirect output to stderr so we don't break the JSON-RPC pipe.
osascript -e 'tell application "Reminders" to name of default list' > /dev/stderr 2>&1

# 2. The Handoff
# Once you click "Allow", this line runs and your server takes over.
exec /Users/pierce/Code/mcp-apple-reminders/venv/bin/python3 -m mcp_apple_reminders
