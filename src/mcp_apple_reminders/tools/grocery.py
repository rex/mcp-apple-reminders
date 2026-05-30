"""Grocery MCP tools — CL-2.4.

`categorize_grocery_items` runs Apple's on-device grocery categorization over a
set of reminders in a grocery-enabled list (the produce/dairy/bakery grouping in
Reminders.app). Backed by the Obj-C ReminderKit helper (private API).
"""

from __future__ import annotations

from mcp.server.fastmcp import Context

from .._native.reminderkit import ReminderKitHelperError, ReminderKitHelperUnavailable
from .._native.reminderkit_content import categorize_grocery_items as helper_categorize_grocery_items
from ..server import mcp
from ._annotations import MUTATE


@mcp.tool(
    name="categorize_grocery_items",
    title="Categorize Grocery Items",
    annotations=MUTATE,
    description=(
        "Auto-categorize grocery reminders (produce, dairy, bakery, …) within a "
        "grocery-enabled list. Pass the list UUID and the reminder UUIDs to "
        "categorize. The list must already have Grocery mode enabled in "
        "Reminders.app. Private ReminderKit API."
    ),
)
async def categorize_grocery_items(list_id: str, reminder_ids: list[str], ctx: Context) -> dict:
    """Categorize `reminder_ids` within grocery list `list_id`."""
    if not list_id or not list_id.strip():
        raise ValueError("list_id is required and must be non-empty")
    if not reminder_ids:
        raise ValueError("reminder_ids must be a non-empty list")
    try:
        resp = helper_categorize_grocery_items(list_id, reminder_ids)
    except ReminderKitHelperUnavailable as e:
        raise ValueError(f"ReminderKit helper not built. Run `make build-native`. ({e})") from e
    except ReminderKitHelperError as e:
        raise ValueError(e.message) from e
    n = resp.get("remindersCategorized", len(reminder_ids))
    await ctx.info(f"Categorized {n} grocery item(s) in list {list_id}")
    return {"list_id": list_id, "reminders_categorized": n, "status": resp.get("status", "updated")}
