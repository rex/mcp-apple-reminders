#!/usr/bin/env python3
"""Comprehensive CRUD test suite orchestrator.

Top-level driver that instantiates `RemindKit`, runs each per-domain CRUD step
in sequence, and cleans up. Per-domain steps live in `crud_*.py` modules
(renamed from `test_crud_*.py` so pytest does not try to collect their
arg-taking helper functions as fixtures-based tests); shared helpers in
`_support/`.

This module is a SCRIPT, not a pytest module — run it with
`python tests/test_comprehensive_crud.py`. `__test__ = False` tells pytest to
skip collection so the orchestration helpers it imports are not mistaken for
tests.

(post S0.2 — no sys.path mutation; RemindKit lives at
`mcp_apple_reminders._native`.)
"""

from __future__ import annotations

import sys

from _support.cleanup import cleanup_test_reminders
from _support.harness import TestResults, get_current_cst_iso8601
from crud_calendars import test_calendar_operations
from crud_queries import test_query_operations
from crud_reminders import test_reminder_crud_operations
from crud_variations import test_additional_reminder_operations

# This file is a script orchestrator, not a pytest test module — skip collection.
__test__ = False


def main() -> int:
    """Run every per-domain CRUD test and clean up. Returns 0 on success."""
    print("\n" + "=" * 70)
    print("MCP APPLE REMINDERS - COMPREHENSIVE CRUD TEST SUITE")
    print("=" * 70)
    print(f"Test Start Time (CST): {get_current_cst_iso8601()}")
    print("=" * 70)

    results = TestResults()
    all_test_reminder_ids = []

    try:
        from mcp_apple_reminders._native import RemindKit

        print("\n📱 Initializing RemindKit...")
        rk = RemindKit()
        print("✅ RemindKit initialized successfully")

        calendars, default_cal = test_calendar_operations(rk, results)

        main_reminder_id = test_reminder_crud_operations(rk, calendars, default_cal, results)
        if main_reminder_id:
            all_test_reminder_ids.append(main_reminder_id)

        additional_ids = test_additional_reminder_operations(rk, results)
        all_test_reminder_ids.extend(additional_ids)

        test_query_operations(rk, results)

        if all_test_reminder_ids:
            print(f"\n📋 Created {len(all_test_reminder_ids)} test reminder(s)")
            cleanup_test_reminders(rk, all_test_reminder_ids, results)

    except PermissionError as e:
        print(f"\n❌ Permission Error: {e}")
        print("\n💡 To grant permissions:")
        print("   1. Go to System Settings → Privacy & Security → Reminders")
        print("   2. Enable access for Terminal or your Python interpreter")
        print("   3. Run this test again")
        return 1

    except Exception as e:
        print(f"\n❌ Fatal Error: {e}")
        import traceback

        traceback.print_exc()
        return 1

    success = results.summary()
    print(f"\nTest End Time (CST): {get_current_cst_iso8601()}")
    print("=" * 70)

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
