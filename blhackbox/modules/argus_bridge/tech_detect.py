"""Technology detection module using HexStrike's httpx/whatweb."""

from __future__ import annotations

import json
import logging
from typing import Any

from blhackbox.models.base import Finding, Severity
from blhackbox.modules.base import HexStrikeModule

logger = logging.getLogger("blhackbox.modules.argus_bridge.tech_detect")


class TechDetectModule(HexStrikeModule):
    """Detect technologies on a target using HexStrike web tools."""

    name = "tech_detect"
    description = "Technology stack detection via httpx and whatweb"
    category = "web"

    async def run(self, target: str, **kwargs: Any) -> list[Finding]:
        """Run httpx and whatweb for technology fingerprinting."""
        self.clear_findings()
        technologies: dict[str, str] = {}  # tech_name -> details

        # Tool 1: httpx with tech detection
        try:
            result = await self._client.run_tool(
                "web", "httpx", {"target": target, "flags": ["-tech-detect"]}
            )
            techs = _parse_httpx_tech(result.output, result.raw_output)
            technologies.update(techs)
            logger.info("httpx detected %d technologies", len(techs))
        except Exception as exc:
            logger.warning("httpx tech detection failed: %s", exc)

        # Tool 2: whatweb
        try:
            result = await self._client.run_tool(
                "web", "whatweb", {"target": target}
            )
            techs = _parse_whatweb(result.output, result.raw_output)
            technologies.update(techs)
            logger.info("whatweb detected %d technologies", len(techs))
        except Exception as exc:
            logger.warning("whatweb failed: %s", exc)

        if technologies:
            desc_lines = [f"- {name}: {detail}" for name, detail in sorted(technologies.items())]
            self.add_finding(
                target=target,
                title=f"Technology Detection: {len(technologies)} technologies identified",
                description="\n".join(desc_lines),
                severity=Severity.INFO,
                evidence=json.dumps(technologies, indent=2),
                raw_data={"technologies": technologies},
            )
        else:
            self.add_finding(
                target=target,
                title="Technology Detection: No technologies identified",
                description="Could not detect any technologies on the target.",
                severity=Severity.INFO,
            )

        return self.findings


def _parse_httpx_tech(output: Any, raw_output: str) -> dict[str, str]:
    """Parse technology info from httpx output."""
    techs: dict[str, str] = {}
    text = raw_output or ""
    if isinstance(output, dict):
        for key in ("technologies", "tech", "fingerprints"):
            if key in output:
                items = output[key]
                if isinstance(items, list):
                    for item in items:
                        name = item if isinstance(item, str) else str(item)
                        techs[name] = "detected by httpx"
                elif isinstance(items, dict):
                    for k, v in items.items():
                        techs[k] = str(v)
    if isinstance(output, str):
        text += " " + output
    # Simple line parsing fallback
    for line in text.split("\n"):
        line = line.strip()
        if line and "[" in line and "]" in line:
            # httpx format: [tech1,tech2]
            start = line.find("[")
            end = line.find("]")
            if start < end:
                tech_str = line[start + 1 : end]
                for t in tech_str.split(","):
                    t = t.strip()
                    if t:
                        techs[t] = "detected by httpx"
    return techs


def _parse_whatweb(output: Any, raw_output: str) -> dict[str, str]:
    """Parse technology info from whatweb output."""
    techs: dict[str, str] = {}
    text = raw_output or ""
    if isinstance(output, dict):
        for k, v in output.items():
            techs[k] = str(v)
    elif isinstance(output, list):
        for item in output:
            if isinstance(item, dict):
                name = item.get("name", item.get("plugin", str(item)))
                version = item.get("version", "")
                techs[str(name)] = version or "detected by whatweb"
            else:
                techs[str(item)] = "detected by whatweb"
    # Line-based parsing for raw text
    for line in text.split("\n"):
        line = line.strip()
        if line and "," in line:
            parts = line.split(",")
            for part in parts:
                part = part.strip()
                if part and "[" not in part and "http" not in part.lower():
                    techs[part] = "detected by whatweb"
    return techs
