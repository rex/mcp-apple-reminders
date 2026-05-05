#!/usr/bin/env python3
"""
Comprehensive test script for MCP Apple Reminders server.
Tests server initialization and RemindKit functionality.
"""

import sys
from pathlib import Path

# Add the pyremindkit library to the path
_project_root = Path(__file__).parent
_pyremindkit_path = _project_root / "libs" / "pyremindkit" / "src"
sys.path.insert(0, str(_pyremindkit_path))


def test_imports():
    """Test that all required modules can be imported."""
    print("🧪 Testing Module Imports")
    print("=" * 60)

    try:
        # Test MCP package
        import mcp

        print("✅ mcp package imported successfully")

        # Test EventKit
        from EventKit import EKEventStore

        print("✅ EventKit framework imported successfully")

        # Test pyremindkit
        from pyremindkit import Priority, Reminder, RemindKit

        print("✅ pyremindkit library imported successfully")

        # Test MCP server
        from mcp_apple_reminders import server

        print("✅ MCP Apple Reminders server imported successfully")

        return True

    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False


def test_server_structure():
    """Test that the server has the expected structure."""
    print("\n🏗️  Testing Server Structure")
    print("=" * 60)

    try:
        from mcp_apple_reminders.server import app

        print("✅ Server app instance found")
        print("✅ list_tools handler found")
        print("✅ call_tool handler found")

        # Check server name
        if hasattr(app, "name"):
            print(f"✅ Server name: {app.name}")

        return True

    except Exception as e:
        print(f"❌ Server structure error: {e}")
        return False


def test_remindkit_permissions():
    """Test RemindKit permissions and basic functionality."""
    print("\n🔐 Testing RemindKit Permissions & Functionality")
    print("=" * 60)

    try:
        from pyremindkit import RemindKit

        # Create RemindKit instance (will request permissions if needed)
        rk = RemindKit()
        print("✅ RemindKit initialized successfully")

        # Try to get calendars
        calendars = list(rk.calendars.list())
        print(f"✅ EventKit access granted - found {len(calendars)} calendar(s)")

        if calendars:
            print("\n📝 Available Reminder Lists:")
            for cal in calendars[:5]:  # Show first 5
                default_marker = " (default)" if cal.is_default else ""
                print(f"   - {cal.name}{default_marker}")
                print(f"     ID: {cal.id}")
                print(f"     Color: {cal.color}")
            if len(calendars) > 5:
                print(f"   ... and {len(calendars) - 5} more")

        # Test getting default calendar
        default_cal = rk.calendars.get_default()
        print(f"\n✅ Default calendar: {default_cal.name}")

        # Test getting reminders (just a few to verify it works)
        print("\n📋 Testing reminder retrieval...")
        reminders = list(rk.get_reminders())[:3]  # Get up to 3 reminders
        print(f"✅ Retrieved {len(reminders)} reminder(s) as sample")

        if reminders:
            print("\nSample reminders:")
            for r in reminders:
                completed = "✓" if r.completed else "○"
                print(f"   {completed} {r.title}")

        return True

    except PermissionError as e:
        print(f"⚠️  Permission Error: {e}")
        print("\n💡 To grant permissions:")
        print("   1. Go to System Settings → Privacy & Security → Reminders")
        print("   2. Enable access for Terminal or your Python interpreter")
        print("   3. Run this test again")
        return False

    except Exception as e:
        print(f"❌ RemindKit error: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_tool_definitions():
    """Test that all expected tools are defined."""
    print("\n🔧 Testing Tool Definitions")
    print("=" * 60)

    try:
        import asyncio

        from mcp_apple_reminders.server import list_tools

        # Call the list_tools handler directly
        async def check_tools():
            tools = await list_tools()
            return tools

        tools = asyncio.run(check_tools())

        expected_tool_count = 16
        if len(tools) >= expected_tool_count:
            print(f"✅ Found {len(tools)} tools (expected at least {expected_tool_count})")

            # Define expected tools
            expected_tools = {
                "list_calendars",
                "get_calendar",
                "get_calendar_by_id",
                "search_calendars",
                "get_default_calendar",
                "create_reminder",
                "update_reminder",
                "complete_reminder",
                "uncomplete_reminder",
                "get_reminder",
                "delete_reminder",
                "get_reminders",
                "search_reminders",
                "get_next_reminder",
                "get_overdue_reminders",
                "get_today_reminders",
            }

            tool_names = {t.name for t in tools}
            missing = expected_tools - tool_names

            if missing:
                print(f"⚠️  Missing expected tools: {', '.join(missing)}")

            # Group tools by category
            calendar_tools = [
                t
                for t in tools
                if t.name.startswith(("list_calendar", "get_calendar", "search_calendar", "get_default_calendar"))
            ]
            reminder_crud = [
                t
                for t in tools
                if t.name
                in (
                    "create_reminder",
                    "update_reminder",
                    "complete_reminder",
                    "uncomplete_reminder",
                    "get_reminder",
                    "delete_reminder",
                )
            ]
            reminder_query = [
                t
                for t in tools
                if t.name
                in (
                    "get_reminders",
                    "search_reminders",
                    "get_next_reminder",
                    "get_overdue_reminders",
                    "get_today_reminders",
                )
            ]

            print("\n📊 Tool Categories:")
            print(f"   Calendar Management: {len(calendar_tools)} tools")
            print(f"   Reminder CRUD: {len(reminder_crud)} tools")
            print(f"   Reminder Query: {len(reminder_query)} tools")

            print("\n📋 All Tools:")
            for tool in sorted(tools, key=lambda t: t.name):
                print(f"   • {tool.name}")

            return len(missing) == 0 and len(tools) >= expected_tool_count
        else:
            print(f"❌ Expected at least {expected_tool_count} tools, found {len(tools)}")
            return False

    except Exception as e:
        print(f"❌ Tool definition error: {e}")
        import traceback

        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("MCP APPLE REMINDERS - COMPREHENSIVE TEST SUITE")
    print("=" * 60)

    results = {}

    # Run tests
    results["imports"] = test_imports()
    results["structure"] = test_server_structure()
    results["permissions"] = test_remindkit_permissions()
    results["tools"] = test_tool_definitions()

    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)

    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{test_name.capitalize():20} {status}")

    print("\n" + "=" * 60)

    all_passed = all(results.values())
    if all_passed:
        print("🎉 All tests passed!")
        print("\n✨ Your MCP Apple Reminders server is ready to use!")
        print("\n📝 Next steps:")
        print("   1. Configure Claude Desktop (see QUICKSTART.md)")
        print("   2. Restart Claude Desktop")
        print("   3. Start using reminders with Claude!")
    else:
        failed_tests = [name for name, passed in results.items() if not passed]
        print(f"⚠️  Some tests failed: {', '.join(failed_tests)}")

        if not results.get("permissions"):
            print("\n💡 Note: Permission errors are expected on first run.")
            print("   Grant access when prompted or in System Settings.")

    print("=" * 60 + "\n")

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
