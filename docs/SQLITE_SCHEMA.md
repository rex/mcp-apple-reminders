# Reminders.app SQLite schema notes

The `src/mcp_apple_reminders/_native/sqlite.py` reader points at this
document for the schema details. Kept here so the Python file stays
under the architecture line-limit gate.

## Store location

`~/Library/Group Containers/group.com.apple.reminders/Container_v1/Stores/Data-*.sqlite`.

The largest `Data-*.sqlite` is the active one. Apple Reminders writes
to multiple stores when multiple iCloud accounts are signed in. The
reader picks the largest file by default.

## Tables we touch

CoreData-flavored — every table starts with `Z`.

### `ZREMCDBASELIST` — reminder lists (a.k.a. calendars)

Columns we read:

- `Z_PK` — integer primary key.
- `ZNAME` — list name.
- `ZCKIDENTIFIER` — UUID that matches `EKCalendar.calendarIdentifier()`.
- `ZCOLOR` — color blob (raw CGColor encoding).
- `ZMARKEDFORDELETION` — soft-delete flag.
- `Z_ENT = 3` filters out smart lists; we always include this in WHERE.

### `ZREMCDREMINDER` — reminders (top-level + subtasks)

Columns we read:

- `Z_PK` — integer primary key.
- `ZTITLE`, `ZNOTES`, `ZICSURL` — text fields.
- `ZCOMPLETED`, `ZFLAGGED` — booleans (0/1).
- `ZPRIORITY` — raw integer 0–9 (1=high, 5=medium, 9=low in this DB —
  inverted vs. EventKit's named-bucket convention; we expose the raw int).
- `ZDUEDATE`, `ZCOMPLETIONDATE`, `ZCREATIONDATE`, `ZLASTMODIFIEDDATE` —
  Apple-epoch timestamps (see below).
- `ZPARENTREMINDER` — `Z_PK` of the parent reminder for subtasks; NULL
  for top-level.
- `ZLIST` — `Z_PK` of the containing list.
- `ZCKIDENTIFIER` — UUID matching `EKReminder.calendarItemIdentifier()`.
- `ZMARKEDFORDELETION` — soft-delete flag.
- `ZACCOUNT` — account FK; NULL on orphaned rows (we filter them out).

### `ZREMCDBASESECTION` — sections within a list

Used by `assign_section` (slice 1.8).

### `ZREMCDHASHTAGLABEL` + `ZREMCDOBJECT` — tags

Tags are stored as labels in `ZREMCDHASHTAGLABEL.ZNAME`, joined to
reminders through `ZREMCDOBJECT` rows where `ZREMINDER3 = reminder.Z_PK`
and `ZHASHTAGLABEL = label.Z_PK`. The reader's correlated subquery
hydrates each row's tag set via `GROUP_CONCAT`.

## Timestamps

CoreData stores dates as **seconds since 2001-01-01 00:00:00 UTC**.
Convert by adding `APPLE_EPOCH_OFFSET` (`978307200`) and calling
`datetime.fromtimestamp()`.

## Permissions

Reading the DB requires either Full Disk Access on the interpreter
binary OR an interpreter that already has Reminders TCC consent. The
conda Python in `./venv/bin/python3` works because it's been granted
Reminders consent (the same consent EventKit uses).

## Contract: deeplink UUID equivalence (verified at S1.0)

`EKReminder.calendarItemIdentifier()` and SQLite `ZCKIDENTIFIER` produce
the same UUID for the same reminder. Same for calendars. Verified live
against this machine's store on 2026-05-28. The deeplink helpers in
`mcp_apple_reminders.models` work identically from either path:

- `x-apple-reminderkit://REMCDReminder/{uuid}`
- `x-apple-reminderkit://REMCDList/{uuid}`

## Concurrency

`connect()` opens with `?mode=ro` (read-only) **without** `immutable=1`.
The `immutable=1` flag tells SQLite to aggressively cache the file
contents and ignore concurrent writes — which would prevent the reader
from seeing the helper subprocess's just-committed changes. Dropping
the flag (S1.5) is what made the live subtask/tag round-trips green.
