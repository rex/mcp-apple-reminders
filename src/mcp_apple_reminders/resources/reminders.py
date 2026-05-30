"""Four canonical MCP Resources, all served from the SQLite reader.

URI patterns:

- `reminders://default` — the user's default list, with reminders.
- `reminders://overdue` — incomplete reminders whose due date is past.
- `reminders://today` — reminders due in the current local day.
- `reminders://list/{calendar_id}` — a specific list by UUID.
- `reminders://recently-deleted` — items marked for deletion, not yet purged.
- `reminders://tags` — every distinct tag in use on live reminders.

Each resource returns JSON: `{"reminders": [Reminder, …], "context": {...}}`.

The Reader is sub-millisecond on the test store, so these are essentially
free for the client to poll. They are the agent-visibility-plane payoff.
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from .._native.sqlite import Reader, RemindersDBUnavailable, connect
from ..server import mcp


def _reminders_payload(reminders: list, **context: Any) -> str:
    payload = {
        "reminders": [r.model_dump(mode="json") for r in reminders],
        "context": context,
    }
    return json.dumps(payload, default=str)


@mcp.resource(
    uri="reminders://default",
    name="Default list",
    title="Default List",
    description=(
        "The user's default reminder list with all incomplete reminders inside it. "
        "Sourced via the SQLite reader; sub-millisecond."
    ),
    mime_type="application/json",
)
def default_list() -> str:
    """Return the default list and its incomplete reminders."""
    try:
        with connect() as conn:
            reader = Reader(conn)
            default_uuid = reader._default_calendar_uuid()  # noqa: SLF001 — module-internal contract
            if not default_uuid:
                return _reminders_payload([], note="No default calendar resolved.")
            cal = reader.get_calendar_by_id(default_uuid)
            reminders_list = list(reader.iter_reminders(calendar_id=default_uuid, completed=False))
            return _reminders_payload(
                reminders_list,
                calendar=cal.model_dump(mode="json") if cal else None,
            )
    except RemindersDBUnavailable as e:
        return _reminders_payload([], error=f"SQLite unavailable: {e}")


@mcp.resource(
    uri="reminders://overdue",
    name="Overdue reminders",
    title="Overdue Reminders",
    description="Incomplete reminders whose due date is in the past. Sub-millisecond via SQLite.",
    mime_type="application/json",
)
def overdue_reminders() -> str:
    """Return incomplete reminders whose due date is past."""
    now = datetime.now()
    try:
        with connect() as conn:
            results = list(Reader(conn).iter_reminders(completed=False, due_before=now))
            return _reminders_payload(results, due_before=now.isoformat(), incomplete_only=True)
    except RemindersDBUnavailable as e:
        return _reminders_payload([], error=f"SQLite unavailable: {e}")


@mcp.resource(
    uri="reminders://today",
    name="Today's reminders",
    title="Today's Reminders",
    description="Incomplete reminders due in the current local day. Sub-millisecond via SQLite.",
    mime_type="application/json",
)
def today_reminders() -> str:
    """Return incomplete reminders due today."""
    now = datetime.now()
    start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end_of_day = now.replace(hour=23, minute=59, second=59, microsecond=999999)
    try:
        with connect() as conn:
            results = list(
                Reader(conn).iter_reminders(
                    completed=False,
                    due_after=start_of_day,
                    due_before=end_of_day,
                )
            )
            return _reminders_payload(
                results,
                window={"start": start_of_day.isoformat(), "end": end_of_day.isoformat()},
                incomplete_only=True,
            )
    except RemindersDBUnavailable as e:
        return _reminders_payload([], error=f"SQLite unavailable: {e}")


@mcp.resource(
    uri="reminders://list/{calendar_id}",
    name="Specific list",
    title="List by ID",
    description=(
        "Reminders inside a specific list identified by its UUID. Substitute "
        "the UUID into the path: e.g. reminders://list/A6D35949-…"
    ),
    mime_type="application/json",
)
def list_by_id(calendar_id: str) -> str:
    """Return reminders inside the given list."""
    try:
        with connect() as conn:
            reader = Reader(conn)
            cal = reader.get_calendar_by_id(calendar_id)
            if cal is None:
                return _reminders_payload([], error=f"Calendar {calendar_id!r} not found.", calendar_id=calendar_id)
            results = list(reader.iter_reminders(calendar_id=calendar_id))
            return _reminders_payload(
                results,
                calendar=cal.model_dump(mode="json"),
            )
    except RemindersDBUnavailable as e:
        return _reminders_payload([], error=f"SQLite unavailable: {e}")


@mcp.resource(
    uri="reminders://recently-deleted",
    name="Recently deleted",
    title="Recently Deleted",
    description=(
        "Reminders marked for deletion but not yet purged (recoverable in "
        "Reminders.app). Read-only recovery view via the SQLite reader."
    ),
    mime_type="application/json",
)
def recently_deleted_reminders() -> str:
    """Return reminders in the Recently Deleted view."""
    try:
        with connect() as conn:
            results = list(Reader(conn).iter_recently_deleted())
            return _reminders_payload(results, marked_for_deletion=True)
    except RemindersDBUnavailable as e:
        return _reminders_payload([], error=f"SQLite unavailable: {e}")


@mcp.resource(
    uri="reminders://tags",
    name="All tags",
    title="All Tags",
    description="Every distinct hashtag/tag in use on live (non-deleted) reminders, sorted. Sub-millisecond via SQLite.",
    mime_type="application/json",
)
def all_tags() -> str:
    """Return the sorted list of distinct tags currently in use."""
    try:
        with connect() as conn:
            rows = conn.execute(
                "SELECT DISTINCT h.ZNAME FROM ZREMCDHASHTAGLABEL h "
                "JOIN ZREMCDOBJECT o ON o.ZHASHTAGLABEL = h.Z_PK "
                "JOIN ZREMCDREMINDER r ON o.ZREMINDER3 = r.Z_PK "
                "WHERE r.ZMARKEDFORDELETION = 0 AND h.ZNAME IS NOT NULL AND h.ZNAME != '' "
                "ORDER BY h.ZNAME"
            ).fetchall()
            tags = [str(row[0]) for row in rows]
            return json.dumps({"tags": tags, "count": len(tags)}, default=str)
    except RemindersDBUnavailable as e:
        return json.dumps({"tags": [], "error": f"SQLite unavailable: {e}"})
