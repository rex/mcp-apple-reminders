"""Bulk-operation skeleton — Slice 2.3.

Helpers that wrap an iterable with per-item progress reporting. Used by the
bulk tool handlers (`bulk_complete`, `bulk_delete_completed`, `bulk_move`).

- `ctx.report_progress(progress=i, total=n, message=...)` sends a
  `notifications/progress` to the client so a UI can render a progress bar.

Cancellation propagates naturally: if the client cancels the request, the
`await` points raise `asyncio.CancelledError` (a `BaseException`, so it is not
swallowed by per-item `except Exception` handlers) and the bulk loop unwinds.
mcp 1.27's `ServerSession` exposes no `check_cancellation()` polling method, so
we rely on that built-in propagation rather than a speculative poll.
"""

from __future__ import annotations

from typing import AsyncIterator, Iterable, TypeVar

from mcp.server.fastmcp import Context

T = TypeVar("T")


async def bulk_iter(
    items: Iterable[T],
    ctx: Context,
    *,
    label: str = "Processing",
    total: int | None = None,
) -> AsyncIterator[T]:
    """Stream items with per-item progress reporting.

    Args:
        items: The items to walk. If `total` is omitted, we materialize
            `items` into a list to count it — pass an explicit `total`
            for already-materialized lists where the count is cheap.
        ctx: The tool's `Context`.
        label: User-visible progress message prefix.
        total: Total count for the progress bar.

    Yields:
        Each item, after reporting progress on it.
    """
    materialized: list[T]
    if total is None:
        materialized = list(items)
        total = len(materialized)
    else:
        materialized = list(items) if not isinstance(items, list) else items  # type: ignore[assignment]

    for index, item in enumerate(materialized, start=1):
        await ctx.report_progress(
            progress=index,
            total=total,
            message=f"{label} {index}/{total}",
        )
        yield item


__all__ = ["bulk_iter"]
