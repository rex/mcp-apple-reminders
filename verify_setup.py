#!/usr/bin/env python3
"""
MCP Apple Reminders - Installation Verification Script

This script verifies that the MCP server is properly installed and configured.
Run this after installation to check that everything is working correctly.
"""

import sys
import os
from pathlib import Path


def print_status(check_name: str, passed: bool, message: str = ""):
    """Print a formatted status message."""
    symbol = "✓" if passed else "✗"
    status = "PASS" if passed else "FAIL"
    color = "\033[92m" if passed else "\033[91m"
    reset = "\033[0m"

    print(f"{color}{symbol} {check_name}: {status}{reset}")
    if message:
        print(f"  {message}")


def main():
    """Run verification checks."""
    print("🔍 MCP Apple Reminders - Installation Verification")
    print("=" * 60)
    print()

    all_passed = True

    # Check 1: Python version
    print("📋 Checking Python version...")
    py_version = sys.version_info
    py_ok = py_version >= (3, 10)
    print_status(
        "Python Version",
        py_ok,
        f"Found Python {py_version.major}.{py_version.minor}.{py_version.micro}"
        + ("" if py_ok else " (3.10+ required)")
    )
    all_passed = all_passed and py_ok
    print()

    # Check 2: Operating system
    print("💻 Checking operating system...")
    is_macos = sys.platform == "darwin"
    print_status(
        "Operating System",
        is_macos,
        f"Found {sys.platform}" + ("" if is_macos else " (macOS required)")
    )
    all_passed = all_passed and is_macos
    print()

    # Check 3: Required packages
    print("📦 Checking required packages...")

    packages = {
        "mcp": "MCP SDK",
        "objc": "PyObjC Core",
        "EventKit": "PyObjC EventKit Framework",
    }

    for package, description in packages.items():
        try:
            if package == "EventKit":
                __import__("EventKit")
            else:
                __import__(package)
            print_status(description, True, f"Module '{package}' found")
        except ImportError:
            print_status(description, False, f"Module '{package}' not found")
            all_passed = False
    print()

    # Check 4: MCP Apple Reminders package
    print("🍎 Checking MCP Apple Reminders package...")
    try:
        sys.path.insert(0, str(Path(__file__).parent / "src"))
        import mcp_apple_reminders
        print_status(
            "MCP Apple Reminders",
            True,
            f"Version {mcp_apple_reminders.__version__}"
        )
    except ImportError as e:
        print_status("MCP Apple Reminders", False, f"Import error: {e}")
        all_passed = False
    print()

    # Check 5: pyremindkit library
    print("📚 Checking pyremindkit library...")
    try:
        sys.path.insert(0, str(Path(__file__).parent / "libs" / "pyremindkit" / "src"))
        from pyremindkit import RemindKit, Priority, Reminder
        print_status("pyremindkit", True, "Library found and importable")
    except ImportError as e:
        print_status("pyremindkit", False, f"Import error: {e}")
        all_passed = False
    print()

    # Check 6: Configuration file
    print("⚙️  Checking Claude Desktop configuration...")
    config_path = Path.home() / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"
    config_exists = config_path.exists()
    print_status(
        "Configuration File",
        config_exists,
        f"{'Found' if config_exists else 'Not found'} at {config_path}"
    )
    if not config_exists:
        print("  ℹ️  You need to create this file to use the MCP server with Claude Desktop")
        print(f"  ℹ️  See QUICKSTART.md for configuration instructions")
    print()

    # Summary
    print("=" * 60)
    if all_passed and config_exists:
        print("✅ All checks passed! Your installation is complete.")
        print()
        print("🚀 Next steps:")
        print("   1. Make sure Claude Desktop is configured (see QUICKSTART.md)")
        print("   2. Restart Claude Desktop")
        print("   3. Grant Reminders permissions when prompted")
        print("   4. Start using MCP Apple Reminders with Claude!")
    elif all_passed:
        print("⚠️  Installation complete but configuration needed.")
        print()
        print("📝 Next steps:")
        print("   1. Configure Claude Desktop (see QUICKSTART.md)")
        print("   2. Restart Claude Desktop")
        print("   3. Start using the MCP server!")
    else:
        print("❌ Some checks failed. Please review the errors above.")
        print()
        print("💡 Common fixes:")
        print("   - Run ./install.sh to install dependencies")
        print("   - Ensure you're on macOS 10.15 or later")
        print("   - Make sure Python 3.10+ is installed")
        print()
        print("📖 See README.md for detailed installation instructions")

    print()
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
