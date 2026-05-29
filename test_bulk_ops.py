"""Slice 3.4 — bulk_complete + bulk_move + bulk_delete_completed.

Unit-level coverage of input handling and the empty-input fast path.
Live bulk round-trips are intentionally not exercised here — they'd
require fabricating dozens of test reminders and policing cleanup
across multiple bridge paths. The per-item paths (complete, move,
delete) are exercised by other tests; bulk just wraps them with
progress reporting + elicitation.
"""

from __future__ import annotations

import asyncio

import pytest

from mcp_apple_reminders.server import mcp


def _list_tools():
    return asyncio.run(mcp.list_tools())


def test_three_bulk_tools_registered():
    names = {t.name for t in _list_tools()}
    assert {"bulk_complete", "bulk_move", "bulk_delete_completed"}.issubset(names)


def test_bulk_delete_completed_validates_window():
    """end < start raises ValueError synchronously."""
    from mcp_apple_reminders.tools.bulk import bulk_delete_completed

    async def go():
        # ctx is None — we expect the validation to fire before we touch it.
        try:
            await bulk_delete_completed(start="2026-05-01T00:00:00", end="2026-04-01T00:00:00", ctx=None)
        except ValueError as e:
            return str(e)
        return None

    msg = asyncio.run(go())
    assert msg and "end" in msg


def test_bulk_complete_with_empty_list_returns_zero_processed():
    """Empty input returns the canonical empty report without touching the bridge."""
    from mcp_apple_reminders.tools.bulk import bulk_complete

    out = asyncio.run(bulk_complete(reminder_ids=[], ctx=None))
    assert out == {"processed": 0, "failed": []}


def test_bulk_move_with_empty_list_returns_zero_processed():
    from mcp_apple_reminders.tools.bulk import bulk_move

    out = asyncio.run(bulk_move(reminder_ids=[], calendar_id="X", ctx=None))
    assert out == {"processed": 0, "failed": []}


def test_valid_routes_unused_import_silenced():
    """Module-level sanity check — the deferred `native_reminder_to_pydantic` import shouldn't crash."""
    from mcp_apple_reminders.tools import bulk

    # `_unused` proves the deferred import resolved without exception.
    assert hasattr(bulk, "_unused")


# pytest config — we don't yield from any external state, suppress xdist warnings.
pytestmark = pytest.mark.filterwarnings("ignore::DeprecationWarning")
