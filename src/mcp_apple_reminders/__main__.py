"""Entry point for running mcp_apple_reminders as a module.

This file allows the package to be run using:
    python -m mcp_apple_reminders
"""

import asyncio
from .server import main

if __name__ == "__main__":
    asyncio.run(main())
