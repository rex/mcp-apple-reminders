# Security Review — mcp-apple-reminders

Slice 4.4 of spec 002. Structured against the OWASP MCP Security Top 10
checklist + ad-hoc threat-modeling specific to the macOS Reminders surface.

## 1. Threat model

### 1.1 Trust boundaries

- **MCP client ↔ server**: stdio (default) or HTTP (opt-in, slice 4.3). Both
  are local-only by default. The MCP wire format itself is JSON-RPC; no
  authentication is layered on top because the transport itself is
  in-process or localhost-only.
- **Server ↔ Reminders.app SQLite store**: read-only file access (`mode=ro`
  on the connection URI; no `immutable=1` so concurrent writes are visible).
- **Server ↔ EventKit helper subprocess**: stdin/stdout JSON pipe. The
  subprocess runs with the same uid as the server.
- **Server ↔ ReminderKit (private framework) helper subprocess**: same.
  Linked against `/System/Library/PrivateFrameworks/`.
- **Server ↔ user TCC permissions**: the conda Python in `./venv/bin/`
  is the binary that holds the Reminders TCC grant.

### 1.2 Adversaries we consider

- **Hostile MCP request**: a malicious tool call from the client (e.g. a
  prompt-injected agent). The server should validate inputs and reject
  ambiguous or destructive operations without confirmation.
- **Hostile local process**: not in scope. The same user can already
  read/write Reminders via Reminders.app; we are not raising privilege.
- **Hostile network actor**: not in scope unless `streamable_http`
  transport is enabled. Even then, the server binds to localhost in the
  default config.

### 1.3 Adversaries we do NOT consider

- Kernel- or kext-level adversaries.
- Side-channel attacks (timing, electromagnetic, etc.).
- Threats to other macOS subsystems (Keychain, iCloud, etc.). We only
  touch Reminders.

## 2. OWASP MCP Top 10 walk-through

### MCP-1: Tool prompt injection

**Risk**: a malicious item title or notes field contains a prompt that
the client's LLM treats as an instruction.

**Mitigation**: the server never executes tool arguments as code, and
returns content as structured Pydantic. The client's LLM is responsible
for its own input handling — this is an upstream concern. We do call out
in the changelog (S2.5) that `triage_brain_dump` returns proposed routing
that the user must approve.

### MCP-2: Insecure tool authorization

**Risk**: any caller can invoke any tool.

**Mitigation**: we don't currently gate tools per-call. The `VIBE.yaml::
agents.tool_flags` map (sketched below) is the planned hook for a kill
switch. Future work.

### MCP-3: Excessive agency

**Risk**: a tool does more than the user intended (e.g. deletes the wrong
list).

**Mitigations**:
- `delete_calendar(force=False)` refuses to cascade-delete non-empty lists.
- `delete_calendar(force=True)` on the **default** calendar is rejected
  unconditionally (S1.3).
- `delete_calendar(force=True)` with N≥1 reminders calls `ctx.elicit` for
  user confirmation (S2.4).
- `bulk_delete_completed` calls `ctx.elicit` before the cascade fires
  (S3.4).
- `set_parent` is **deferred** — there is no way to detach/reassign a
  parent today; the missing capability is documented rather than fudged.

### MCP-4: Insecure direct object references

**Risk**: passing an arbitrary UUID lets you touch anything.

**Mitigation**: every write tool resolves the UUID via the SQLite reader
or the bridge before invoking the helper — non-existent IDs raise
`ValueError` early. The Obj-C helper additionally fails closed on
unknown reminders ("Reminder not found").

### MCP-5: Insecure transport

**Risk**: stdio gives a co-process full bidirectional access without
authentication.

**Mitigation**: stdio is the default; the parent client process is
trusted by design. The `streamable_http` transport binds to localhost
and does **not** ship auth in this slice — running it remotely without a
reverse-proxy that handles auth would be incorrect; the VIBE.yaml hint
calls this out.

### MCP-6: Output sanitization

**Risk**: a malicious reminder title is rendered as HTML/markdown in
the client and triggers DOM injection.

**Mitigation**: Pydantic models return raw strings; the client is
responsible for safe rendering. We do not transform or escape on the
server.

### MCP-7: Excessive data exposure

**Risk**: the SQLite reader returns more than the caller needs.

**Mitigation**: the `Reminder` Pydantic model is a documented contract.
We don't surface internal Z_PK values, raw blobs, or partial database
internals. The `tags_csv` correlated subquery returns just tag names.

### MCP-8: Insufficient logging

**Risk**: destructive ops happen without an audit trail.

**Mitigation**: every destructive tool logs `await ctx.warning(...)`
before firing and `ctx.info(...)` on success. Failures log
`ctx.error(...)`. Logs flow through the MCP session — clients with a
logging UI see them.

### MCP-9: Vulnerable dependencies

**Risk**: a CVE in `mcp` or `pyobjc` reaches the server.

**Mitigation**: `pyproject.toml` pins `mcp>=1.27,<2` and `pyobjc-*
>=12.0,<13` (S0.1). The architecture gate requires bumping a VERSION on
every commit, surfacing dependency churn. Pre-commit hooks include
`detect-secrets` and `gitleaks` (S0.6 hardening).

### MCP-10: Server side request forgery (SSRF)

**Risk**: not applicable — the server never makes outbound HTTP
requests on behalf of the caller.

## 3. Per-tool kill switch sketch (deferred to a follow-up slice)

The `VIBE.yaml::agents.tool_flags` map (planned) would let an operator
disable destructive tools at startup:

```yaml
agents:
  tool_flags:
    delete_calendar: enabled
    delete_reminder: enabled
    bulk_delete_completed: disabled        # block this tool from being called
```

A small `tools/_kill_switch.py` helper would consult that map in the
`@mcp.tool` decorator and raise `ValueError` early for disabled tools.
Implementation is straightforward but out of scope for slice 4.4 — the
threat model + walk-through above is what S4.4 promised.

## 4. Conclusion

The current surface is **safe for single-user, single-machine** use with
trust placed in the MCP client (Claude Desktop, Claude Code, Codex). The
elicitation guards on the cascading-delete paths are the user's last
line of defense against agent misbehavior. The private-framework
ReminderKit helper is a third-party dependency tracked in
`_native/THIRD_PARTY_NOTICES.md` and is subject to macOS-release breakage.

## References

- OWASP MCP Top 10 — <https://github.com/OWASP/www-project-mcp-security-top-10>
- spec 002 `design.md` § "Threat model + trust boundaries"
- `_native/THIRD_PARTY_NOTICES.md` for the borrowed Swift/Obj-C source
  attribution + upstream pin.
