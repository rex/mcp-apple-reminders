"""Test result accumulator and small helpers.

Shared by every test script at the repo root. The `TestResults` class tracks
pass/fail/skip counts and prints a final summary; `get_current_cst_iso8601`
produces a CST-timezoned ISO8601 string used as a unique suffix in test
reminder titles.
"""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo


class TestResults:
    """Track pass/fail/skip outcomes across a test run and print a summary."""

    def __init__(self):
        self.passed = []
        self.failed = []
        self.skipped = []

    def add_pass(self, test_name, message=""):
        self.passed.append((test_name, message))
        print(f"  ✅ {test_name}" + (f": {message}" if message else ""))

    def add_fail(self, test_name, error):
        self.failed.append((test_name, str(error)))
        print(f"  ❌ {test_name}: {error}")

    def add_skip(self, test_name, reason):
        self.skipped.append((test_name, reason))
        print(f"  ⏭️  {test_name}: {reason}")

    def summary(self) -> bool:
        """Print the final summary and return True iff no tests failed."""
        total = len(self.passed) + len(self.failed) + len(self.skipped)
        print("\n" + "=" * 70)
        print("TEST SUMMARY")
        print("=" * 70)
        print(f"Total Tests:  {total}")
        print(f"✅ Passed:    {len(self.passed)}")
        print(f"❌ Failed:    {len(self.failed)}")
        print(f"⏭️  Skipped:   {len(self.skipped)}")

        if self.failed:
            print("\n" + "=" * 70)
            print("FAILED TESTS:")
            print("=" * 70)
            for name, error in self.failed:
                print(f"❌ {name}")
                print(f"   Error: {error}")

        print("=" * 70)
        return len(self.failed) == 0


def get_current_cst_iso8601() -> str:
    """Return the current time as a CST-zoned ISO8601 string (suffix for unique titles)."""
    cst = ZoneInfo("America/Chicago")
    now = datetime.now(cst)
    return now.strftime("%Y-%m-%dT%H:%M:%S%z")
