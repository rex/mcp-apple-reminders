"""List-icon suggestion MCP tool — `suggest_list_icon`.

Read-only: ranks SF Symbol candidates for a proposed list title via the hybrid
suggester in `icon_suggest` (curated keyword table; the agent-fallback glyph
when nothing matches confidently). Creates and modifies nothing. The automatic
icon behaviour *at creation time* lives in `create_calendar` /
`create_smart_list` (their `icon` argument).
"""

from __future__ import annotations

from mcp.server.fastmcp import Context

from ..icon_suggest import IconSuggestionResult, suggest_icons
from ..server import mcp


@mcp.tool(
    name="suggest_list_icon",
    description=(
        "Suggest SF Symbol icons for a proposed Reminders list title. Returns "
        "ranked candidate symbols (each with the keywords it matched), a "
        "`recommended` symbol, and the `fallback` glyph used for agent-created "
        "lists when nothing matches confidently. Read-only — creates nothing. "
        "Pass a chosen symbol to `set_list_appearance`, or just let "
        "`create_calendar` / `create_smart_list` pick automatically via their "
        "`icon` argument."
    ),
)
async def suggest_list_icon(title: str, ctx: Context, limit: int = 5) -> IconSuggestionResult:
    """Rank icon candidates for `title`. See the tool description."""
    if not title or not title.strip():
        raise ValueError("title is required and must be non-empty")
    result = suggest_icons(title, limit=limit)
    await ctx.debug(f"suggest_list_icon({title!r}) → {result.recommended} (confident={result.confident})")
    return result
