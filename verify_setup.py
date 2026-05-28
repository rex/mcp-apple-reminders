#!/usr/bin/env python3
"""
MCP Apple Reminders - Installation Verification Script

This script verifies that the MCP server is properly installed and configured.
Run this after installation to check that everything is working correctly.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent
RUNTIME_PYTHON = REPO_ROOT / "venv" / "bin" / "python3"
CLAUDE_CONFIG = Path.home() / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"
CODEX_CONFIG = Path.home() / ".codex" / "config.toml"


def print_status(check_name: str, passed: bool, message: str = ""):
    """Print a formatted status message."""
    symbol = "✓" if passed else "✗"
    status = "PASS" if passed else "FAIL"
    color = "\033[92m" if passed else "\033[91m"
    reset = "\033[0m"

    print(f"{color}{symbol} {check_name}: {status}{reset}")
    if message:
        print(f"  {message}")


def run_python(code: str) -> subprocess.CompletedProcess[str]:
    """Run a Python snippet in the configured MCP runtime."""
    return subprocess.run(
        [str(RUNTIME_PYTHON), "-c", code],
        capture_output=True,
        text=True,
        check=False,
    )


def config_contains(path: Path, needle: str) -> bool:
    """Check whether a config file contains a marker string."""
    if not path.exists():
        return False

    try:
        return needle in path.read_text()
    except OSError:
        return False


def main():
    """Run verification checks."""
    print("🔍 MCP Apple Reminders - Installation Verification")
    print("=" * 60)
    print()

    all_passed = True

    # Check 1: Host Python version (informational)
    print("📋 Checking current interpreter (informational)...")
    host_version = sys.version_info
    host_ok = host_version >= (3, 10)
    print_status(
        "Current Interpreter",
        host_ok,
        f"Found Python {host_version.major}.{host_version.minor}.{host_version.micro}"
        + ("" if host_ok else " (system python is older than the server requirement)"),
    )
    print()

    # Check 2: Operating system
    print("💻 Checking operating system...")
    is_macos = sys.platform == "darwin"
    print_status(
        "Operating System",
        is_macos,
        f"Found {sys.platform}" + ("" if is_macos else " (macOS required)"),
    )
    all_passed = all_passed and is_macos
    print()

    # Check 3: MCP runtime interpreter
    print("🐍 Checking MCP runtime...")
    runtime_exists = RUNTIME_PYTHON.exists()
    runtime_ok = False
    runtime_message = f"{RUNTIME_PYTHON} not found"
    if runtime_exists:
        version_result = run_python("import sys; print(sys.version)")
        runtime_ok = version_result.returncode == 0
        runtime_message = version_result.stdout.strip() if runtime_ok else version_result.stderr.strip()
    print_status("Runtime Python", runtime_exists and runtime_ok, runtime_message)
    all_passed = all_passed and runtime_exists and runtime_ok
    print()

    # Check 4: Required packages in the runtime
    print("📦 Checking runtime packages...")
    package_checks = {
        "mcp": "MCP SDK",
        "objc": "PyObjC Core",
        "EventKit": "PyObjC EventKit Framework",
        "pydantic": "Pydantic v2",
    }
    for package, description in package_checks.items():
        module = "EventKit" if package == "EventKit" else package
        result = run_python(f"import {module}")
        passed = result.returncode == 0
        print_status(description, passed, f"Module '{module}' {'found' if passed else 'not found'}")
        all_passed = all_passed and passed
    print()

    # Check 4b: MCP SDK version (must be >=1.27 for FastMCP + Context APIs)
    print("📐 Checking MCP SDK version (>=1.27 required for FastMCP)...")
    mcp_version_result = run_python(
        "from importlib.metadata import version; print(version('mcp'))"
    )
    mcp_version_ok = False
    mcp_version_message = mcp_version_result.stderr.strip()
    if mcp_version_result.returncode == 0:
        installed_version = mcp_version_result.stdout.strip()
        try:
            major, minor = installed_version.split(".")[:2]
            mcp_version_ok = (int(major), int(minor)) >= (1, 27)
            mcp_version_message = (
                f"mcp=={installed_version}"
                + ("" if mcp_version_ok else " (need >=1.27,<2)")
            )
        except ValueError:
            mcp_version_message = f"Unparseable version: {installed_version!r}"
    print_status("MCP SDK Version", mcp_version_ok, mcp_version_message)
    all_passed = all_passed and mcp_version_ok
    print()

    # Check 4c: PyObjC deprecation warnings on macOS 26.1
    print("🔇 Checking PyObjC for deprecation warnings...")
    warn_result = run_python(
        "import warnings; warnings.simplefilter('error', DeprecationWarning); "
        "import objc, EventKit; "
        "print('clean')"
    )
    warn_ok = warn_result.returncode == 0 and "clean" in warn_result.stdout
    warn_message = (
        "No DeprecationWarnings raised by importing objc + EventKit"
        if warn_ok
        else (warn_result.stderr.strip() or warn_result.stdout.strip() or "unknown failure")
    )
    print_status("PyObjC Deprecation-Free Import", warn_ok, warn_message)
    # Treat deprecation warnings as informational (not a hard fail) — log only.
    print()

    # Check 5: MCP Apple Reminders package
    print("🍎 Checking MCP Apple Reminders package...")
    package_result = run_python(
        "import mcp_apple_reminders; print(mcp_apple_reminders.__version__)"
    )
    package_ok = package_result.returncode == 0
    print_status(
        "MCP Apple Reminders",
        package_ok,
        f"Version {package_result.stdout.strip()}" if package_ok else package_result.stderr.strip(),
    )
    all_passed = all_passed and package_ok
    print()

    # Check 6: _native package (post-S0.2 home of the EventKit wrapper)
    print("📚 Checking mcp_apple_reminders._native package...")
    native_result = run_python(
        "from mcp_apple_reminders import _native; "
        "print(_native.__file__)"
    )
    native_ok = native_result.returncode == 0
    print_status(
        "_native",
        native_ok,
        native_result.stdout.strip() if native_ok else native_result.stderr.strip(),
    )
    all_passed = all_passed and native_ok
    print()

    # Check 7: Claude Desktop configuration
    print("⚙️  Checking Claude Desktop configuration...")
    claude_configured = config_contains(CLAUDE_CONFIG, "mcp_apple_reminders")
    print_status(
        "Claude Config",
        claude_configured,
        f"{'Found apple-reminders entry in' if claude_configured else 'No apple-reminders entry in'} {CLAUDE_CONFIG}",
    )
    print()

    # Check 8: Codex configuration
    print("🤖 Checking Codex configuration...")
    codex_configured = config_contains(CODEX_CONFIG, "[mcp_servers.mcp-apple-reminders]")
    print_status(
        "Codex Config",
        codex_configured,
        f"{'Found mcp-apple-reminders entry in' if codex_configured else 'No mcp-apple-reminders entry in'} {CODEX_CONFIG}",
    )
    print()

    # Summary
    print("=" * 60)
    if all_passed and (claude_configured or codex_configured):
        print("✅ Required runtime checks passed and at least one MCP client is configured.")
        print()
        print("🚀 Next steps:")
        print("   1. Restart your MCP client after config changes")
        print("   2. Grant Reminders permissions when prompted")
        print("   3. Run a harmless tool like list_calendars to confirm connectivity")
    elif all_passed:
        print("⚠️  Runtime checks passed, but no MCP client configuration was found.")
        print()
        print("📝 Next steps:")
        print("   1. Add the server to Claude Desktop or Codex")
        print("   2. Restart the client")
        print("   3. Re-run this verification script")
    else:
        print("❌ Some checks failed. Please review the errors above.")
        print()
        print("💡 Common fixes:")
        print("   - Run ./install.sh to create or refresh the venv")
        print("   - Use the repo venv in your MCP client config instead of bare python3")
        print("   - Reinstall the editable package with ./venv/bin/python -m pip install -e .")
        print()
        print("📖 See README.md for detailed installation instructions")

    print()
    return 0 if all_passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
