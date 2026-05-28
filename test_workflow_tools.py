#!/usr/bin/env python3
"""Workflow tools test suite orchestrator.

Top-level driver that instantiates `RemindKit`, runs each per-domain workflow
test module, and cleans up. Per-domain tests live in `test_workflow_*.py`;
shared helpers in `test_support/`.

(post S0.2 — no sys.path mutation; RemindKit lives at
`mcp_apple_reminders._native`.)
"""

from __future__ import annotations

import sys

from test_support.cleanup import cleanup_test_reminders
from test_support.harness import TestResults, get_current_cst_iso8601
from test_workflow_convenience import test_workflow_convenience_functions
from test_workflow_discovery import test_get_workflow_lists
from test_workflow_errors import test_error_handling
from test_workflow_moves import test_move_between_all_workflow_lists, test_move_reminder_functionality


def main() -> int:
    """Run every per-domain workflow test and clean up. Returns 0 on success."""
    print("\n" + "=" * 70)
    print("MCP APPLE REMINDERS - WORKFLOW TOOLS TEST SUITE")
    print("=" * 70)
    print(f"Test Start Time (CST): {get_current_cst_iso8601()}")
    print("=" * 70)

    results = TestResults()
    test_reminder_ids = []

    try:
        from mcp_apple_reminders._native import RemindKit

        print("\n📱 Initializing RemindKit...")
        rk = RemindKit()
        print("✅ RemindKit initialized successfully")

        workflow_lists = test_get_workflow_lists(rk, results)

        if not workflow_lists:
            print("\n⚠️  No workflow lists found!")
            print("To test workflow features, create lists in Apple Reminders:")
            print("  - Claude-Brain-Dump")
            print("  - Claude-On-Deck")
            print("  - Claude-Active")
            print("  - Claude-Done")
            print("  - Claude-Waiting")
        else:
            reminder_id = test_move_reminder_functionality(rk, workflow_lists, results)
            if reminder_id:
                test_reminder_ids.append(reminder_id)

            reminder_id = test_workflow_convenience_functions(rk, workflow_lists, results)
            if reminder_id:
                test_reminder_ids.append(reminder_id)

            reminder_id = test_move_between_all_workflow_lists(rk, workflow_lists, results)
            if reminder_id:
                test_reminder_ids.append(reminder_id)

        test_error_handling(rk, results)

        if test_reminder_ids:
            cleanup_test_reminders(rk, test_reminder_ids, results)

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
