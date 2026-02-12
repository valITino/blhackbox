"""AI Planner — uses LLM to decide the next tool/agent to execute."""

from __future__ import annotations

import json
import logging
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from blhackbox.llm.client import get_llm
from blhackbox.llm.prompts import SYSTEM_PROMPT, build_user_prompt

logger = logging.getLogger("blhackbox.core.planner")

# Default tools available via HexStrike
DEFAULT_AVAILABLE_TOOLS = """
Network:
  - nmap: Port scanning and service detection
  - rustscan: Fast port scanner
  - masscan: High-speed port scanner

Web:
  - nuclei: Template-based vulnerability scanner
  - ffuf: Web fuzzer (directories, parameters)
  - httpx: HTTP probe and technology detection
  - whatweb: Web technology identification

DNS / Subdomains:
  - subfinder: Subdomain discovery
  - amass: In-depth subdomain enumeration
  - dnsx: DNS query tool

Intelligence:
  - analyze-target: AI-driven comprehensive target analysis

AI Agents:
  - bug_bounty: Autonomous bug bounty agent
  - recon: Dedicated recon agent
  - cve_intel: CVE intelligence agent
"""


class Planner:
    """Uses an LLM to plan the next reconnaissance step."""

    def __init__(self, max_iterations: int = 10) -> None:
        self._llm = get_llm()
        self._max_iterations = max_iterations

    async def decide_next(
        self,
        target: str,
        iteration: int,
        completed_tools: list[str],
        findings_summary: str,
        available_tools: str = DEFAULT_AVAILABLE_TOOLS,
    ) -> dict[str, Any]:
        """Ask the LLM to decide the next action.

        Returns a dict with keys: action, category, tool, params, reasoning
        or: action=stop, reasoning.
        """
        user_msg = build_user_prompt(
            target=target,
            iteration=iteration,
            max_iterations=self._max_iterations,
            completed_tools=completed_tools,
            findings_summary=findings_summary,
            available_tools=available_tools,
        )

        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=user_msg),
        ]

        logger.info("Planner iteration %d: asking LLM for next action", iteration)
        response = await self._llm.ainvoke(messages)
        raw = response.content if hasattr(response, "content") else str(response)
        logger.debug("Planner raw response: %s", raw)

        return _parse_llm_response(raw)


def _parse_llm_response(raw: str) -> dict[str, Any]:
    """Parse the LLM JSON response, handling markdown fences and edge cases."""
    text = raw.strip()

    # Strip markdown code fences if present
    if text.startswith("```"):
        lines = text.split("\n")
        # Remove first and last fence lines
        lines = [line for line in lines if not line.strip().startswith("```")]
        text = "\n".join(lines).strip()

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        # Try to extract JSON from the response
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            try:
                data = json.loads(text[start:end])
            except json.JSONDecodeError:
                logger.warning("Could not parse LLM response as JSON: %s", text[:200])
                return {"action": "stop", "reasoning": "Failed to parse planner response"}
        else:
            logger.warning("No JSON found in LLM response: %s", text[:200])
            return {"action": "stop", "reasoning": "Failed to parse planner response"}

    action = data.get("action", "stop")
    if action not in ("run_tool", "run_agent", "stop"):
        logger.warning("Unknown action '%s', stopping", action)
        return {"action": "stop", "reasoning": f"Unknown action: {action}"}

    return data
