"""Wire client + reporter for the integration suite.

`wire_session()` spins up a fresh stdio server; `WireClient` unwraps tool /
resource / prompt results and records pass/fail into a `Reporter`. Everything is
assertion-free at the harness layer — scenarios call `reporter.check(...)` so a
single failure never aborts the whole run (we still want the rest of the
coverage + the cleanup to execute).
"""

from __future__ import annotations

import json
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Any, Optional

from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client
from pydantic import AnyUrl

SERVER = StdioServerParameters(command="./venv/bin/python", args=["-m", "mcp_apple_reminders"])


@dataclass
class Check:
    name: str
    ok: bool
    detail: str = ""


@dataclass
class Reporter:
    checks: list[Check] = field(default_factory=list)

    def check(self, name: str, cond: Any, detail: str = "") -> bool:
        ok = bool(cond)
        self.checks.append(Check(name, ok, detail))
        mark = "\033[32mPASS\033[0m" if ok else "\033[31mFAIL\033[0m"
        line = f"  [{mark}] {name}"
        if detail and not ok:
            line += f" — {detail}"
        print(line, flush=True)
        return ok

    @property
    def failed(self) -> list[Check]:
        return [c for c in self.checks if not c.ok]

    def summary(self) -> str:
        total = len(self.checks)
        nf = len(self.failed)
        return f"{total - nf}/{total} checks passed" + (f"  ({nf} FAILED)" if nf else "  — all green")


def _err_text(res: Any) -> str:
    for c in getattr(res, "content", []) or []:
        if hasattr(c, "text"):
            return str(c.text)[:300]
    return "isError=True (no text content)"


class WireClient:
    """Async wrapper over `ClientSession` with result-unwrapping helpers."""

    def __init__(self, session: ClientSession, reporter: Reporter) -> None:
        self.s = session
        self.r = reporter

    async def call_raw(self, name: str, args: Optional[dict] = None) -> Any:
        return await self.s.call_tool(name, args or {})

    async def call_ok(self, name: str, args: Optional[dict] = None, *, label: str = "") -> Optional[dict]:
        """Call a tool, assert ``not isError``, return its structuredContent."""
        res = await self.s.call_tool(name, args or {})
        ok = not res.isError
        self.r.check(label or f"call {name}", ok, "" if ok else _err_text(res))
        return res.structuredContent if ok else None

    async def call_value(self, name: str, args: Optional[dict] = None, *, label: str = "") -> Any:
        """Call a tool whose structuredContent wraps a list / Optional in ``result``."""
        sc = await self.call_ok(name, args, label=label)
        if isinstance(sc, dict) and list(sc.keys()) == ["result"]:
            return sc["result"]
        return sc

    async def call_expect_error(self, name: str, args: Optional[dict] = None, *, label: str = "") -> str:
        """Call a tool expecting ``isError`` (negative test). Returns the error text."""
        res = await self.s.call_tool(name, args or {})
        self.r.check(label or f"{name} rejects bad input", res.isError, "expected isError=True")
        return _err_text(res)

    async def read_json(self, uri: str) -> Optional[dict]:
        res = await self.s.read_resource(AnyUrl(uri))
        for c in res.contents:
            if hasattr(c, "text") and c.text:
                try:
                    return json.loads(c.text)
                except json.JSONDecodeError:
                    return {"_raw": c.text}
        return None

    async def prompt_text(self, name: str, args: Optional[dict] = None) -> str:
        res = await self.s.get_prompt(name, args or None)
        return "".join(m.content.text if hasattr(m.content, "text") else "" for m in res.messages)

    async def tool_map(self) -> dict[str, Any]:
        return {t.name: t for t in (await self.s.list_tools()).tools}


@asynccontextmanager
async def wire_session(reporter: Reporter):
    async with stdio_client(SERVER) as (read, write), ClientSession(read, write) as session:
        await session.initialize()
        yield WireClient(session, reporter)
