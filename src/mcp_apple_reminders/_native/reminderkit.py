"""Python wrapper around the Objective-C ReminderKit (private framework) helper.

ReminderKit is the **private** macOS framework that backs Reminders.app's
sections, subtasks, tags, flagged-by-API, list pinning, smart-list filters,
and a few other capabilities that EventKit does not expose. Slice 1.4 ships
the protocol skin; Slices 1.5–1.8 build the per-action surface on top
(`subtasks`, `set_flagged`, `set_tags`, `assign_section`).

### Protocol

Identical shape to `_native/eventkit.py`:

  Request:  {"action": "set_flagged", "id": "<uuid>", "flagged": true}
  Response: {"status": "ok", ...}
  Errors:   {"status": "error", "message": "..."} with exit code 1.

Per-call subprocess mode (per Slice 0.6 decision). ~50–200 ms per call.
Long-lived mode is a swap-in upgrade if profiling shows it matters.

### Availability flag

`REMINDERKIT_HELPER_AVAILABLE` is computed at import time. Callers that
want a fast "is the feature live?" check can read the constant without
spawning a subprocess. `is_available(refresh=True)` re-probes if the
helper was just built.

### WARNING — private API

`rem_reminderkit` links against `/System/Library/PrivateFrameworks/
ReminderKit.framework`. Apple may rename or remove symbols across macOS
releases. Pierce explicitly accepted the risk in spec 002. If a future
release breaks the helper:
- EventKit-backed read/write tools keep working.
- The SQLite reader keeps working.
- The ReminderKit-backed tools (subtasks, set_flagged, set_tags,
  assign_section) raise `ReminderKitHelperUnavailable`.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any, Optional

# Default binary location: <package>/_native/bin/rem_reminderkit.
_BIN_DIR = Path(__file__).resolve().parent / "bin"
DEFAULT_HELPER_PATH = _BIN_DIR / "rem_reminderkit"


class ReminderKitHelperUnavailable(RuntimeError):  # noqa: N818 — matches slice-acceptance naming.
    """Raised when the ReminderKit helper isn't present or won't start.

    Most common cause: `make build-native` has not been run on this checkout,
    OR the helper was built but the ReminderKit private framework's symbols
    changed in a recent macOS release.
    """


class ReminderKitHelperError(RuntimeError):  # noqa: N818 — matches the spec-named pair above.
    """Raised when the helper returned a structured error response.

    `.message` carries the helper's own error message. Caller picks the
    right way to surface it (typically `ValueError` for the user-facing
    tool).
    """

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


def _resolve_helper_path(override: Optional[Path] = None) -> Path:
    """Return the path to the ReminderKit helper, raising if missing."""
    path = Path(override) if override else DEFAULT_HELPER_PATH
    if not path.exists():
        raise ReminderKitHelperUnavailable(f"Helper binary not found: {path}. Run `make build-native` to compile it.")
    if not path.is_file():
        raise ReminderKitHelperUnavailable(f"Helper path is not a regular file: {path}")
    return path


def _probe_available(helper_path: Optional[Path] = None) -> bool:
    """Spawn the helper with `--ping` to confirm it loads and ReminderKit resolves."""
    try:
        path = _resolve_helper_path(helper_path)
    except ReminderKitHelperUnavailable:
        return False
    try:
        proc = subprocess.run(
            [str(path), "--ping"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return False
    if proc.returncode != 0:
        return False
    return '"status":"ok"' in (proc.stdout or "")


# Module-level availability flag — computed once at import time. Refresh by
# calling `is_available(refresh=True)` after a fresh `make build-native`.
REMINDERKIT_HELPER_AVAILABLE: bool = _probe_available()


def is_available(refresh: bool = False) -> bool:
    """Return whether the helper binary loads + ReminderKit symbols resolve.

    Args:
        refresh: When True, re-probe the binary; otherwise return the cached
            value computed at import time. Pass True after a fresh
            `make build-native` to refresh.
    """
    global REMINDERKIT_HELPER_AVAILABLE
    if refresh:
        REMINDERKIT_HELPER_AVAILABLE = _probe_available()
    return REMINDERKIT_HELPER_AVAILABLE


def _invoke(
    payload: dict,
    *,
    helper_path: Optional[Path] = None,
    timeout_s: float = 30.0,
) -> dict:
    """Run the ReminderKit helper with `payload` piped on stdin; return JSON.

    Raises `ReminderKitHelperUnavailable` if the binary is missing or fails to
    spawn. Raises `ReminderKitHelperError` if the helper returned an error
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
        raise ReminderKitHelperUnavailable(f"Could not exec {path}: {e}") from e
    except subprocess.TimeoutExpired as e:
        raise ReminderKitHelperError(f"Helper timed out after {timeout_s}s") from e

    stdout = (proc.stdout or "").strip()
    stderr = (proc.stderr or "").strip()

    if proc.returncode != 0:
        try:
            error_body = json.loads(stdout) if stdout else {}
        except json.JSONDecodeError:
            error_body = {}
        message = error_body.get("message") or stderr or stdout or "Unknown helper error"
        raise ReminderKitHelperError(message)

    if not stdout:
        raise ReminderKitHelperError("Helper returned an empty stdout body.")

    try:
        return json.loads(stdout)
    except json.JSONDecodeError as e:
        raise ReminderKitHelperError(f"Helper returned non-JSON output: {stdout!r} ({e})") from e


