"""Base class for all Ollama preprocessing agents.

Each agent is a plain Python class that:
1. Loads a task-specific system prompt from a .md file
2. Sends the prompt + raw pentest data to Ollama's POST /api/chat endpoint
3. Parses the JSON response into a Python dict

There is no agent framework involved — just httpx HTTP calls to a standard
Ollama instance running on localhost:11434.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import httpx

logger = logging.getLogger("blhackbox.agents.base")

# Resolve prompts directory relative to this file
_PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts" / "agents"


class BaseAgent:
    """Abstract base for Ollama preprocessing agents.

    Subclasses set ``agent_name`` which determines which prompt file to load
    (e.g. ``recon_agent`` loads ``prompts/agents/recon_agent.md``).
    """

    agent_name: str = "base"

    def __init__(
        self,
        ollama_url: str = "http://localhost:11434",
        model: str = "llama3.3",
    ) -> None:
        self.ollama_url = ollama_url.rstrip("/")
        self.model = model
        self.system_prompt = self._load_prompt()

    def _load_prompt(self) -> str:
        """Load the agent's system prompt from its .md file."""
        prompt_file = _PROMPTS_DIR / f"{self.agent_name}.md"
        if not prompt_file.exists():
            logger.warning("Prompt file not found: %s", prompt_file)
            return f"You are a {self.agent_name} data processing agent. Respond only in valid JSON."
        return prompt_file.read_text(encoding="utf-8")

    async def process(self, raw_data: str) -> dict[str, Any]:
        """Send raw data to Ollama for processing and return parsed JSON.

        If Ollama is unreachable or returns invalid JSON, returns an empty dict
        rather than raising — the caller is responsible for degraded handling.
        """
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    f"{self.ollama_url}/api/chat",
                    json={
                        "model": self.model,
                        "messages": [
                            {"role": "system", "content": self.system_prompt},
                            {"role": "user", "content": raw_data},
                        ],
                        "stream": False,
                        "format": "json",
                    },
                )
                response.raise_for_status()
        except (httpx.HTTPError, OSError) as exc:
            logger.error("%s: Ollama request failed: %s", self.agent_name, exc)
            return {}

        return self._parse(response.json())

    def _parse(self, ollama_response: dict[str, Any]) -> dict[str, Any]:
        """Extract and parse the JSON content from Ollama's response."""
        message = ollama_response.get("message", {})
        content = message.get("content", "")

        if not content:
            logger.warning("%s: Empty response from Ollama", self.agent_name)
            return {}

        try:
            return json.loads(content)
        except json.JSONDecodeError:
            # Try to extract JSON from the response text
            text = content.strip()
            start = text.find("{")
            end = text.rfind("}") + 1
            if start >= 0 and end > start:
                try:
                    return json.loads(text[start:end])
                except json.JSONDecodeError:
                    pass
            logger.warning(
                "%s: Could not parse Ollama response as JSON: %s",
                self.agent_name,
                text[:200],
            )
            return {}
