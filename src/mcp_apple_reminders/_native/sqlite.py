"""Direct read-only access to the Reminders.app CoreData SQLite store.

See `docs/SQLITE_SCHEMA.md` for schema notes. Public surface: `Reader`,
`RemindersDBUnavailable`, `connect`, `find_db_path`, `APPLE_EPOCH_OFFSET`.
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
    _resolve_section_name,
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

    # Standard projection for ZREMCDBASELIST rows — includes ZISGROUP +
    # ZPARENTLIST so _calendar_from_row + the parent-group resolver have
    # what they need. Used by every public read method below.
    _LIST_COLS = "Z_PK, ZNAME, ZCKIDENTIFIER, ZCOLOR, ZISGROUP, ZPARENTLIST"

    def _resolve_parent_group_uuid(self, parent_z_pk: Optional[int]) -> Optional[str]:
        """Resolve a `ZPARENTLIST` foreign-key Z_PK to the group's UUID."""
        if not parent_z_pk:
            return None
        row = self._conn.execute(
            "SELECT ZCKIDENTIFIER FROM ZREMCDBASELIST WHERE Z_PK = ? LIMIT 1",
            (parent_z_pk,),
        ).fetchone()
        return str(row["ZCKIDENTIFIER"]) if row and row["ZCKIDENTIFIER"] else None

    def list_calendars(self, *, include_groups: bool = False) -> list[Calendar]:
        """Return every non-deleted user-visible reminder list.

        Args:
            include_groups: If False (default), filter out group rows
                (ZISGROUP=1). If True, return groups alongside regular
                lists. Post-S5.1 default — groups have their own
                discovery surface via `list_groups()`.
        """
        default_uuid = self._default_calendar_uuid()
        where = "ZMARKEDFORDELETION = 0 AND Z_ENT = 3 AND ZNAME IS NOT NULL AND ZNAME != ''"
        if not include_groups:
            where += " AND (ZISGROUP IS NULL OR ZISGROUP = 0)"
        rows = self._conn.execute(
            f"SELECT {self._LIST_COLS} FROM ZREMCDBASELIST WHERE {where} ORDER BY ZNAME"
        ).fetchall()
        return [
            _calendar_from_row(r, default_uuid, parent_group_id=self._resolve_parent_group_uuid(r["ZPARENTLIST"]))
            for r in rows
        ]

    def list_groups(self) -> list[Calendar]:
        """Return every Reminders.app group (Z_ENT=3 ∧ ZISGROUP=1).

        Groups have no reminders of their own; child lists point at them
        via `ZPARENTLIST`. The returned `Calendar` will have
        `is_group=True` and `parent_group_id=None`.
        """
        default_uuid = self._default_calendar_uuid()
        rows = self._conn.execute(
            f"SELECT {self._LIST_COLS} FROM ZREMCDBASELIST "
            "WHERE ZMARKEDFORDELETION = 0 AND Z_ENT = 3 AND ZISGROUP = 1 "
            "AND ZNAME IS NOT NULL AND ZNAME != '' ORDER BY ZNAME"
        ).fetchall()
        return [
            _calendar_from_row(r, default_uuid, parent_group_id=self._resolve_parent_group_uuid(r["ZPARENTLIST"]))
            for r in rows
        ]

    def iter_lists_in_group(self, group_uuid: str) -> Iterator[Calendar]:
        """Stream every list whose `ZPARENTLIST` points at the given group UUID."""
        default_uuid = self._default_calendar_uuid()
        group_row = self._conn.execute(
            "SELECT Z_PK FROM ZREMCDBASELIST "
            "WHERE lower(ZCKIDENTIFIER) = lower(?) AND ZISGROUP = 1 AND ZMARKEDFORDELETION = 0 LIMIT 1",
            (group_uuid,),
        ).fetchone()
        if not group_row:
            return
        group_pk = group_row["Z_PK"]
        rows = self._conn.execute(
            f"SELECT {self._LIST_COLS} FROM ZREMCDBASELIST "
            "WHERE ZPARENTLIST = ? AND ZMARKEDFORDELETION = 0 AND Z_ENT = 3 "
            "AND (ZISGROUP IS NULL OR ZISGROUP = 0) "
            "AND ZNAME IS NOT NULL AND ZNAME != '' ORDER BY ZNAME",
            (group_pk,),
        ).fetchall()
        for r in rows:
            yield _calendar_from_row(r, default_uuid, parent_group_id=group_uuid)

    def get_calendar_by_id(self, calendar_id: str) -> Optional[Calendar]:
        """Look up a calendar by its `ZCKIDENTIFIER` UUID. Includes groups."""
        default_uuid = self._default_calendar_uuid()
        row = self._conn.execute(
            f"SELECT {self._LIST_COLS} FROM ZREMCDBASELIST "
            "WHERE lower(ZCKIDENTIFIER) = lower(?) AND ZMARKEDFORDELETION = 0 AND Z_ENT = 3 LIMIT 1",
            (calendar_id,),
        ).fetchone()
        if not row:
            return None
        return _calendar_from_row(
            row, default_uuid, parent_group_id=self._resolve_parent_group_uuid(row["ZPARENTLIST"])
        )

    def get_calendar_by_name(self, name: str) -> Optional[Calendar]:
        """Look up a calendar by exact name. Includes groups."""
        default_uuid = self._default_calendar_uuid()
        row = self._conn.execute(
            f"SELECT {self._LIST_COLS} FROM ZREMCDBASELIST "
            "WHERE ZNAME = ? AND ZMARKEDFORDELETION = 0 AND Z_ENT = 3 LIMIT 1",
            (name,),
        ).fetchone()
        if not row:
            return None
        return _calendar_from_row(
            row, default_uuid, parent_group_id=self._resolve_parent_group_uuid(row["ZPARENTLIST"])
        )

    def search_calendars(self, query: str, *, include_groups: bool = False) -> list[Calendar]:
        """Case-insensitive substring search by calendar name.

        Args:
            query: Substring to match against ZNAME.
            include_groups: If False (default), exclude group rows. Matches
                the `list_calendars` default.
        """
        default_uuid = self._default_calendar_uuid()
        where = "ZMARKEDFORDELETION = 0 AND Z_ENT = 3 AND ZNAME IS NOT NULL AND lower(ZNAME) LIKE lower(?)"
        params: list = [f"%{query}%"]
        if not include_groups:
            where += " AND (ZISGROUP IS NULL OR ZISGROUP = 0)"
        rows = self._conn.execute(
            f"SELECT {self._LIST_COLS} FROM ZREMCDBASELIST WHERE {where} ORDER BY ZNAME",
            params,
        ).fetchall()
        return [
            _calendar_from_row(r, default_uuid, parent_group_id=self._resolve_parent_group_uuid(r["ZPARENTLIST"]))
            for r in rows
        ]

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
        """Resolve a reminder's section_name via the parent list's membership blob."""
        return _resolve_section_name(self._conn, reminder_uuid)

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
