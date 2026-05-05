"""MCP Apple Reminders — conversational ADHD task management for Claude.

A Model Context Protocol server that exposes Apple Reminders as tools,
resources, and prompts to LLM clients (Claude Desktop, Codex, Cursor,
Cline, etc.) on macOS.
"""

__version__ = "0.2.0"
__license__ = "MIT"

from .server import cli_main, main

__all__ = ["cli_main", "main", "__version__"]
