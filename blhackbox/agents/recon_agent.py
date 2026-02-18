"""ReconAgent — extracts subdomains, IPs, technologies, ASN, and certificates."""

from __future__ import annotations

from blhackbox.agents.base_agent import BaseAgent


class ReconAgent(BaseAgent):
    """Processes raw reconnaissance output (subfinder, amass, WHOIS, CT logs, etc.)."""

    agent_name: str = "recon_agent"
