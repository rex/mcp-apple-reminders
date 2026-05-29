"""Bulk-operation tools — Slice 3.4.

Three operations wrap the existing per-item paths (`update_reminder`,
`delete_reminder`, `move_reminder`) with `_native/bulk.py::bulk_iter`
progress reporting + elicitation guards on the destructive call
(`bulk_delete_completed`).

All three return a structured `{ "processed": int, "failed": list[dict] }`
report so the caller can show a per-item outcome.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from mcp.server.fastmcp import Context
from pydantic import BaseModel

from .._native.bulk import bulk_iter
from .._native.sqlite import Reader, RemindersDBUnavailable
from ..lifespan import app_context as _app_context
from ..models import Reminder, native_reminder_to_pydantic
from ..server import mcp


@mcp.tool(
    name="bulk_complete",
    description=(
        "Mark a list of reminder IDs as completed. Returns a per-item "
        "outcome so the caller can see which ids failed (e.g. missing "
        "reminders). Reports progress as it goes."
    ),
)
async def bulk_complete(reminder_ids: list[str], ctx: Context) -> dict:
    """Mark each reminder in `reminder_ids` as completed."""
    if not reminder_ids:
        return {"processed": 0, "failed": []}

    app = _app_context(ctx)
    processed = 0
    failed: list[dict] = []
    async for rid in bulk_iter(reminder_ids, ctx, label="Completing reminder", total=len(reminder_ids)):
        try:
            app.bridge.update_reminder(rid, is_completed=True)
            processed += 1
        except Exception as e:  # noqa: BLE001 — per-item failures surface in the report.
            failed.append({"id": rid, "error": str(e)})

    await ctx.info(f"bulk_complete: processed={processed} failed={len(failed)}")
    return {"processed": processed, "failed": failed}


@mcp.tool(
    name="bulk_move",
    description=(
        "Move a list of reminder IDs to a target calendar. Returns a per-item " "outcome and reports progress."
    ),
)
async def bulk_move(reminder_ids: list[str], calendar_id: str, ctx: Context) -> dict:
    """Move each reminder in `reminder_ids` to `calendar_id`."""
    if not reminder_ids:
        return {"processed": 0, "failed": []}

    app = _app_context(ctx)
    processed = 0
    failed: list[dict] = []
    async for rid in bulk_iter(reminder_ids, ctx, label="Moving reminder", total=len(reminder_ids)):
        try:
            app.bridge.move_reminder(rid, calendar_id)
            processed += 1
        except Exception as e:  # noqa: BLE001
            failed.append({"id": rid, "error": str(e)})

    await ctx.info(f"bulk_move: processed={processed} failed={len(failed)}")
    return {"processed": processed, "failed": failed, "target_calendar_id": calendar_id}


class _ConfirmBulkDelete(BaseModel):
    """Empty schema — the user just needs to accept/decline the elicitation."""


@mcp.tool(
    name="bulk_delete_completed",
    description=(
        "Permanently delete every completed reminder whose completion_date "
        "falls in [start, end). DESTRUCTIVE — surfaces an elicitation prompt "
        "before the cascade fires so the client can confirm. Half-open window: "
        "passing the same datetime for both is a no-op."
    ),
)
async def bulk_delete_completed(
    start: str,
    end: str,
    ctx: Context,
    calendar_id: Optional[str] = None,
) -> dict:
    """Delete completed reminders whose completion_date is in [start, end)."""
    start_dt = datetime.fromisoformat(start)
    end_dt = datetime.fromisoformat(end)
    if end_dt < start_dt:
        raise ValueError("end must be >= start")

    app = _app_context(ctx)
    try:
        with app.open_sqlite() as conn:
            candidates: list[Reminder] = list(
                Reader(conn).iter_reminders(
                    completed=True,
                    completion_after=start_dt,
                    completion_before=end_dt,
                    calendar_id=calendar_id,
                )
            )
    except RemindersDBUnavailable as e:
        await ctx.error(f"SQLite unavailable; can't enumerate candidates: {e}")
        raise ValueError(f"SQLite read path unavailable ({e}).") from e

    if not candidates:
        await ctx.info("bulk_delete_completed: nothing in window.")
        return {"processed": 0, "failed": [], "window": {"start": start, "end": end}}

    # Elicitation guard — best-effort. Older SDKs without ctx.elicit fall through.
    try:
        elicitation = await ctx.elicit(
            message=(
                f"About to permanently delete {len(candidates)} completed reminder(s) "
                f"whose completion_date is in [{start}, {end}). This cannot be undone. "
                f"Confirm?"
            ),
            schema=_ConfirmBulkDelete,
        )
        if elicitation.action != "accept":
            raise ValueError(f"bulk_delete_completed aborted by elicitation ({elicitation.action}).")
    except AttributeError:
        await ctx.debug("Elicitation not available; skipping confirm.")

    await ctx.warning(f"Bulk-deleting {len(candidates)} reminder(s) in [{start}, {end}).")
    processed = 0
    failed: list[dict] = []
    async for r in bulk_iter(candidates, ctx, label="Deleting reminder", total=len(candidates)):
        try:
            app.bridge.delete_reminder(r.id)
            processed += 1
        except Exception as e:  # noqa: BLE001
            failed.append({"id": r.id, "error": str(e)})

    await ctx.info(f"bulk_delete_completed: processed={processed} failed={len(failed)}")
    return {
        "processed": processed,
        "failed": failed,
        "window": {"start": start, "end": end},
    }


# Avoid an unused-import lint hit while keeping the converter ready for future use.
_unused = native_reminder_to_pydantic  # noqa: F841
