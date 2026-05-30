"""Module-private helpers extracted from `_native/sqlite.py` for the
architecture-line-limit gate.

Re-exported through `sqlite.py` so the public surface (`Reader`,
`RemindersDBUnavailable`, `connect`, `find_db_path`) is unchanged.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from typing import Iterator, Optional

from ..models import Calendar, Reminder, calendar_deeplink, reminder_deeplink
from ._color import decode_list_color

APPLE_EPOCH_OFFSET = 978_307_200

_REMINDER_COLS = (
    "r.Z_PK, r.ZTITLE, r.ZNOTES, r.ZCOMPLETED, r.ZFLAGGED, r.ZPRIORITY, "
    "r.ZDUEDATE, r.ZCOMPLETIONDATE, r.ZCREATIONDATE, r.ZLASTMODIFIEDDATE, "
    "r.ZPARENTREMINDER, r.ZICSURL, r.ZCKIDENTIFIER, "
    "l.ZCKIDENTIFIER AS list_ckid, "
    "(SELECT group_concat(h.ZNAME, ',') FROM ZREMCDOBJECT o "
    "JOIN ZREMCDHASHTAGLABEL h ON o.ZHASHTAGLABEL = h.Z_PK "
    "WHERE o.ZREMINDER3 = r.Z_PK) AS tags_csv, "
    "(SELECT p.ZCKIDENTIFIER FROM ZREMCDREMINDER p WHERE p.Z_PK = r.ZPARENTREMINDER) AS parent_ckid, "
    "(SELECT group_concat(c.ZCKIDENTIFIER, ',') FROM ZREMCDREMINDER c "
    "WHERE c.ZPARENTREMINDER = r.Z_PK AND c.ZMARKEDFORDELETION = 0) AS subtask_ckids, "
    "r.ZDUEDATEDELTAALERTSDATA AS early_blob"
)


def _ts(value: Optional[float]) -> Optional[datetime]:
    """Convert a CoreData timestamp (or None) to a naive local datetime."""
    if value is None:
        return None
    return datetime.fromtimestamp(value + APPLE_EPOCH_OFFSET)


_DELTA_UNIT = {0: "day", 1: "week", 2: "month", 3: "year", 4: "hour"}


def _early_reminders_from_blob(blob) -> list[str]:
    """Decode ZDUEDATEDELTAALERTSDATA (JSON) into human early-reminder summaries.

    e.g. {"dueDateDeltaAlerts": [{"dueDateDeltaCount": -1, "dueDateDeltaUnit": 2}]}
    -> ["1 month before due"]. Returns [] for NULL/garbage blobs.
    """
    if not blob:
        return []
    try:
        data = json.loads(bytes(blob))
    except (TypeError, ValueError):
        return []
    out: list[str] = []
    for alert in data.get("dueDateDeltaAlerts", []):
        count = alert.get("dueDateDeltaCount")
        unit = alert.get("dueDateDeltaUnit")
        if count is None or unit is None:
            continue
        n = abs(int(count))
        word = _DELTA_UNIT.get(int(unit), "unit")
        plural = "s" if n != 1 else ""
        when = "after due" if int(count) > 0 else "before due"
        out.append(f"{n} {word}{plural} {when}")
    return out


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
        color=decode_list_color(row["ZCOLOR"]),
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
    parent_ckid = row["parent_ckid"] if "parent_ckid" in row_keys else None
    subtasks_csv = row["subtask_ckids"] if "subtask_ckids" in row_keys else None
    subtasks = [s for s in (subtasks_csv or "").split(",") if s]
    early = _early_reminders_from_blob(row["early_blob"] if "early_blob" in row_keys else None)
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
        parent_reminder_id=str(parent_ckid) if parent_ckid else None,
        subtasks=subtasks,
        tags=tags,
        section_name=None,
        completion_date=_ts(row["ZCOMPLETIONDATE"]),
        start_date=None,
        deeplink=reminder_deeplink(reminder_id),
        early_reminders=early,
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
    flagged: Optional[bool] = None,
    marked_for_deletion: bool = False,
) -> tuple[str, list]:
    where = ["r.ZMARKEDFORDELETION = ?", "r.ZACCOUNT IS NOT NULL"]
    params: list = [1 if marked_for_deletion else 0]
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
    if flagged is not None:
        where.append("r.ZFLAGGED = ?")
        params.append(1 if flagged else 0)
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


def _stream_reminders(
    conn: sqlite3.Connection,
    sql: str,
    params: list,
    limit: Optional[int],
) -> Iterator[Reminder]:
    """Apply an optional LIMIT, execute the query, and yield mapped reminders.

    Shared by `Reader.iter_reminders` and `Reader.iter_recently_deleted` so the
    streaming tail lives in one place.
    """
    if limit and limit > 0:
        sql += " LIMIT ?"
        params.append(int(limit))
    for row in conn.execute(sql, params):
        yield _reminder_from_row(row, str(row["list_ckid"] or ""))


def _resolve_section_name(conn: sqlite3.Connection, reminder_uuid: str) -> Optional[str]:
    """Resolve a reminder's section_name via the parent list's membership blob.

    Section memberships live in `ZREMCDBASELIST.ZMEMBERSHIPSOFREMINDERSINSECTIONSASDATA`
    as a JSON document keyed by reminder UUID. Returns None if the reminder
    is unsectioned or the blob is empty.
    """
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
    "_stream_reminders",
    "_ts",
]
