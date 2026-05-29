"""Direct read-only access to the Reminders.app CoreData SQLite store.

Slice 1.0 — see `docs/SQLITE_SCHEMA.md` for the full schema breakdown,
column mapping, timestamp/epoch notes, and the deeplink UUID equivalence
contract verified at slice ship.

Public surface:

- `Reader(conn)` — facade class wrapping a connection with typed read
  methods.
- `RemindersDBUnavailable` — raised when the store can't be opened.
- `connect(db_path=None)` + `find_db_path(store_dir=...)` — open/locate.
- `APPLE_EPOCH_OFFSET` constant.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Iterator, Optional

from ..models import Calendar, Reminder
from ._sqlite_helpers import (
    _REMINDER_COLS,
    APPLE_EPOCH_OFFSET,
    _build_reminders_query,
    _calendar_from_row,
    _reminder_from_row,
)

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
        calendar_ids: Optional[list[str]] = None,
        completed: Optional[bool] = None,
        due_after: Optional[datetime] = None,
        due_before: Optional[datetime] = None,
        completion_after: Optional[datetime] = None,
        completion_before: Optional[datetime] = None,
        tags: Optional[list[str]] = None,
        limit: Optional[int] = None,
    ) -> Iterator[Reminder]:
        """Stream reminders that match the supplied filters."""
        sql, params = _build_reminders_query(
            calendar_id,
            completed,
            due_after,
            due_before,
            tags=tags,
            calendar_ids=calendar_ids,
            completion_after=completion_after,
            completion_before=completion_before,
        )
        if limit and limit > 0:
            sql += " LIMIT ?"
            params.append(int(limit))
        for row in self._conn.execute(sql, params):
            yield _reminder_from_row(row, str(row["list_ckid"] or ""))

    def get_reminder_by_id(self, reminder_id: str) -> Optional[Reminder]:
        """Look up a reminder by its `ZCKIDENTIFIER` UUID.

        Populates `section_name` via the parent list's membership blob.
        """
        row = self._conn.execute(
            f"SELECT {_REMINDER_COLS} FROM ZREMCDREMINDER r "
            "LEFT JOIN ZREMCDBASELIST l ON r.ZLIST = l.Z_PK "
            "WHERE lower(r.ZCKIDENTIFIER) = lower(?) AND r.ZMARKEDFORDELETION = 0 "
            "ORDER BY r.Z_PK DESC LIMIT 1",
            (reminder_id,),
        ).fetchone()
        if not row:
            return None
        base = _reminder_from_row(row, str(row["list_ckid"] or ""))
        section_name = self.get_section_name(reminder_id)
        return base.model_copy(update={"section_name": section_name}) if section_name else base

    def list_sections_in_calendar(self, calendar_uuid: str) -> list[tuple[str, str]]:
        """Return `[(section_id, section_name), …]` for the given list."""
        rows = self._conn.execute(
            "SELECT s.ZCKIDENTIFIER AS sid, s.ZDISPLAYNAME AS sname "
            "FROM ZREMCDBASESECTION s "
            "JOIN ZREMCDBASELIST l ON s.ZLIST = l.Z_PK "
            "WHERE lower(l.ZCKIDENTIFIER) = lower(?) AND s.ZMARKEDFORDELETION = 0 "
            "AND s.ZDISPLAYNAME IS NOT NULL "
            "ORDER BY s.Z_PK",
            (calendar_uuid,),
        ).fetchall()
        return [(str(r["sid"]), str(r["sname"])) for r in rows]

    def get_section_name(self, reminder_uuid: str) -> Optional[str]:
        """Resolve a reminder's section_name via the parent list's membership blob.

        Section memberships live in `ZREMCDBASELIST.ZMEMBERSHIPSOFREMINDERSINSECTIONSASDATA`
        as a JSON document keyed by reminder UUID. Returns None if the
        reminder is unsectioned or the blob is empty.
        """
        import json

        row = self._conn.execute(
            "SELECT l.Z_PK, l.ZMEMBERSHIPSOFREMINDERSINSECTIONSASDATA AS blob "
            "FROM ZREMCDREMINDER r JOIN ZREMCDBASELIST l ON r.ZLIST = l.Z_PK "
            "WHERE lower(r.ZCKIDENTIFIER) = lower(?) AND r.ZMARKEDFORDELETION = 0 "
            "LIMIT 1",
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
        section_row = self._conn.execute(
            "SELECT ZDISPLAYNAME FROM ZREMCDBASESECTION "
            "WHERE lower(ZCKIDENTIFIER) = lower(?) AND ZMARKEDFORDELETION = 0 LIMIT 1",
            (group_id,),
        ).fetchone()
        return str(section_row["ZDISPLAYNAME"]) if section_row else None

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
