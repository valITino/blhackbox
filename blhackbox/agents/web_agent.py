"""WebAgent — normalizes HTTP findings, deduplicates paths, identifies CMS."""

from __future__ import annotations

from blhackbox.agents.base_agent import BaseAgent


class WebAgent(BaseAgent):
    """Processes raw web scanning output (gobuster, dirb, whatweb, wpscan, etc.)."""

    agent_name: str = "web_agent"
