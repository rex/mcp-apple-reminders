"""Smoke tests for `mcp_apple_reminders._native.reminderkit` — Slice 1.4.

Wrapper-level tests. The per-action tag/subtask/flag round-trips arrive in
Slices 1.5–1.8.

Tests:
- The wrapper detects a missing binary as `ReminderKitHelperUnavailable`.
- The cached `REMINDERKIT_HELPER_AVAILABLE` flag tracks the binary's presence.
- `is_available(refresh=True)` re-probes.
- `_invoke` round-trips a JSON payload (mocked binary).
- `_invoke` translates exit-code-1 with a structured error into
  `ReminderKitHelperError`.
- Live `--ping` against the real helper if it's been built.
"""

from __future__ import annotations

import json
import os

import pytest

from mcp_apple_reminders._native.reminderkit import (
    DEFAULT_HELPER_PATH,
    ReminderKitHelperError,
    ReminderKitHelperUnavailable,
    _invoke_action,
    is_available,
    ping,
)

# Expose the module-private dispatcher under its old test-only alias.
invoke_action = _invoke_action

# ---------------------------------------------------------------------------
# Availability detection
# ---------------------------------------------------------------------------


def test_missing_helper_path_returns_false_from_is_available(monkeypatch):
    """A bogus override returns False from is_available(refresh=True)."""
    # Point the wrapper at /nonexistent and refresh.
    monkeypatch.setattr(
        "mcp_apple_reminders._native.reminderkit.DEFAULT_HELPER_PATH",
        DEFAULT_HELPER_PATH.parent / "definitely-not-there",
    )
    assert is_available(refresh=True) is False


def test_ping_with_missing_helper_raises(tmp_path):
    """ping() raises ReminderKitHelperUnavailable when the binary is missing."""
    bogus = tmp_path / "rem_reminderkit"
    with pytest.raises(ReminderKitHelperUnavailable):
        ping(helper_path=bogus)


# ---------------------------------------------------------------------------
# Mocked-subprocess protocol
# ---------------------------------------------------------------------------


def _make_helper(tmp_path, *, stdout: str, exit_code: int = 0):
    helper = tmp_path / "rem_reminderkit"
    helper.write_text("#!/bin/sh\n" f"cat <<'EOF'\n{stdout}\nEOF\n" f"exit {exit_code}\n")
    helper.chmod(0o755)
    return helper


def test_invoke_action_success_returns_response_dict(tmp_path, monkeypatch):
    """A successful helper response is parsed and returned by invoke_action."""
    helper = _make_helper(
        tmp_path,
        stdout=json.dumps({"status": "ok", "id": "ABC", "flagged": True}),
    )
    monkeypatch.setattr(
        "mcp_apple_reminders._native.reminderkit.DEFAULT_HELPER_PATH",
        helper,
    )
    resp = invoke_action("set_flagged", id="ABC", flagged=True)
    assert resp == {"status": "ok", "id": "ABC", "flagged": True}


def test_invoke_action_error_response_raises_helper_error(tmp_path, monkeypatch):
    """An exit-code-1 + JSON-error body surfaces as ReminderKitHelperError."""
    helper = _make_helper(
        tmp_path,
        stdout=json.dumps({"status": "error", "message": "Unknown action"}),
        exit_code=1,
    )
    monkeypatch.setattr(
        "mcp_apple_reminders._native.reminderkit.DEFAULT_HELPER_PATH",
        helper,
    )
    with pytest.raises(ReminderKitHelperError, match="Unknown action"):
        invoke_action("set_flagged", id="ABC", flagged=True)


def test_invoke_action_payload_shape_via_stdin_capture(tmp_path, monkeypatch):
    """Captured stdin reflects the action + kwargs verbatim."""
    stdin_dump = tmp_path / "stdin.json"
    helper = tmp_path / "rem_reminderkit"
    helper.write_text(
        "#!/bin/sh\n" f"cat > {stdin_dump.as_posix()}\n" "cat <<'EOF'\n" '{"status":"ok"}\n' "EOF\n" "exit 0\n"
    )
    helper.chmod(0o755)
    monkeypatch.setattr(
        "mcp_apple_reminders._native.reminderkit.DEFAULT_HELPER_PATH",
        helper,
    )
    invoke_action("add_tags", id="UUID-1", tags=["work", "urgent"])
    payload = json.loads(stdin_dump.read_text())
    assert payload == {"action": "add_tags", "id": "UUID-1", "tags": ["work", "urgent"]}


# ---------------------------------------------------------------------------
# Live --ping against the real helper (skipped if not built)
# ---------------------------------------------------------------------------


@pytest.mark.skipif(
    not DEFAULT_HELPER_PATH.exists() or os.environ.get("REM_SKIP_LIVE_PING") == "1",
    reason="rem_reminderkit not built — run `make build-native` first.",
)
def test_live_ping_against_real_helper():
    """The real helper (built via `make build-native`) returns the ok ping."""
    response = ping()
    assert response == {"status": "ok", "helper": "rem_reminderkit"}
