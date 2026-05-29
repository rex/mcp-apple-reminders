"""CL-2.1 — smart-list tool tests.

Default run: input guards + registration (no artifacts created). The live
create→delete round-trip is opt-in via REM_LIVE_HELPER=1 and self-cleans.
"""

from __future__ import annotations

import asyncio
import os

import pytest

from mcp_apple_reminders._native.reminderkit import DEFAULT_HELPER_PATH as RK_HELPER
from mcp_apple_reminders._native.reminderkit_lists import (
    create_smart_list,
    delete_smart_list,
    update_smart_list,
)


def _list_tools():
    from mcp_apple_reminders.server import mcp

    return asyncio.run(mcp.list_tools())


def test_smart_list_tools_registered():
    names = {t.name for t in _list_tools()}
    assert {"create_smart_list", "update_smart_list", "delete_smart_list"}.issubset(names)


def test_create_smart_list_requires_name():
    with pytest.raises(ValueError, match="non-empty"):
        create_smart_list("")
    with pytest.raises(ValueError, match="non-empty"):
        create_smart_list("   ")


def test_update_smart_list_requires_id():
    with pytest.raises(ValueError, match="non-empty"):
        update_smart_list("")


def test_delete_smart_list_requires_id():
    with pytest.raises(ValueError, match="non-empty"):
        delete_smart_list("")


@pytest.mark.skipif(
    os.environ.get("REM_LIVE_HELPER") != "1" or not RK_HELPER.exists(),
    reason="Set REM_LIVE_HELPER=1 with the ReminderKit helper built to run the live smart-list round-trip.",
)
def test_live_smart_list_round_trip():
    """Create a custom smart list, then delete it (self-cleaning)."""
    resp = create_smart_list("REM-TEST-SMARTLIST-CL21", emoji="🧪")
    sid = str(resp.get("id") or "")
    assert sid, f"no id returned: {resp!r}"
    try:
        upd = update_smart_list(sid, name="REM-TEST-SMARTLIST-CL21b")
        assert upd.get("status") in {"updated", "ok"}
    finally:
        import contextlib

        with contextlib.suppress(Exception):
            delete_smart_list(sid)
