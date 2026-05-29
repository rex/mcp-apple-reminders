"""Slice 2.3 — bulk_iter smoke test."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

from mcp_apple_reminders._native.bulk import bulk_iter


def test_bulk_iter_yields_all_items_and_reports_progress():
    ctx = MagicMock()
    ctx.report_progress = AsyncMock()
    ctx.session = None

    async def run():
        out = []
        async for item in bulk_iter(["a", "b", "c"], ctx, label="step", total=3):
            out.append(item)
        return out

    out = asyncio.run(run())
    assert out == ["a", "b", "c"]
    assert ctx.report_progress.await_count == 3
    # Check the call args of the final progress report.
    last_call = ctx.report_progress.await_args_list[-1]
    assert last_call.kwargs["progress"] == 3
    assert last_call.kwargs["total"] == 3
    assert "step 3/3" in last_call.kwargs["message"]


def test_bulk_iter_computes_total_when_omitted():
    ctx = MagicMock()
    ctx.report_progress = AsyncMock()
    ctx.session = None

    async def run():
        out = []
        async for item in bulk_iter([1, 2], ctx, label="x"):
            out.append(item)
        return out

    out = asyncio.run(run())
    assert out == [1, 2]
    assert ctx.report_progress.await_args_list[0].kwargs["total"] == 2
