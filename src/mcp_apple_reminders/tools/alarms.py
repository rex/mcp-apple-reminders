"""Alarm + recurrence tools — Slices 3.1–3.3.

S3.1 — `set_alarm` (time-based) ships here. S3.2 (location alarms) and
S3.3 (recurrence) will land alongside as the spec rolls forward.
"""

from __future__ import annotations

from typing import Optional

from mcp.server.fastmcp import Context

from .._native.eventkit import (
    EventKitHelperError,
    EventKitHelperUnavailable,
)
from .._native.eventkit import (
    set_alarm as helper_set_alarm,
)
from ..server import mcp


@mcp.tool(
    name="set_alarm",
    description=(
        "Set or clear time-based alarm(s) on a reminder. `when` accepts a "
        "relative duration (e.g. '1h', '30m', '2d') OR an ISO-format absolute "
        "datetime (e.g. '2026-06-15T09:00:00'). Pass `clear=true` to wipe "
        "existing alarms — combine with `when` to replace, or omit `when` "
        "to leave the reminder with no alarms."
    ),
)
async def set_alarm(
    reminder_id: str,
    ctx: Context,
    when: Optional[str] = None,
    clear: bool = False,
) -> dict:
    """Set or clear a reminder's time-based alarm via the Swift helper.

    Args:
        reminder_id: The reminder's UUID.
        when: Relative duration ('1h', '30m', '2d', '15s') or absolute ISO datetime. Optional.
        clear: Wipe existing alarms before setting the new one. Optional.
    """
    if not reminder_id or not reminder_id.strip():
        raise ValueError("reminder_id is required and must be non-empty")
    if when is None and not clear:
        raise ValueError("Pass `when` to set an alarm, or `clear=true` to remove existing alarms")

    try:
        result = helper_set_alarm(reminder_id, when, clear=clear)
    except EventKitHelperUnavailable as e:
        await ctx.error(f"EventKit helper unavailable: {e}")
        raise ValueError(f"EventKit helper binary not built. Run `make build-native`. ({e})") from e
    except EventKitHelperError as e:
        await ctx.error(f"set_alarm failed: {e.message}")
        raise ValueError(e.message) from e

    await ctx.info(f"Updated alarms on reminder {reminder_id}: clear={clear}, when={when!r}")
    return result
