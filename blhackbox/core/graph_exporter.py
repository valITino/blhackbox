"""Translate HexStrike JSON results into knowledge graph operations."""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List

from blhackbox.core.knowledge_graph import KnowledgeGraphClient
from blhackbox.models.base import Finding, ScanSession

logger = logging.getLogger("blhackbox.core.graph_exporter")

# Regex patterns for extracting structured data from tool output
_IP_PATTERN = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
_PORT_PATTERN = re.compile(r"(\d{1,5})/(tcp|udp)\s+\w+\s+(.*)")
_SUBDOMAIN_PATTERN = re.compile(r"(?:[a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}")
_CVE_PATTERN = re.compile(r"CVE-\d{4}-\d{4,}", re.IGNORECASE)


class GraphExporter:
    """Exports HexStrike results into the Neo4j knowledge graph.

    Handles multiple output formats from different tools and agents,
    parsing structured data and creating appropriate nodes/relationships.
    """

    def __init__(self, kg_client: KnowledgeGraphClient) -> None:
        self._kg = kg_client

    async def export_session(self, session: ScanSession) -> int:
        """Export all findings from a scan session into the graph.

        Returns the number of graph operations performed.
        """
        target = str(session.target)
        ops = 0

        # Ensure the root target node exists
        await self._kg.merge_domain(target)
        ops += 1

        for finding in session.findings:
            ops += await self._export_finding(target, finding)

        logger.info("Exported session %s: %d graph operations", session.id, ops)
        return ops

    async def export_tool_result(
        self,
        target: str,
        tool: str,
        category: str,
        output: Any,
    ) -> int:
        """Export a single tool result into the graph.

        Dispatches to specialised handlers based on tool category/name.
        """
        ops = 0
        await self._kg.merge_domain(target)
        ops += 1

        if category == "network":
            ops += await self._handle_network(target, tool, output)
        elif category == "web":
            ops += await self._handle_web(target, tool, output)
        elif category == "intelligence":
            ops += await self._handle_intelligence(target, tool, output)
        else:
            ops += await self._handle_generic(target, tool, category, output)

        return ops

    # -- internal handlers ---------------------------------------------------

    async def _export_finding(self, target: str, finding: Finding) -> int:
        """Export a Finding model into the graph."""
        ops = 0

        await self._kg.merge_finding(
            target_value=finding.target,
            finding_id=finding.id,
            tool=finding.tool,
            title=finding.title,
            severity=finding.severity if isinstance(finding.severity, str) else finding.severity.value,
            description=finding.description,
            evidence=finding.evidence,
            remediation=finding.remediation,
        )
        ops += 1

        # Extract IPs from raw data/description
        text = finding.description + " " + finding.evidence
        for ip in _IP_PATTERN.findall(text):
            await self._kg.link_domain_to_ip(finding.target, ip)
            ops += 1

        # Extract subdomains
        for sub in _SUBDOMAIN_PATTERN.findall(text):
            if sub != target and target in sub:
                await self._kg.link_subdomain(sub, target)
                ops += 1

        # Extract CVEs
        for cve in _CVE_PATTERN.findall(text):
            await self._kg.merge_vulnerability(
                target_value=finding.target,
                identifier=cve.upper(),
                severity=finding.severity if isinstance(finding.severity, str) else finding.severity.value,
                title=finding.title,
            )
            ops += 1

        return ops

    async def _handle_network(self, target: str, tool: str, output: Any) -> int:
        """Handle network tool output (nmap, rustscan, masscan)."""
        ops = 0
        text = _to_text(output)

        # Extract IPs
        for ip in _IP_PATTERN.findall(text):
            await self._kg.link_domain_to_ip(target, ip)
            ops += 1

        # Extract port/service lines (nmap-style)
        for match in _PORT_PATTERN.finditer(text):
            port_num = int(match.group(1))
            protocol = match.group(2)
            service_info = match.group(3).strip()
            service_name = service_info.split()[0] if service_info else "unknown"

            # Use first detected IP, or infer from target
            ips = _IP_PATTERN.findall(text)
            ip = ips[0] if ips else target

            await self._kg.merge_service(ip, port_num, service_name)
            ops += 1

        return ops

    async def _handle_web(self, target: str, tool: str, output: Any) -> int:
        """Handle web tool output (nuclei, ffuf, httpx)."""
        ops = 0
        text = _to_text(output)

        # Subdomains
        for sub in _SUBDOMAIN_PATTERN.findall(text):
            if sub != target and target in sub:
                await self._kg.link_subdomain(sub, target)
                ops += 1

        # CVEs from nuclei
        for cve in _CVE_PATTERN.findall(text):
            await self._kg.merge_vulnerability(
                target_value=target,
                identifier=cve.upper(),
                severity="medium",
                title=f"Detected by {tool}",
            )
            ops += 1

        return ops

    async def _handle_intelligence(self, target: str, tool: str, output: Any) -> int:
        """Handle intelligence/analysis output."""
        ops = 0
        if isinstance(output, dict):
            # Recursively extract useful data
            text = _to_text(output)
            for ip in _IP_PATTERN.findall(text):
                await self._kg.link_domain_to_ip(target, ip)
                ops += 1
            for sub in _SUBDOMAIN_PATTERN.findall(text):
                if sub != target and target in sub:
                    await self._kg.link_subdomain(sub, target)
                    ops += 1
        return ops

    async def _handle_generic(
        self, target: str, tool: str, category: str, output: Any
    ) -> int:
        """Fallback handler for unknown tool categories."""
        ops = 0
        text = _to_text(output)

        for ip in _IP_PATTERN.findall(text):
            await self._kg.link_domain_to_ip(target, ip)
            ops += 1

        for cve in _CVE_PATTERN.findall(text):
            await self._kg.merge_vulnerability(
                target_value=target,
                identifier=cve.upper(),
                severity="info",
                title=f"Found by {tool}",
            )
            ops += 1

        return ops


def _to_text(data: Any) -> str:
    """Flatten arbitrary data into a searchable text string."""
    if isinstance(data, str):
        return data
    if isinstance(data, dict):
        parts = []
        for v in data.values():
            parts.append(_to_text(v))
        return " ".join(parts)
    if isinstance(data, (list, tuple)):
        return " ".join(_to_text(item) for item in data)
    return str(data)
