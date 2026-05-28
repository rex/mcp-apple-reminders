"""Direct read-only access to the Reminders.app CoreData SQLite store.

Slice 1.0 of spec 002. Replaces slow EventKit iteration for the read-path
tools (`list_calendars`, `get_reminders`, `search_reminders`, `get_overdue_reminders`,
`get_today_reminders`, `get_reminder`). Reads a single SQLite database that
already contains every field we need including ReminderKit-only ones
(sections, subtasks, tags, alarms metadata, recurrence metadata) — so a lot
of Phase 3 work comes for free as soon as the schema is mapped.

### Schema (CoreData-flavored — every table starts with `Z`)

The store path is
`~/Library/Group Containers/group.com.apple.reminders/Container_v1/Stores/Data-*.sqlite`.
The largest `Data-*.sqlite` is the active one. Apple Reminders writes to
multiple stores when multiple accounts are signed in.

Key tables we touch:

- `ZREMCDBASELIST` — Reminder lists (a.k.a. calendars). `Z_ENT = 3` filters
  out smart lists. Columns: `Z_PK`, `ZNAME`, `ZCKIDENTIFIER` (the UUID that
  matches `EKCalendar.calendarIdentifier()`), `ZCOLOR`, `ZMARKEDFORDELETION`.
- `ZREMCDREMINDER` — Top-level + subtask reminders. Columns: `Z_PK`,
  `ZTITLE`, `ZNOTES`, `ZCOMPLETED`, `ZFLAGGED`, `ZPRIORITY`, `ZDUEDATE`,
  `ZCOMPLETIONDATE`, `ZCREATIONDATE`, `ZLASTMODIFIEDDATE`, `ZPARENTREMINDER`
  (Z_PK of the parent, NULL for top-level), `ZLIST` (Z_PK of the containing
  list), `ZICSURL` (attached URL), `ZCKIDENTIFIER` (UUID matching
  `EKReminder.calendarItemIdentifier()`), `ZMARKEDFORDELETION`,
  `ZACCOUNT` (NULL on orphaned rows — filter them out).
- `ZREMCDBASESECTION` — Sections within a list. Used by `assign_section`
  (Slice 1.8).

### Timestamps

CoreData stores dates as "seconds since the Apple epoch" (2001-01-01
00:00:00 UTC). Convert by adding `APPLE_EPOCH_OFFSET` (`978307200`) and
calling `datetime.fromtimestamp()`.

### Permissions

Reading the DB requires either Full Disk Access on the interpreter
binary OR an interpreter that already has Reminders TCC consent. The
conda Python in `./venv/bin/python3` works because it's been granted
Reminders consent (the same consent EventKit uses).

### Contract verified at S1.0 (deeplink UUID equivalence)

`EKReminder.calendarItemIdentifier()` and SQLite `ZCKIDENTIFIER` produce
the same UUID for the same reminder. Same for calendars. Verified live
against this machine's store on 2026-05-28. The deeplink helpers in
`mcp_apple_reminders.models` work identically from either path.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Iterator, Optional

from ..models import Calendar, Reminder, calendar_deeplink, reminder_deeplink

# CoreData timestamps are seconds since 2001-01-01 00:00:00 UTC.
APPLE_EPOCH_OFFSET = 978_307_200

DEFAULT_STORE_PATH = (
    Path.home() / "Library" / "Group Containers" / "group.com.apple.reminders" / "Container_v1" / "Stores"
)


class RemindersDBUnavailable(RuntimeError):  # noqa: N818 — historical name; matches the spec acceptance bullets.
    """Raised when the Reminders SQLite store can't be opened.

    Common reasons:
    - The Reminders app has never run on this user.
    - Full Disk Access has not been granted to the current interpreter and
      the conda Python's Reminders TCC consent does not cover the path.
    - The store dir layout changed across macOS releases (unlikely; the
      `Container_v1` path has been stable for years).

    Callers should catch this, log a warning via `ctx.warning`, and degrade
    to the EventKit read path.
    """


def find_db_path(store_dir: Path = DEFAULT_STORE_PATH) -> Path:
    """Return the path to the active `Data-*.sqlite` store (the largest one).

    Raises `RemindersDBUnavailable` if the store dir doesn't exist or has no
    candidates.
    """
    if not store_dir.is_dir():
        raise RemindersDBUnavailable(f"Reminders store dir not found: {store_dir}")
    candidates = sorted(
        store_dir.glob("Data-*.sqlite"),
        key=lambda p: p.stat().st_size,
        reverse=True,
    )
    if not candidates:
        raise RemindersDBUnavailable(f"No Data-*.sqlite files in {store_dir}")
    return candidates[0]


def connect(db_path: Optional[Path] = None) -> sqlite3.Connection:
    """Open a read-only connection to the Reminders SQLite store.

    Uses URI form (`file:...?mode=ro`) so SQLite refuses any write —
    defense in depth on top of the CoreData store-coordinator lock.
    `immutable=1` is intentionally NOT set: it would tell SQLite to assume
    the file never changes and cache the contents, which prevents the
    reader from seeing writes that the ReminderKit helper just made
    against the live store. With plain `mode=ro` we re-read the file
    state on each query.
    Sets `row_factory = sqlite3.Row` for column-name access.
    """
    path = db_path or find_db_path()
    try:
        conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    except sqlite3.OperationalError as e:
        raise RemindersDBUnavailable(f"Could not open {path}: {e}") from e
    conn.row_factory = sqlite3.Row
    return conn


# ---------------------------------------------------------------------------
# Private converters (underscore-prefixed; not part of the module's
# public-entry-point count enforced by `make check-architecture`).
# ---------------------------------------------------------------------------


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
        # sqlite3.Row needs `.keys()` to check column presence — `in row` queries values.
        modified_date=(_ts(row["ZLASTMODIFIEDDATE"]) if "ZLASTMODIFIEDDATE" in row.keys() else None),  # noqa: SIM118
        flagged=bool(row["ZFLAGGED"]),
        parent_reminder_id=None,
        subtasks=[],
        tags=[],
        section_name=None,
        completion_date=_ts(row["ZCOMPLETIONDATE"]),
        start_date=None,
        deeplink=reminder_deeplink(reminder_id),
    )


_REMINDER_COLS = (
    "r.Z_PK, r.ZTITLE, r.ZNOTES, r.ZCOMPLETED, r.ZFLAGGED, r.ZPRIORITY, "
    "r.ZDUEDATE, r.ZCOMPLETIONDATE, r.ZCREATIONDATE, r.ZLASTMODIFIEDDATE, "
    "r.ZPARENTREMINDER, r.ZICSURL, r.ZCKIDENTIFIER, "
    "l.ZCKIDENTIFIER AS list_ckid"
)


def _build_reminders_query(
    calendar_id: Optional[str],
    completed: Optional[bool],
    due_after: Optional[datetime],
    due_before: Optional[datetime],
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
    sql = (
        f"SELECT {_REMINDER_COLS} FROM ZREMCDREMINDER r "
        "LEFT JOIN ZREMCDBASELIST l ON r.ZLIST = l.Z_PK "
        f"WHERE {' AND '.join(where)} ORDER BY r.ZDUEDATE NULLS LAST, r.Z_PK"
    )
    return sql, params


# ---------------------------------------------------------------------------
# Public reader facade
# ---------------------------------------------------------------------------


class Reader:
    """Read-only facade over the Reminders.app SQLite store.

    Wraps a single `sqlite3.Connection` and exposes typed methods that return
    Pydantic `Calendar` / `Reminder` objects. The connection is *not* owned
    by this class — callers should manage its lifetime (typically via a
    `with` block around `connect()`).
    """

    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    # ----- introspection -----

    def schema_summary(self) -> dict:
        """Capture the table list at module-load time for diagnostics."""
        tables = [
            r["name"]
            for r in self._conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' " "AND name LIKE 'ZREMCD%' ORDER BY name"
            ).fetchall()
        ]
        required = {"ZREMCDBASELIST", "ZREMCDREMINDER", "ZREMCDBASESECTION"}
        missing = sorted(required - set(tables))
        return {"tables": tables, "required_present": not missing, "missing": missing}

    # ----- internal default-calendar lookup -----

    def _default_calendar_uuid(self) -> Optional[str]:
        """Return the UUID of the default new-reminder list, if recorded."""
        try:
            row = self._conn.execute(
                "SELECT ZACCOUNT, ZDEFAULTLIST FROM ZREMCDACCOUNTLISTDATA "
                "WHERE ZDEFAULTLIST IS NOT NULL ORDER BY Z_PK LIMIT 1"
            ).fetchone()
            if row and row["ZDEFAULTLIST"]:
                uuid_row = self._conn.execute(
                    "SELECT ZCKIDENTIFIER FROM ZREMCDBASELIST WHERE Z_PK = ?",
                    (row["ZDEFAULTLIST"],),
                ).fetchone()
                if uuid_row:
                    return str(uuid_row["ZCKIDENTIFIER"])
        except sqlite3.OperationalError:
            pass
        row = self._conn.execute(
            "SELECT ZCKIDENTIFIER FROM ZREMCDBASELIST "
            "WHERE ZMARKEDFORDELETION = 0 AND Z_ENT = 3 AND ZNAME = 'Reminders' LIMIT 1"
        ).fetchone()
        return str(row["ZCKIDENTIFIER"]) if row else None

    # ----- calendars -----

    def list_calendars(self) -> list[Calendar]:
        """Return every non-deleted user-visible reminder list."""
        default_uuid = self._default_calendar_uuid()
        rows = self._conn.execute(
            "SELECT Z_PK, ZNAME, ZCKIDENTIFIER, ZCOLOR FROM ZREMCDBASELIST "
            "WHERE ZMARKEDFORDELETION = 0 AND Z_ENT = 3 AND ZNAME IS NOT NULL AND ZNAME != '' "
            "ORDER BY ZNAME"
        ).fetchall()
        return [_calendar_from_row(r, default_uuid) for r in rows]

    def get_calendar_by_id(self, calendar_id: str) -> Optional[Calendar]:
        """Look up a calendar by its `ZCKIDENTIFIER` UUID."""
        default_uuid = self._default_calendar_uuid()
        row = self._conn.execute(
            "SELECT Z_PK, ZNAME, ZCKIDENTIFIER, ZCOLOR FROM ZREMCDBASELIST "
            "WHERE lower(ZCKIDENTIFIER) = lower(?) AND ZMARKEDFORDELETION = 0 AND Z_ENT = 3 LIMIT 1",
            (calendar_id,),
        ).fetchone()
        return _calendar_from_row(row, default_uuid) if row else None

    def get_calendar_by_name(self, name: str) -> Optional[Calendar]:
        """Look up a calendar by exact name."""
        default_uuid = self._default_calendar_uuid()
        row = self._conn.execute(
            "SELECT Z_PK, ZNAME, ZCKIDENTIFIER, ZCOLOR FROM ZREMCDBASELIST "
            "WHERE ZNAME = ? AND ZMARKEDFORDELETION = 0 AND Z_ENT = 3 LIMIT 1",
            (name,),
        ).fetchone()
        return _calendar_from_row(row, default_uuid) if row else None

    def search_calendars(self, query: str) -> list[Calendar]:
        """Case-insensitive substring search by calendar name."""
        default_uuid = self._default_calendar_uuid()
        rows = self._conn.execute(
            "SELECT Z_PK, ZNAME, ZCKIDENTIFIER, ZCOLOR FROM ZREMCDBASELIST "
            "WHERE ZMARKEDFORDELETION = 0 AND Z_ENT = 3 AND ZNAME IS NOT NULL "
            "AND lower(ZNAME) LIKE lower(?) ORDER BY ZNAME",
            (f"%{query}%",),
        ).fetchall()
        return [_calendar_from_row(r, default_uuid) for r in rows]

    # ----- reminders -----

    def iter_reminders(
        self,
        *,
        calendar_id: Optional[str] = None,
        completed: Optional[bool] = None,
        due_after: Optional[datetime] = None,
        due_before: Optional[datetime] = None,
        limit: Optional[int] = None,
    ) -> Iterator[Reminder]:
        """Stream reminders that match the supplied filters."""
        sql, params = _build_reminders_query(calendar_id, completed, due_after, due_before)
        if limit and limit > 0:
            sql += " LIMIT ?"
            params.append(int(limit))
        for row in self._conn.execute(sql, params):
            yield _reminder_from_row(row, str(row["list_ckid"] or ""))

    def get_reminder_by_id(self, reminder_id: str) -> Optional[Reminder]:
        """Look up a reminder by its `ZCKIDENTIFIER` UUID."""
        row = self._conn.execute(
            f"SELECT {_REMINDER_COLS} FROM ZREMCDREMINDER r "
            "LEFT JOIN ZREMCDBASELIST l ON r.ZLIST = l.Z_PK "
            "WHERE lower(r.ZCKIDENTIFIER) = lower(?) AND r.ZMARKEDFORDELETION = 0 "
            "ORDER BY r.Z_PK DESC LIMIT 1",
            (reminder_id,),
        ).fetchone()
        return _reminder_from_row(row, str(row["list_ckid"] or "")) if row else None

    def iter_subtasks(self, parent_uuid: str) -> Iterator[Reminder]:
        """Stream the subtasks of the reminder identified by `parent_uuid`.

        Subtasks are stored as `ZREMCDREMINDER` rows whose `ZPARENTREMINDER`
        column matches the parent's `Z_PK`. We resolve the parent's `Z_PK`
        first, then issue the WHERE clause against that integer.
        """
        parent_row = self._conn.execute(
            "SELECT Z_PK FROM ZREMCDREMINDER "
            "WHERE lower(ZCKIDENTIFIER) = lower(?) AND ZMARKEDFORDELETION = 0 LIMIT 1",
            (parent_uuid,),
        ).fetchone()
        if not parent_row:
            return
        parent_pk = parent_row["Z_PK"]
        cur = self._conn.execute(
            f"SELECT {_REMINDER_COLS} FROM ZREMCDREMINDER r "
            "LEFT JOIN ZREMCDBASELIST l ON r.ZLIST = l.Z_PK "
            "WHERE r.ZPARENTREMINDER = ? AND r.ZMARKEDFORDELETION = 0 AND r.ZACCOUNT IS NOT NULL "
            "ORDER BY r.Z_PK",
            (parent_pk,),
        )
        for row in cur:
            yield _reminder_from_row(row, str(row["list_ckid"] or ""))

    def search_reminders(self, query: str, *, limit: Optional[int] = None) -> list[Reminder]:
        """Case-insensitive substring search across `ZTITLE` and `ZNOTES`."""
        pattern = f"%{query}%"
        sql = (
            f"SELECT {_REMINDER_COLS} FROM ZREMCDREMINDER r "
            "LEFT JOIN ZREMCDBASELIST l ON r.ZLIST = l.Z_PK "
            "WHERE r.ZMARKEDFORDELETION = 0 AND r.ZACCOUNT IS NOT NULL "
            "AND (lower(r.ZTITLE) LIKE lower(?) OR lower(r.ZNOTES) LIKE lower(?)) "
            "ORDER BY r.ZDUEDATE NULLS LAST, r.Z_PK"
        )
        params: list = [pattern, pattern]
        if limit and limit > 0:
            sql += " LIMIT ?"
            params.append(int(limit))
        return [_reminder_from_row(r, str(r["list_ckid"] or "")) for r in self._conn.execute(sql, params)]


__all__ = [
    "APPLE_EPOCH_OFFSET",
    "DEFAULT_STORE_PATH",
    "Reader",
    "RemindersDBUnavailable",
    "connect",
    "find_db_path",
]
