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
from .._native.eventkit import (
    set_location_alarm as helper_set_location_alarm,
)
from .._native.eventkit import (
    set_recurrence as helper_set_recurrence,
)
from ..server import mcp
from ._annotations import CREATE, MUTATE


@mcp.tool(
    name="set_alarm",
    title="Set Alarm",
    annotations=CREATE,
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


@mcp.tool(
    name="set_location_alarm",
    title="Set Location Alarm",
    annotations=CREATE,
    description=(
        "Add a geofenced (location-based) alarm to a reminder. Fires when "
        "the user enters or leaves a circular geofence centered on the "
        "given coordinates. Use `proximity='enter'` for arrival alarms "
        "and `'leave'` for departure alarms."
    ),
)
async def set_location_alarm(
    reminder_id: str,
    latitude: float,
    longitude: float,
    ctx: Context,
    location_title: Optional[str] = None,
    radius_m: float = 100.0,
    proximity: str = "enter",
) -> dict:
    """Add a location-based alarm via the Swift helper.

    Args:
        reminder_id: Target reminder UUID.
        latitude: Decimal degrees, -90 to 90.
        longitude: Decimal degrees, -180 to 180.
        location_title: Human-readable label. Optional.
        radius_m: Geofence radius in meters. Default 100. Optional.
        proximity: 'enter' (default) or 'leave'. Optional.
    """
    try:
        result = helper_set_location_alarm(
            reminder_id,
            latitude,
            longitude,
            location_title=location_title,
            radius_m=radius_m,
            proximity=proximity,
        )
    except EventKitHelperUnavailable as e:
        await ctx.error(f"EventKit helper unavailable: {e}")
        raise ValueError(f"EventKit helper not built. Run `make build-native`. ({e})") from e
    except EventKitHelperError as e:
        await ctx.error(f"set_location_alarm failed: {e.message}")
        raise ValueError(e.message) from e

    await ctx.info(
        f"Set location alarm on reminder {reminder_id}: "
        f"({latitude}, {longitude}) r={radius_m}m proximity={proximity}"
    )
    return result


@mcp.tool(
    name="set_recurrence",
    title="Set Recurrence",
    annotations=MUTATE,
    description=(
        "Set a recurrence rule on a reminder. `frequency` must be one of "
        "`daily`, `weekly`, `monthly`, `yearly`. `interval` defaults to 1 "
        "(every cycle). Optional `days_of_week` (ISO 1=Mon…7=Sun) and "
        "`days_of_month` (1–31) refine `weekly`/`monthly`. Optional ISO "
        "`end_iso` stops the recurrence; omit for infinite."
    ),
)
async def set_recurrence(
    reminder_id: str,
    frequency: str,
    ctx: Context,
    interval: int = 1,
    days_of_week: Optional[list[int]] = None,
    days_of_month: Optional[list[int]] = None,
    end_iso: Optional[str] = None,
) -> dict:
    """Set a recurrence rule on a reminder via the Swift helper.

    Args:
        reminder_id: Target reminder UUID.
        frequency: `daily` / `weekly` / `monthly` / `yearly`.
        interval: Every N cycles. Default 1.
        days_of_week: ISO weekday numbers (1=Mon…7=Sun). Optional.
        days_of_month: 1–31. Optional.
        end_iso: When the recurrence stops. Optional.
    """
    try:
        result = helper_set_recurrence(
            reminder_id,
            frequency,
            interval=interval,
            days_of_week=days_of_week,
            days_of_month=days_of_month,
            end_iso=end_iso,
        )
    except EventKitHelperUnavailable as e:
        await ctx.error(f"EventKit helper unavailable: {e}")
        raise ValueError(f"EventKit helper not built. Run `make build-native`. ({e})") from e
    except EventKitHelperError as e:
        await ctx.error(f"set_recurrence failed: {e.message}")
        raise ValueError(e.message) from e

    await ctx.info(f"Set recurrence on reminder {reminder_id}: {frequency} every {interval}")
    return result
