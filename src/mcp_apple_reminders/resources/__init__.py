"""MCP Resources surface — Slice 2.1.

Importing this package registers the four canonical reminders:// resources
against the shared FastMCP instance via the decorators in `reminders.py`.
"""

from __future__ import annotations

from . import reminders

__all__ = ["reminders"]
