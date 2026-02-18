"""VulnAgent — deduplicates CVEs, normalizes severity, groups by host."""

from __future__ import annotations

from blhackbox.agents.base_agent import BaseAgent


class VulnAgent(BaseAgent):
    """Processes raw vulnerability scan output (nuclei, nikto, etc.)."""

    agent_name: str = "vuln_agent"
