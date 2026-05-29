"""Regression: EventKit write failures must propagate, not be swallowed.

PyObjC folds the trailing `NSError**` out-parameter of
`saveReminder:commit:error:` / `removeReminder:commit:error:` into the return
value, so the call returns a `(BOOL, NSError)` tuple. The pre-CL-1 code captured
that whole (always-truthy) tuple into a single `success` local, making the
failure branch dead and reporting success on genuinely failed writes. These
tests pin the corrected tuple-unpacking behavior.
"""

# ruff: noqa: N802 — fake classes deliberately mirror PyObjC selector names
#                     (saveReminder:commit:error:, removeReminder:commit:error:, …).
from __future__ import annotations

import pytest

from mcp_apple_reminders._native._internal import _save_ek_reminder


class _FakeNSError:
    def __init__(self, message: str):
        self._message = message

    def localizedDescription(self) -> str:
        return self._message


def test_save_ek_reminder_raises_on_eventkit_failure():
    """A (False, NSError) return must raise RuntimeError with the error detail."""

    class _FakeStore:
        def saveReminder_commit_error_(self, reminder, commit, error):
            return (False, _FakeNSError("No calendar has been set."))

    with pytest.raises(RuntimeError, match="No calendar has been set"):
        _save_ek_reminder(_FakeStore(), object())


def test_save_ek_reminder_returns_true_on_success():
    """A (True, None) return is success."""

    class _FakeStore:
        def saveReminder_commit_error_(self, reminder, commit, error):
            return (True, None)

    assert _save_ek_reminder(_FakeStore(), object()) is True


def test_delete_reminder_raises_on_eventkit_failure():
    """RemindKit.delete_reminder must raise when removeReminder returns (False, NSError)."""
    from mcp_apple_reminders._native.core import RemindKit

    class _FakeStore:
        def calendarItemWithIdentifier_(self, rid):
            return object()  # lookup succeeds

        def removeReminder_commit_error_(self, reminder, commit, error):
            return (False, _FakeNSError("Reminder is read-only."))

    rk = object.__new__(RemindKit)  # bypass __init__ (no EventKit / permission prompt)
    rk._event_store = _FakeStore()
    with pytest.raises(RuntimeError, match="read-only"):
        rk.delete_reminder("any-id")
