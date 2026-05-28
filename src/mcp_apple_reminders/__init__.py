"""MCP Apple Reminders - Model Context Protocol server for Apple Reminders integration.

This package provides a comprehensive MCP server that enables Claude and other AI assistants
to interact with Apple Reminders through the EventKit framework.
"""

__version__ = "0.1.0"
__author__ = "Pierce"
__license__ = "MIT"

from .server import cli_main, mcp

__all__ = ["cli_main", "mcp"]
