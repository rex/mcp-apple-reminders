# Security Policy

## Reporting a vulnerability

Please **do not** open public GitHub issues for security vulnerabilities.

Instead, open a private security advisory:
<https://github.com/rex/mcp-apple-reminders/security/advisories/new>

Or email the maintainer at the address in the `pyproject.toml` `authors` field.

You can expect an initial response within 7 days. We'll work with you on a fix
and disclosure timeline.

## Scope

- The MCP server reads and writes your local Apple Reminders database via
  EventKit. It runs entirely on your machine over stdio; there is no network
  surface in default operation.
- Permissions are governed by macOS TCC (Reminders access). Revoke at any time
  in System Settings → Privacy & Security → Reminders.

## Out of scope

- Third-party MCP clients you connect to this server.
- The upstream `pyremindkit` and `pyobjc` dependencies (please report those to
  their respective maintainers).
