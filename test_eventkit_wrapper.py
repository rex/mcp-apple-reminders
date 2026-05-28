"""Tests for `mcp_apple_reminders._native.eventkit` — Slice 1.2.

Exercises the Python ↔ Swift JSON-over-stdio protocol:
- Helper-binary not-present → EventKitHelperUnavailable.
- Successful create round-trip → Calendar with populated deeplink.
- Helper structured error → EventKitHelperError.
- Optional live integration test that creates + cleans up a real list
  on the user's Reminders DB. Guarded by REM_LIVE_HELPER=1 so CI / fresh
  agents do not pollute Reminders.app.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

from mcp_apple_reminders._native.eventkit import (
    DEFAULT_HELPER_PATH,
    EventKitHelperError,
    EventKitHelperUnavailable,
    create_calendar,
)
from mcp_apple_reminders.models import Calendar

# ---------------------------------------------------------------------------
# Helper availability guard
# ---------------------------------------------------------------------------


def test_missing_helper_raises_unavailable(tmp_path):
    """A nonexistent helper path raises EventKitHelperUnavailable."""
    bogus = tmp_path / "rem_eventkit"  # does not exist
    with pytest.raises(EventKitHelperUnavailable):
        create_calendar("doesn't matter", helper_path=bogus)


def test_blank_title_raises_value_error():
    """The Python wrapper guards against blank titles before invoking the helper."""
    with pytest.raises(ValueError, match="non-empty"):
        create_calendar("")
    with pytest.raises(ValueError, match="non-empty"):
        create_calendar("   ")


# ---------------------------------------------------------------------------
# Mocked-subprocess integration
# ---------------------------------------------------------------------------


def _make_fake_helper(tmp_path: Path, *, stdout: str, exit_code: int = 0) -> Path:
    """Drop a tiny shell helper that echoes a canned response and exits."""
    helper = tmp_path / "fake_rem_eventkit"
    # Quote-escape the JSON for shell. Single-quoting is safest.
    helper.write_text(
        "#!/bin/sh\n"
        # We don't read stdin in the fake; that's fine since `_invoke` only
        # cares about exit code + stdout body.
        f"cat <<'EOF'\n{stdout}\nEOF\n"
        f"exit {exit_code}\n"
    )
    helper.chmod(0o755)
    return helper


def test_success_response_returns_calendar_with_deeplink(tmp_path):
    """A successful helper response builds a Pydantic Calendar with the canonical deeplink."""
    helper = _make_fake_helper(
        tmp_path,
        stdout=json.dumps({"status": "created", "id": "TEST-UUID-1234", "title": "Demo"}),
    )
    cal = create_calendar("Demo", helper_path=helper)
    assert isinstance(cal, Calendar)
    assert cal.id == "TEST-UUID-1234"
    assert cal.name == "Demo"
    assert cal.deeplink == "x-apple-reminderkit://REMCDList/TEST-UUID-1234"
    assert cal.is_default is False


def test_error_response_raises_helper_error_with_message(tmp_path):
    """An exit-code-1 + JSON-error body surfaces as EventKitHelperError."""
    helper = _make_fake_helper(
        tmp_path,
        stdout=json.dumps({"status": "error", "message": "Calendar source missing"}),
        exit_code=1,
    )
    with pytest.raises(EventKitHelperError) as exc:
        create_calendar("Whatever", helper_path=helper)
    assert "Calendar source missing" in str(exc.value)


def test_non_json_stdout_raises_helper_error(tmp_path):
    """A success exit code with non-JSON output surfaces as EventKitHelperError."""
    helper = _make_fake_helper(tmp_path, stdout="not json at all")
    with pytest.raises(EventKitHelperError):
        create_calendar("Hi", helper_path=helper)


def test_color_argument_is_passed_to_helper(tmp_path):
    """The wrapper includes the color key in the JSON payload sent to the helper."""
    # The fake helper writes its actual stdin to a side-channel file
    # so the test can assert what was sent.
    stdin_dump = tmp_path / "captured-stdin.json"
    helper = tmp_path / "capturing_rem_eventkit"
    helper.write_text(
        "#!/bin/sh\n"
        f"cat > {stdin_dump.as_posix()}\n"
        "cat <<'EOF'\n"
        '{"status":"created","id":"COLORED","title":"Colored"}\n'
        "EOF\n"
        "exit 0\n"
    )
    helper.chmod(0o755)

    cal = create_calendar("Colored", color="orange", helper_path=helper)
    assert cal.color == "orange"

    captured = json.loads(stdin_dump.read_text())
    assert captured["action"] == "create_list"
    assert captured["title"] == "Colored"
    assert captured["color"] == "orange"


# ---------------------------------------------------------------------------
# Optional live integration — creates + cleans up a real list
# ---------------------------------------------------------------------------


@pytest.mark.skipif(
    os.environ.get("REM_LIVE_HELPER") != "1" or not DEFAULT_HELPER_PATH.exists(),
    reason="Set REM_LIVE_HELPER=1 with a built helper to run the live round-trip.",
)
def test_live_create_and_cleanup_round_trip():
    """Live: create a list, verify deeplink format, then delete via the helper."""
    test_name = "REM-TEST-AUTODELETE-S12"

    cal = create_calendar(test_name, color="blue")
    assert cal.id
    assert cal.deeplink == f"x-apple-reminderkit://REMCDList/{cal.id}"
    assert cal.name == test_name

    # Clean up via the helper's `delete_list` action.
    delete_payload = json.dumps({"action": "delete_list", "title": test_name})
    proc = subprocess.run(
        [str(DEFAULT_HELPER_PATH)],
        input=delete_payload,
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )
    assert proc.returncode == 0, (
        f"delete_list cleanup failed; you may need to delete {test_name!r} manually. "
        f"stderr={proc.stderr!r} stdout={proc.stdout!r}"
    )
