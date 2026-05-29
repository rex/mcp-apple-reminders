"""Module-private helpers extracted from `_native/sqlite.py` for the
architecture-line-limit gate.

Re-exported through `sqlite.py` so the public surface (`Reader`,
`RemindersDBUnavailable`, `connect`, `find_db_path`) is unchanged.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime
from typing import Optional

from ..models import Calendar, Reminder, calendar_deeplink, reminder_deeplink

APPLE_EPOCH_OFFSET = 978_307_200

_REMINDER_COLS = (
    "r.Z_PK, r.ZTITLE, r.ZNOTES, r.ZCOMPLETED, r.ZFLAGGED, r.ZPRIORITY, "
    "r.ZDUEDATE, r.ZCOMPLETIONDATE, r.ZCREATIONDATE, r.ZLASTMODIFIEDDATE, "
    "r.ZPARENTREMINDER, r.ZICSURL, r.ZCKIDENTIFIER, "
    "l.ZCKIDENTIFIER AS list_ckid, "
    "(SELECT group_concat(h.ZNAME, ',') FROM ZREMCDOBJECT o "
    "JOIN ZREMCDHASHTAGLABEL h ON o.ZHASHTAGLABEL = h.Z_PK "
    "WHERE o.ZREMINDER3 = r.Z_PK) AS tags_csv"
)


def _ts(value: Optional[float]) -> Optional[datetime]:
    """Convert a CoreData timestamp (or None) to a naive local datetime."""
    if value is None:
        return None
    return datetime.fromtimestamp(value + APPLE_EPOCH_OFFSET)


def _calendar_from_row(row: sqlite3.Row, default_uuid: Optional[str]) -> Calendar:
    cal_id = str(row["ZCKIDENTIFIER"])
    return Calendar(
        id=cal_id,
        name=row["ZNAME"] or "",
        color=str(row["ZCOLOR"] or ""),
        is_default=(cal_id == default_uuid),
        owner=None,
        deeplink=calendar_deeplink(cal_id),
    )


def _reminder_from_row(row: sqlite3.Row, list_uuid: str) -> Reminder:
    reminder_id = str(row["ZCKIDENTIFIER"])
    # sqlite3.Row needs `.keys()` to check column presence — `in row` queries values.
    row_keys = row.keys()  # noqa: SIM118
    tags_csv = row["tags_csv"] if "tags_csv" in row_keys else None
    tags = [t for t in (tags_csv or "").split(",") if t]
    return Reminder(
        id=reminder_id,
        title=row["ZTITLE"] or "",
        due_date=_ts(row["ZDUEDATE"]),
        notes=row["ZNOTES"],
        completed=bool(row["ZCOMPLETED"]),
        url=row["ZICSURL"],
        priority=row["ZPRIORITY"] or 0,
        list_id=list_uuid,
        created_date=_ts(row["ZCREATIONDATE"]),
        modified_date=_ts(row["ZLASTMODIFIEDDATE"]) if "ZLASTMODIFIEDDATE" in row_keys else None,
        flagged=bool(row["ZFLAGGED"]),
        parent_reminder_id=None,
        subtasks=[],
        tags=tags,
        section_name=None,
        completion_date=_ts(row["ZCOMPLETIONDATE"]),
        start_date=None,
        deeplink=reminder_deeplink(reminder_id),
    )


def _build_reminders_query(
    calendar_id: Optional[str],
    completed: Optional[bool],
    due_after: Optional[datetime],
    due_before: Optional[datetime],
    tags: Optional[list[str]] = None,
) -> tuple[str, list]:
    where = ["r.ZMARKEDFORDELETION = 0", "r.ZACCOUNT IS NOT NULL"]
    params: list = []
    if calendar_id is not None:
        where.append("lower(l.ZCKIDENTIFIER) = lower(?)")
        params.append(calendar_id)
    if completed is not None:
        where.append("r.ZCOMPLETED = ?")
        params.append(1 if completed else 0)
    if due_after is not None:
        where.append("r.ZDUEDATE >= ?")
        params.append(due_after.timestamp() - APPLE_EPOCH_OFFSET)
    if due_before is not None:
        where.append("r.ZDUEDATE <= ?")
        params.append(due_before.timestamp() - APPLE_EPOCH_OFFSET)
    if tags:
        placeholders = ", ".join("?" for _ in tags)
        where.append(
            "r.Z_PK IN ("
            "SELECT DISTINCT o.ZREMINDER3 FROM ZREMCDOBJECT o "
            "JOIN ZREMCDHASHTAGLABEL h ON o.ZHASHTAGLABEL = h.Z_PK "
            f"WHERE h.ZNAME IN ({placeholders}))"
        )
        params.extend(tags)
    sql = (
        f"SELECT {_REMINDER_COLS} FROM ZREMCDREMINDER r "
        "LEFT JOIN ZREMCDBASELIST l ON r.ZLIST = l.Z_PK "
        f"WHERE {' AND '.join(where)} ORDER BY r.ZDUEDATE NULLS LAST, r.Z_PK"
    )
    return sql, params


__all__ = [
    "APPLE_EPOCH_OFFSET",
    "_REMINDER_COLS",
    "_build_reminders_query",
    "_calendar_from_row",
    "_reminder_from_row",
    "_ts",
]
