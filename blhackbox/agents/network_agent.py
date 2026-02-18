"""NetworkAgent — parses open ports, services, versions, and OS fingerprints."""

from __future__ import annotations

from blhackbox.agents.base_agent import BaseAgent


class NetworkAgent(BaseAgent):
    """Processes raw network scanning output (nmap, masscan, rustscan, etc.)."""

    agent_name: str = "network_agent"
