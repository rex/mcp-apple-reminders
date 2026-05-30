"""Slice 3.1 — set_alarm tests."""

from __future__ import annotations

import json
import os

import pytest

from mcp_apple_reminders._native.eventkit import (
    DEFAULT_HELPER_PATH,
    EventKitHelperError,
    set_alarm,
)


def test_set_alarm_requires_id():
    with pytest.raises(ValueError, match="reminder_id"):
        set_alarm("", "1h")


def test_set_alarm_requires_at_least_one_action():
    """Either alarm_spec or clear must be set."""
    with pytest.raises(ValueError, match="alarm_spec"):
        set_alarm("UUID", None)


def test_set_alarm_normalizes_bare_relative_spec(tmp_path):
    """Bare `1h` becomes `-1h` in the payload."""
    stdin_dump = tmp_path / "stdin.json"
    helper = tmp_path / "helper"
    helper.write_text(
        "#!/bin/sh\n"
        f"cat > {stdin_dump.as_posix()}\n"
        'cat <<\'EOF\'\n{"status":"updated","id":"X"}\nEOF\n'
        "exit 0\n"
    )
    helper.chmod(0o755)
    set_alarm("UUID-1", "1h", helper_path=helper)
    payload = json.loads(stdin_dump.read_text())
    assert payload["action"] == "update"
    assert payload["id"] == "UUID-1"
    assert payload["alarm"] == "-1h"
    assert "clearAlarms" not in payload


def test_set_alarm_preserves_already_signed_relative(tmp_path):
    """`-30m` passes through unchanged."""
    stdin_dump = tmp_path / "stdin.json"
    helper = tmp_path / "helper"
    helper.write_text(
        "#!/bin/sh\n"
        f"cat > {stdin_dump.as_posix()}\n"
        'cat <<\'EOF\'\n{"status":"updated","id":"X"}\nEOF\n'
        "exit 0\n"
    )
    helper.chmod(0o755)
    set_alarm("UUID-2", "-30m", helper_path=helper)
    payload = json.loads(stdin_dump.read_text())
    assert payload["alarm"] == "-30m"


def test_set_alarm_clear_only(tmp_path):
    """clear=True with no when sends just clearAlarms."""
    stdin_dump = tmp_path / "stdin.json"
    helper = tmp_path / "helper"
    helper.write_text(
        "#!/bin/sh\n"
        f"cat > {stdin_dump.as_posix()}\n"
        'cat <<\'EOF\'\n{"status":"updated","id":"X"}\nEOF\n'
        "exit 0\n"
    )
    helper.chmod(0o755)
    set_alarm("UUID-3", None, clear=True, helper_path=helper)
    payload = json.loads(stdin_dump.read_text())
    assert payload["clearAlarms"] is True
    assert "alarm" not in payload


def test_set_alarm_passes_absolute_iso_unchanged(tmp_path):
    """ISO date-time is forwarded as-is."""
    stdin_dump = tmp_path / "stdin.json"
    helper = tmp_path / "helper"
    helper.write_text(
        "#!/bin/sh\n"
        f"cat > {stdin_dump.as_posix()}\n"
        'cat <<\'EOF\'\n{"status":"updated","id":"X"}\nEOF\n'
        "exit 0\n"
    )
    helper.chmod(0o755)
    set_alarm("UUID-4", "2026-06-15T09:00:00", helper_path=helper)
    payload = json.loads(stdin_dump.read_text())
    assert payload["alarm"] == "2026-06-15T09:00:00"


@pytest.mark.skipif(
    os.environ.get("REM_LIVE_HELPER") != "1" or not DEFAULT_HELPER_PATH.exists(),
    reason="Set REM_LIVE_HELPER=1 with the helper built to run the live round-trip.",
)
def test_live_set_and_clear_alarm():
    from mcp_apple_reminders._native import RemindKit
    from mcp_apple_reminders._native.eventkit import create_calendar, delete_calendar

    rk = RemindKit()
    list_name = "REM-TEST-ALARM-S31"
    cal = create_calendar(list_name)
    try:
        r = rk.create_reminder(title="Alarm target", calendar_id=cal.id)
        result_set = set_alarm(r.id, "30m")
        assert result_set.status == "updated"
        result_clear = set_alarm(r.id, None, clear=True)
        assert result_clear.status == "updated"
    except EventKitHelperError as e:
        raise AssertionError(f"Live alarm round-trip failed: {e.message}") from e
    finally:
        delete_calendar(list_name)
