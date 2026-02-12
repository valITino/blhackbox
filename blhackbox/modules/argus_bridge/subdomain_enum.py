"""Subdomain enumeration module using HexStrike's subfinder/amass."""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from blhackbox.models.base import Finding, Severity
from blhackbox.modules.base import HexStrikeModule

logger = logging.getLogger("blhackbox.modules.argus_bridge.subdomain_enum")

_SUBDOMAIN_RE = re.compile(r"(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}")


class SubdomainEnumModule(HexStrikeModule):
    """Enumerate subdomains using multiple HexStrike tools and deduplicate."""

    name = "subdomain_enum"
    description = "Multi-source subdomain enumeration via HexStrike"
    category = "dns"

    async def run(self, target: str, **kwargs: Any) -> list[Finding]:
        """Run subfinder and amass via HexStrike, merge and deduplicate results."""
        self.clear_findings()
        all_subdomains: set[str] = set()

        # Tool 1: subfinder
        try:
            result = await self._client.run_tool(
                "dns", "subfinder", {"target": target}
            )
            subs = _extract_subdomains(result.output, result.raw_output, target)
            all_subdomains.update(subs)
            logger.info("subfinder found %d subdomains", len(subs))
        except Exception as exc:
            logger.warning("subfinder failed: %s", exc)

        # Tool 2: amass (passive)
        try:
            result = await self._client.run_tool(
                "dns", "amass", {"target": target, "mode": "passive"}
            )
            subs = _extract_subdomains(result.output, result.raw_output, target)
            all_subdomains.update(subs)
            logger.info("amass found %d subdomains", len(subs))
        except Exception as exc:
            logger.warning("amass failed: %s", exc)

        # Build findings
        if all_subdomains:
            sorted_subs = sorted(all_subdomains)
            self.add_finding(
                target=target,
                title=f"Subdomain Enumeration: {len(sorted_subs)} subdomains found",
                description="\n".join(sorted_subs),
                severity=Severity.INFO,
                evidence=json.dumps(sorted_subs),
                raw_data={"subdomains": sorted_subs, "count": len(sorted_subs)},
            )
        else:
            self.add_finding(
                target=target,
                title="Subdomain Enumeration: No subdomains found",
                description="No subdomains were discovered.",
                severity=Severity.INFO,
            )

        return self.findings


def _extract_subdomains(output: Any, raw_output: str, parent: str) -> set[str]:
    """Extract unique subdomains from tool output."""
    text = raw_output or ""
    if isinstance(output, list):
        text += " ".join(str(item) for item in output)
    elif isinstance(output, dict):
        text += " " + json.dumps(output)
    elif isinstance(output, str):
        text += " " + output

    found: set[str] = set()
    for match in _SUBDOMAIN_RE.findall(text):
        match_lower = match.lower().rstrip(".")
        if parent in match_lower and match_lower != parent:
            found.add(match_lower)
    return found
