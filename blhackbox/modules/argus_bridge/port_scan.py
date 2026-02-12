"""Port scanning module using HexStrike's nmap/rustscan."""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Tuple

from blhackbox.models.base import Finding, Severity
from blhackbox.modules.base import HexStrikeModule

logger = logging.getLogger("blhackbox.modules.argus_bridge.port_scan")

_PORT_LINE_RE = re.compile(r"(\d{1,5})/(tcp|udp)\s+(\w+)\s+(.*)")


class PortScanModule(HexStrikeModule):
    """Comprehensive port scan using nmap via HexStrike."""

    name = "port_scan"
    description = "Port scanning and service detection via nmap"
    category = "network"

    async def run(self, target: str, **kwargs: Any) -> List[Finding]:
        """Run nmap service scan via HexStrike."""
        self.clear_findings()
        scan_type = kwargs.get("scan_type", "service")

        flags = {
            "quick": ["-F", "-T4"],
            "service": ["-sV", "-sC", "-T4"],
            "full": ["-sV", "-sC", "-p-", "-T4"],
        }.get(scan_type, ["-sV", "-sC", "-T4"])

        try:
            result = await self._client.run_tool(
                "network", "nmap", {"target": target, "flags": flags}
            )
        except Exception as exc:
            self.add_finding(
                target=target,
                title="Port Scan Failed",
                description=f"nmap scan failed: {exc}",
                severity=Severity.LOW,
            )
            return self.findings

        ports = _parse_nmap_ports(result.output, result.raw_output)

        if ports:
            desc_lines = []
            for port, proto, state, service in ports:
                desc_lines.append(f"{port}/{proto}  {state}  {service}")

            self.add_finding(
                target=target,
                title=f"Port Scan: {len(ports)} open ports found",
                description="\n".join(desc_lines),
                severity=Severity.INFO,
                evidence=result.raw_output[:5000] if result.raw_output else "",
                raw_data={
                    "ports": [
                        {
                            "port": p,
                            "protocol": proto,
                            "state": state,
                            "service": svc,
                        }
                        for p, proto, state, svc in ports
                    ]
                },
            )

            # Flag potentially risky services
            for port, proto, state, service in ports:
                sev = _service_severity(port, service)
                if sev in (Severity.HIGH, Severity.CRITICAL):
                    self.add_finding(
                        target=target,
                        title=f"Risky Service: {service} on port {port}/{proto}",
                        description=(
                            f"Service '{service}' on port {port} may pose a security risk."
                        ),
                        severity=sev,
                        remediation=(
                            "Review if this service needs to be publicly exposed. "
                            "Consider firewall rules or VPN access."
                        ),
                    )
        else:
            self.add_finding(
                target=target,
                title="Port Scan: No open ports detected",
                description="nmap did not find any open ports.",
                severity=Severity.INFO,
            )

        return self.findings


def _parse_nmap_ports(
    output: Any, raw_output: str
) -> List[Tuple[int, str, str, str]]:
    """Extract (port, protocol, state, service) tuples from nmap output."""
    ports: List[Tuple[int, str, str, str]] = []
    text = raw_output or ""

    if isinstance(output, dict):
        # Structured nmap output
        for key in ("ports", "open_ports", "results"):
            if key in output and isinstance(output[key], list):
                for entry in output[key]:
                    if isinstance(entry, dict):
                        ports.append((
                            int(entry.get("port", 0)),
                            entry.get("protocol", "tcp"),
                            entry.get("state", "open"),
                            entry.get("service", "unknown"),
                        ))
    elif isinstance(output, str):
        text += " " + output

    # Regex fallback on raw text
    for match in _PORT_LINE_RE.finditer(text):
        port_num = int(match.group(1))
        proto = match.group(2)
        state = match.group(3)
        service = match.group(4).strip()
        ports.append((port_num, proto, state, service))

    # Deduplicate
    seen = set()
    unique = []
    for entry in ports:
        key = (entry[0], entry[1])
        if key not in seen:
            seen.add(key)
            unique.append(entry)

    return unique


def _service_severity(port: int, service: str) -> Severity:
    """Estimate severity based on port/service exposure."""
    svc_lower = service.lower()
    high_risk = {"telnet", "ftp", "rlogin", "rsh", "rexec", "vnc", "rdp"}
    critical_ports = {23, 21, 3389, 5900}

    if port in critical_ports or any(r in svc_lower for r in high_risk):
        return Severity.HIGH
    if port in {3306, 5432, 6379, 27017, 9200}:
        return Severity.HIGH
    return Severity.INFO
