"""Bulk-operation skeleton — Slice 2.3.

Helpers that wrap an iterable with per-item progress reporting + cancellation
checks. Used by bulk tool handlers in Phase 3 (`bulk_complete`,
`bulk_delete_completed`, `bulk_move`).

The two checks:

- `ctx.report_progress(progress=i, total=n, message=...)` — sends a
  `notifications/progress` to the client so a UI can render a progress bar.
- `ctx.session.check_cancellation()` (when available) — lets the client
  cancel mid-operation; we raise `BulkCancelled` if it triggers.

Cancellation isn't universally implemented across MCP clients yet; treat
its absence as "no cancel signal, keep going."
"""

from __future__ import annotations

from typing import AsyncIterator, Iterable, TypeVar

from mcp.server.fastmcp import Context

T = TypeVar("T")


class BulkCancelled(RuntimeError):  # noqa: N818 — descriptive name; consumers know it's an exception.
    """Raised mid-iteration when the client signals cancellation."""


async def bulk_iter(
    items: Iterable[T],
    ctx: Context,
    *,
    label: str = "Processing",
    total: int | None = None,
) -> AsyncIterator[T]:
    """Stream items with per-item progress + cancellation reporting.

    Args:
        items: The items to walk. If `total` is omitted, we materialize
            `items` into a list to count it — pass an explicit `total`
            for already-materialized lists where the count is cheap.
        ctx: The tool's `Context`.
        label: User-visible progress message prefix.
        total: Total count for the progress bar.

    Yields:
        Each item, after reporting progress on it.

    Raises:
        BulkCancelled: client signaled cancellation.
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
        # Cancellation check is best-effort; not every client supports it.
        # The Context.session may expose `check_cancellation` in a future
        # MCP SDK release — guard with hasattr so we don't blow up today.
        session = getattr(ctx, "session", None)
        if session is not None and hasattr(session, "check_cancellation"):
            try:
                await session.check_cancellation()
            except Exception as e:  # pragma: no cover — best-effort path
                raise BulkCancelled(f"Client cancelled the bulk op: {e}") from e

        yield item


__all__ = ["BulkCancelled", "bulk_iter"]
