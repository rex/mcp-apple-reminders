"""Python wrapper around the Swift EventKit helper subprocess.

Spawns `_native/bin/rem_eventkit` per call (the S0.6 design decision — see
spec 002 plan.md and `THIRD_PARTY_NOTICES.md`), pipes a JSON command on
stdin, parses the JSON response on stdout. ~50–200 ms per call.

### Protocol

Request:  `{"action": "create_list", "title": "Work", "color": "blue"}`
Response: `{"status": "created", "id": "<uuid>", "title": "Work"}`
Errors:   `{"status": "error", "message": "..."}` with exit code 1.

Supported actions wired here so far (Slice 1.2):

- `create_list` — title + optional color (named palette token).

Slice 1.3 adds `rename_list` + `delete_list`. Slices 3.1–3.3 add the
remaining write actions (alarms, recurrence) via the same wrapper.

### Helper not built / not present

If `_native/bin/rem_eventkit` is missing the wrapper raises
`EventKitHelperUnavailable`. Tool handlers should catch this, log via
`ctx.error(...)`, and surface a clear "run `make build-native`" message.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any, Optional

from ..models import Calendar, calendar_deeplink

# Default binary location: <package>/_native/bin/rem_eventkit.
# Resolves regardless of where the package is installed.
_BIN_DIR = Path(__file__).resolve().parent / "bin"
DEFAULT_HELPER_PATH = _BIN_DIR / "rem_eventkit"


class EventKitHelperUnavailable(RuntimeError):  # noqa: N818 — matches slice-acceptance naming.
    """Raised when the Swift EventKit helper binary isn't present or won't start.

    Most common cause: `make build-native` has not been run on this checkout.
    """


class EventKitHelperError(RuntimeError):  # noqa: N818 — matches the spec-named pair above.
    """Raised when the helper returned a structured error response.

    `.message` carries the helper's own error message. Caller picks the
    right way to surface it (typically `ValueError` for the user-facing
    tool).
    """

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


def _resolve_helper_path(override: Optional[Path] = None) -> Path:
    """Return the path to the EventKit helper, raising if missing."""
    path = Path(override) if override else DEFAULT_HELPER_PATH
    if not path.exists():
        raise EventKitHelperUnavailable(f"Helper binary not found: {path}. Run `make build-native` to compile it.")
    if not path.is_file():
        raise EventKitHelperUnavailable(f"Helper path is not a regular file: {path}")
    return path


def _invoke(payload: dict, *, helper_path: Optional[Path] = None, timeout_s: float = 30.0) -> dict:
    """Run the Swift helper with `payload` piped on stdin; return parsed JSON.

    Raises `EventKitHelperUnavailable` if the binary is missing or fails to
    spawn. Raises `EventKitHelperError` if the helper returned an error
    response (exit code 1 with a JSON body).
    """
    path = _resolve_helper_path(helper_path)
    try:
        proc = subprocess.run(
            [str(path)],
            input=json.dumps(payload),
            capture_output=True,
            text=True,
            timeout=timeout_s,
            check=False,
        )
    except FileNotFoundError as e:
        raise EventKitHelperUnavailable(f"Could not exec {path}: {e}") from e
    except subprocess.TimeoutExpired as e:
        raise EventKitHelperError(f"Helper timed out after {timeout_s}s") from e

    stdout = (proc.stdout or "").strip()
    stderr = (proc.stderr or "").strip()

    if proc.returncode != 0:
        # Helper convention: error responses are JSON on stdout with status="error".
        try:
            error_body = json.loads(stdout) if stdout else {}
        except json.JSONDecodeError:
            error_body = {}
        message = error_body.get("message") or stderr or stdout or "Unknown helper error"
        raise EventKitHelperError(message)

    if not stdout:
        raise EventKitHelperError("Helper returned an empty stdout body.")

    try:
        return json.loads(stdout)
    except json.JSONDecodeError as e:
        raise EventKitHelperError(f"Helper returned non-JSON output: {stdout!r} ({e})") from e


# ---------------------------------------------------------------------------
# Public write actions (Slice 1.2 = create_list only; 1.3 will add the rest)
# ---------------------------------------------------------------------------


def create_calendar(
    title: str,
    color: Optional[str] = None,
    *,
    helper_path: Optional[Path] = None,
) -> Calendar:
    """Create a new reminder list via the Swift helper.

    Args:
        title: The list name. Required; non-empty.
        color: Optional named-palette token (e.g. "red", "blue", "orange").
            The helper's `colorForName(_:)` recognizes the standard
            Reminders palette plus a few extras. Unknown values are
            silently ignored by the helper (the list is created without
            a color).

    Returns:
        A Pydantic `Calendar` model populated from the helper's response.
        The returned `is_default` is always `False` (a freshly-created
        list is never the default; the user would have to switch it in
        Reminders.app).

    Raises:
        ValueError: `title` is empty or whitespace.
        EventKitHelperUnavailable: helper binary missing.
        EventKitHelperError: helper returned a structured error
            (e.g. no calDAV/local source available).
    """
    if not title or not title.strip():
        raise ValueError("title is required and must be non-empty")

    payload: dict[str, Any] = {"action": "create_list", "title": title}
    if color:
        payload["color"] = color

    response = _invoke(payload, helper_path=helper_path)

    # The helper currently emits `id` and `title`. Color comes back through a
    # later SQLite read once the calendar is in the store.
    cal_id = str(response.get("id") or "")
    if not cal_id:
        raise EventKitHelperError(f"Helper succeeded but returned no id: {response!r}")
    return Calendar(
        id=cal_id,
        name=str(response.get("title") or title),
        color=str(color or ""),
        is_default=False,
        owner=None,
        deeplink=calendar_deeplink(cal_id),
    )


def delete_calendar(
    title: str,
    *,
    helper_path: Optional[Path] = None,
) -> dict:
    """Delete a reminder list (and all its reminders) via the Swift helper.

    The underlying EventKit call (`removeCalendar(commit:)`) is atomic and
    cascading — removing the calendar removes its reminders in the same
    transaction. The tool layer is where the force-flag semantics and
    the default-calendar guard live; this wrapper just talks to the helper.

    Args:
        title: The list name to delete.

    Returns:
        The raw helper response dict (`{"status": "deleted", "title": ...}`).

    Raises:
        ValueError: `title` is blank.
        EventKitHelperUnavailable: helper binary missing.
        EventKitHelperError: helper returned a structured error
            (e.g. the named list does not exist).
    """
    if not title or not title.strip():
        raise ValueError("title is required and must be non-empty")
    return _invoke({"action": "delete_list", "title": title}, helper_path=helper_path)


def rename_calendar(
    title: str,
    new_title: str,
    *,
    helper_path: Optional[Path] = None,
) -> Calendar:
    """Rename a reminder list via the Swift helper.

    Args:
        title: The current list name.
        new_title: The desired new name.

    Returns:
        A Pydantic `Calendar` reflecting the renamed list.

    Raises:
        ValueError: titles are blank.
        EventKitHelperUnavailable: helper binary missing.
        EventKitHelperError: helper returned a structured error
            (e.g. the named list does not exist; new name conflicts).
    """
    if not title or not title.strip():
        raise ValueError("title is required and must be non-empty")
    if not new_title or not new_title.strip():
        raise ValueError("new_title is required and must be non-empty")
    response = _invoke(
        {"action": "rename_list", "title": title, "newTitle": new_title},
        helper_path=helper_path,
    )
    cal_id = str(response.get("id") or "")
    if not cal_id:
        raise EventKitHelperError(f"Helper succeeded but returned no id: {response!r}")
    return Calendar(
        id=cal_id,
        name=str(response.get("title") or new_title),
        color="",
        is_default=False,
        owner=None,
        deeplink=calendar_deeplink(cal_id),
    )


__all__ = [
    "DEFAULT_HELPER_PATH",
    "EventKitHelperError",
    "EventKitHelperUnavailable",
    "create_calendar",
    "delete_calendar",
    "rename_calendar",
]
