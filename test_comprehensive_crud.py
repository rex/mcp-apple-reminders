#!/usr/bin/env python3
"""Comprehensive CRUD test suite orchestrator.

Top-level driver that sets up the pyremindkit import path, instantiates
`RemindKit`, runs each per-domain test module in sequence, and cleans up.
Per-domain tests live in `test_crud_*.py` modules; shared helpers in
`test_support/`.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure vendored pyremindkit is on sys.path before the first import.
_project_root = Path(__file__).parent
_pyremindkit_path = _project_root / "libs" / "pyremindkit" / "src"
sys.path.insert(0, str(_pyremindkit_path))

from test_crud_calendars import test_calendar_operations
from test_crud_queries import test_query_operations
from test_crud_reminders import test_reminder_crud_operations
from test_crud_variations import test_additional_reminder_operations
from test_support.cleanup import cleanup_test_reminders
from test_support.harness import TestResults, get_current_cst_iso8601


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
        from pyremindkit import RemindKit

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
