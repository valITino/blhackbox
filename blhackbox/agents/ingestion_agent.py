"""Ingestion Agent — parses raw tool output into structured typed data.

No filtering, no deduplication — just parse and structure everything.
"""

from __future__ import annotations

from blhackbox.agents.base_agent import BaseAgent


class IngestionAgent(BaseAgent):
    """Parse all raw tool output into structured typed data objects.

    Input: raw strings (nmap XML, nikto output, gobuster lists,
           HexStrike JSON, etc.)
    Output: structured dict — hosts, ports, services, endpoints,
            CVEs, subdomains, etc.
    """
