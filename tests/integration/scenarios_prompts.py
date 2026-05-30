"""All 5 MCP prompts render over the wire (get_prompt), against the fixture list."""

from __future__ import annotations

from .fixtures import TestStore
from .harness import Reporter, WireClient


async def run(c: WireClient, store: TestStore, r: Reporter) -> None:
    lname = store.list_name

    daily = await c.prompt_text("daily_review")
    r.check("daily_review renders", "Daily Review" in daily)

    weekly = await c.prompt_text("weekly_retro", {"window_days": "7"})
    r.check("weekly_retro renders (7-day window)", "Weekly Retro" in weekly and "7 day" in weekly)

    bd = await c.prompt_text("brain_dump_triage", {"list_name": lname})
    r.check("brain_dump_triage renders for fixture list", lname in bd)

    av = await c.prompt_text("agent_visibility_sync", {"project_name": "IntegTest"})
    r.check("agent_visibility_sync mentions Agents-IntegTest", "Agents-IntegTest" in av)

    org = await c.prompt_text("organize_into_sections", {"list_name": lname})
    r.check("organize_into_sections renders for fixture list", lname in org)