# ---------------------------------------------------------------------------
# Public smoke probe (per-action surface lives in S1.5–S1.8)
# ---------------------------------------------------------------------------


def ping(*, helper_path: Optional[Path] = None) -> dict:
    """Probe the helper via `--ping` and return the parsed JSON response.

    Returns the helper's `{"status":"ok","helper":"rem_reminderkit"}` payload
    on success. Raises `ReminderKitHelperUnavailable` if the binary isn't
    built and `ReminderKitHelperError` if it loads but `--ping` fails.
    """
    path = _resolve_helper_path(helper_path)
    try:
        proc = subprocess.run(
            [str(path), "--ping"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (FileNotFoundError, OSError) as e:
        raise ReminderKitHelperUnavailable(f"Could not exec {path}: {e}") from e
    except subprocess.TimeoutExpired as e:
        raise ReminderKitHelperError(f"Helper --ping timed out: {e}") from e
    if proc.returncode != 0:
        raise ReminderKitHelperError(
            f"Helper --ping returned exit {proc.returncode}: " f"stderr={proc.stderr!r} stdout={proc.stdout!r}"
        )
    try:
        return json.loads((proc.stdout or "").strip())
    except json.JSONDecodeError as e:
        raise ReminderKitHelperError(f"Helper --ping returned non-JSON: {proc.stdout!r} ({e})") from e


def invoke_action(action: str, **kwargs: Any) -> dict:
    """Shared entry point for per-action helpers in S1.5+.

    Subsequent slices add typed wrappers (e.g. `set_flagged`, `add_tags`)
    that call this with a fixed action name. Returning the raw dict keeps
    the protocol-level error path centralized here.

    Raises:
        ReminderKitHelperUnavailable: helper missing.
        ReminderKitHelperError: structured error from the helper.
    """
    payload: dict[str, Any] = {"action": action}
    payload.update(kwargs)
    return _invoke(payload)


def set_flagged(reminder_id: str, flagged: bool) -> dict:
    """Set the flagged flag on a reminder via the Obj-C `set_flagged` action.

    Args:
        reminder_id: The reminder's UUID.
        flagged: True to flag, False to clear.

    Raises:
        ValueError: `reminder_id` is blank.
        ReminderKitHelperUnavailable: helper missing.
        ReminderKitHelperError: helper returned a structured error.
    """
    if not reminder_id or not reminder_id.strip():
        raise ValueError("reminder_id is required and must be non-empty")
    return _invoke({"action": "set_flagged", "id": reminder_id, "flagged": bool(flagged)})


def create_subtask(parent_id: str, title: str, **extras: Any) -> dict:
    """Create one new subtask under the given parent via `add_subtasks`.

    The subtask inherits the parent's list automatically — there's no separate
    list_id to pass. Additional kwargs flow through to the helper's
    per-subtask spec dict (e.g. `priority`).

    Args:
        parent_id: The parent reminder's UUID (matches
            `EKReminder.calendarItemIdentifier()` and SQLite `ZCKIDENTIFIER`).
        title: The subtask title.
        **extras: Per-subtask metadata flowed into the spec dict.

    Returns:
        The helper's response dict, which carries the new subtask's id and url
        under `subtasks[0]` of the response payload.

    Raises:
        ReminderKitHelperUnavailable: helper missing.
        ReminderKitHelperError: helper returned a structured error.
        ValueError: title or parent_id blank.
    """
    if not parent_id or not parent_id.strip():
        raise ValueError("parent_id is required and must be non-empty")
    if not title or not title.strip():
        raise ValueError("title is required and must be non-empty")
    spec: dict[str, Any] = {"title": title, **extras}
    return _invoke({"action": "add_subtasks", "id": parent_id, "subtasks": [spec]})


__all__ = [
    "DEFAULT_HELPER_PATH",
    "REMINDERKIT_HELPER_AVAILABLE",
    "ReminderKitHelperError",
    "ReminderKitHelperUnavailable",
    "create_subtask",
    "invoke_action",
    "is_available",
    "ping",
    "set_flagged",
]
