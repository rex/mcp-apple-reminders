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


def _calendar_from_row(
    row: sqlite3.Row,
    default_uuid: Optional[str],
    *,
    parent_group_id: Optional[str] = None,
) -> Calendar:
    """Build a `Calendar` Pydantic from a `ZREMCDBASELIST` row.

    `is_group` is read from the `ZISGROUP` column when present (S5.1).
    `parent_group_id` is passed by the caller because the row alone only
    has the group's integer `Z_PK`; the caller is responsible for
    resolving that to a UUID via a join.
    """
    # sqlite3.Row needs `.keys()` to check column presence — `in row` queries values.
    row_keys = row.keys()  # noqa: SIM118
    cal_id = str(row["ZCKIDENTIFIER"])
    is_group = bool(row["ZISGROUP"]) if "ZISGROUP" in row_keys else False
    return Calendar(
        id=cal_id,
        name=row["ZNAME"] or "",
        color=str(row["ZCOLOR"] or ""),
        is_default=(cal_id == default_uuid),
        owner=None,
        deeplink=calendar_deeplink(cal_id),
        is_group=is_group,
        parent_group_id=parent_group_id,
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
    calendar_ids: Optional[list[str]] = None,
    completion_after: Optional[datetime] = None,
    completion_before: Optional[datetime] = None,
) -> tuple[str, list]:
    where = ["r.ZMARKEDFORDELETION = 0", "r.ZACCOUNT IS NOT NULL"]
    params: list = []
    if calendar_id is not None:
        where.append("lower(l.ZCKIDENTIFIER) = lower(?)")
        params.append(calendar_id)
    if calendar_ids:
        placeholders = ", ".join("?" for _ in calendar_ids)
        where.append(f"lower(l.ZCKIDENTIFIER) IN ({placeholders})")
        params.extend(c.lower() for c in calendar_ids)
    if completed is not None:
        where.append("r.ZCOMPLETED = ?")
        params.append(1 if completed else 0)
    if due_after is not None:
        where.append("r.ZDUEDATE >= ?")
        params.append(due_after.timestamp() - APPLE_EPOCH_OFFSET)
    if due_before is not None:
        where.append("r.ZDUEDATE <= ?")
        params.append(due_before.timestamp() - APPLE_EPOCH_OFFSET)
    if completion_after is not None:
        where.append("r.ZCOMPLETIONDATE >= ?")
        params.append(completion_after.timestamp() - APPLE_EPOCH_OFFSET)
    if completion_before is not None:
        where.append("r.ZCOMPLETIONDATE < ?")
        params.append(completion_before.timestamp() - APPLE_EPOCH_OFFSET)
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


def _resolve_section_name(conn: sqlite3.Connection, reminder_uuid: str) -> Optional[str]:
    """Resolve a reminder's section_name via the parent list's membership blob.

    Section memberships live in `ZREMCDBASELIST.ZMEMBERSHIPSOFREMINDERSINSECTIONSASDATA`
    as a JSON document keyed by reminder UUID. Returns None if the reminder
    is unsectioned or the blob is empty.
    """
    import json

    row = conn.execute(
        "SELECT l.Z_PK, l.ZMEMBERSHIPSOFREMINDERSINSECTIONSASDATA AS blob "
        "FROM ZREMCDREMINDER r JOIN ZREMCDBASELIST l ON r.ZLIST = l.Z_PK "
        "WHERE lower(r.ZCKIDENTIFIER) = lower(?) AND r.ZMARKEDFORDELETION = 0 LIMIT 1",
        (reminder_uuid,),
    ).fetchone()
    if not row or not row["blob"]:
        return None
    try:
        data = json.loads(row["blob"])
    except (TypeError, json.JSONDecodeError):
        return None
    membership = next(
        (m for m in data.get("memberships", []) if m.get("memberID") == reminder_uuid),
        None,
    )
    if not membership:
        return None
    group_id = membership.get("groupID")
    if not group_id:
        return None
    section_row = conn.execute(
        "SELECT ZDISPLAYNAME FROM ZREMCDBASESECTION "
        "WHERE lower(ZCKIDENTIFIER) = lower(?) AND ZMARKEDFORDELETION = 0 LIMIT 1",
        (group_id,),
    ).fetchone()
    return str(section_row["ZDISPLAYNAME"]) if section_row else None


__all__ = [
    "APPLE_EPOCH_OFFSET",
    "_REMINDER_COLS",
    "_build_reminders_query",
    "_calendar_from_row",
    "_reminder_from_row",
    "_resolve_section_name",
    "_ts",
]
