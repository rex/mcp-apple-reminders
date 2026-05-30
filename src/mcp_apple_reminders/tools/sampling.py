"""Sampling-driven tools — Slice 2.5.

The MCP "sampling" primitive lets a server *ask the client's LLM* to do
work. We use it to classify Brain-Dump items into the right destination
list. The user remains in the loop because the client's LLM does the
inference — the tool just routes.

Today this slice ships only `triage_brain_dump`. Other sampling-driven
tools can follow the same pattern: read state from SQLite, build a
prompt, `await ctx.session.create_message(…)`, parse the response,
return structured output.
"""

from __future__ import annotations

import json
from typing import Optional

# `CreateMessageRequestParams` / `SamplingMessage` live under mcp.types in
# the SDK; we import lazily so server start doesn't fail if the SDK version
# drops or renames them.
from mcp import types as mcp_types
from mcp.server.fastmcp import Context

from .._native.sqlite import Reader, RemindersDBUnavailable
from ..lifespan import app_context as _app_context
from ..results import TriageResult
from ..server import mcp
from ._annotations import READ

_VALID_ROUTES = {
    "Claude-Active": "Working on it now.",
    "Claude-On-Deck": "Queued for the next session.",
    "Claude-Waiting": "Blocked by external input.",
    "Claude-Done": "Already finished; needs marking complete.",
    "delete": "Not worth doing; delete.",
}


def _build_triage_prompt(items: list) -> str:
    """Render the brain-dump items into a sampling prompt body."""
    lines = [
        "You are triaging a brain-dump list of reminders. For each item, "
        "pick exactly ONE destination from the options below.",
        "",
        "Options:",
    ]
    for name, desc in _VALID_ROUTES.items():
        lines.append(f"- `{name}` — {desc}")
    lines.extend(
        [
            "",
            "Items (id, title):",
        ]
    )
    for r in items:
        lines.append(f"- {r.id}\t{r.title}")
    lines.extend(
        [
            "",
            "Respond with JSON: a single object mapping each item id to its destination "
            "(one of the option strings above). Example:",
            '{"<uuid>": "Claude-Active", "<uuid>": "delete"}',
        ]
    )
    return "\n".join(lines)


def _parse_routing(response_text: str, valid_ids: set[str]) -> dict[str, str]:
    """Parse the sampling response into a {reminder_id: destination} dict."""
    raw = response_text.strip()
    # Strip code fences if the LLM wrapped JSON in them.
    if raw.startswith("```"):
        raw = "\n".join(line for line in raw.splitlines() if not line.startswith("```"))
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    if not isinstance(parsed, dict):
        return {}
    out: dict[str, str] = {}
    for k, v in parsed.items():
        if k in valid_ids and isinstance(v, str) and v in _VALID_ROUTES:
            out[k] = v
    return out


@mcp.tool(
    name="triage_brain_dump",
    title="Triage Brain Dump",
    annotations=READ,
    description=(
        "Triage the brain-dump list using the client's LLM via MCP Sampling. "
        "Reads every incomplete item from `from_list` (default Claude-Brain-Dump), "
        "asks the client to classify each as Active / On-Deck / Waiting / Done / delete, "
        "and returns the proposed routing. This tool does NOT move anything — "
        "the caller applies the routing with `move_reminder_*` tools afterwards."
    ),
)
async def triage_brain_dump(
    ctx: Context,
    from_list: str = "Claude-Brain-Dump",
    max_items: Optional[int] = 25,
) -> TriageResult:
    """Triage the brain-dump list via sampling.

    Args:
        from_list: List name to triage. Default `Claude-Brain-Dump`.
        max_items: Cap on the number of items sent to the LLM. Optional.
    """
    app = _app_context(ctx)
    try:
        with app.open_sqlite() as conn:
            reader = Reader(conn)
            cal = reader.get_calendar_by_name(from_list)
            if cal is None:
                raise ValueError(
                    f"List {from_list!r} not found. Create it in Apple Reminders first, "
                    f"or pass a different `from_list` argument."
                )
            items = list(reader.iter_reminders(calendar_id=cal.id, completed=False, limit=max_items))
    except RemindersDBUnavailable as e:
        await ctx.error(f"SQLite unavailable; can't read brain-dump items: {e}")
        raise ValueError(f"SQLite read path unavailable ({e}).") from e

    if not items:
        await ctx.info(f"triage_brain_dump: {from_list!r} is empty; nothing to do.")
        return TriageResult(from_list=from_list)

    prompt = _build_triage_prompt(items)
    await ctx.debug(f"triage_brain_dump: prompting LLM for {len(items)} item(s) via sampling.")

    # Sampling call. Older SDKs expose `ctx.session.create_message`.
    try:
        result = await ctx.session.create_message(
            messages=[
                mcp_types.SamplingMessage(
                    role="user",
                    content=mcp_types.TextContent(type="text", text=prompt),
                ),
            ],
            max_tokens=600,
            temperature=0.0,
        )
    except AttributeError as e:
        await ctx.error("Sampling not supported on this MCP session.")
        raise ValueError(
            f"This MCP client does not support sampling (ctx.session.create_message is missing). "
            f"Run the triage manually instead. ({e})"
        ) from e

    response_text = ""
    if isinstance(result.content, mcp_types.TextContent):
        response_text = result.content.text
    elif hasattr(result.content, "text"):
        response_text = str(result.content.text)

    valid_ids = {r.id for r in items}
    routing = _parse_routing(response_text, valid_ids)

    await ctx.info(
        f"triage_brain_dump: client routed {len(routing)}/{len(items)} item(s). " f"Apply via move_reminder_* tools."
    )

    return TriageResult(
        from_list=from_list,
        items=items,
        routing=routing,
        valid_destinations=list(_VALID_ROUTES.keys()),
        model_response=response_text,
    )


__all__ = ["triage_brain_dump"]
