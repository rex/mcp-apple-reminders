"""Test configuration shared across the unit and integration suites.

The unit suite is hermetic — it runs on Linux and macOS without the real
pyremindkit dependency, by stubbing the module out before mcp_apple_reminders
imports it.

The integration suite mutates a real Apple Reminders database. It is gated
behind ``MCP_APPLE_REMINDERS_LIVE_TESTS=1`` and skipped on non-Darwin or when
the env var is unset.
"""

from __future__ import annotations

import os
import sys

import pytest


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Skip integration tests unless explicitly opted in."""
    if os.environ.get("MCP_APPLE_REMINDERS_LIVE_TESTS") == "1" and sys.platform == "darwin":
        return
    skip_integration = pytest.mark.skip(
        reason="set MCP_APPLE_REMINDERS_LIVE_TESTS=1 on macOS to run live Reminders tests",
    )
    for item in items:
        if "integration" in item.keywords:
            item.add_marker(skip_integration)
