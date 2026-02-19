"""Base class for all Ollama preprocessing agents.

Each agent is a plain Python class that:
1. Loads a task-specific system prompt from a .md file at runtime
2. Sends the prompt + raw pentest data to Ollama's POST /api/chat endpoint
3. Parses the JSON response into a Python dict

There is no agent framework involved — just httpx HTTP calls to a standard
Ollama instance running unchanged as a Docker container.
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

    Subclasses are named IngestionAgent, ProcessingAgent, SynthesisAgent.
    The prompt file is determined by lowercasing the class name
    (e.g. ``IngestionAgent`` loads ``prompts/agents/ingestionagent.md``).
    """

    def __init__(
        self,
        ollama_url: str = "http://localhost:11434",
        model: str = "llama3.3",
    ) -> None:
        self.ollama_url = ollama_url.rstrip("/")
        self.model = model
        # Load system prompt from prompts/agents/<classname>.md at runtime
        prompt_file = _PROMPTS_DIR / f"{self.__class__.__name__.lower()}.md"
        if prompt_file.exists():
            self.system_prompt = prompt_file.read_text(encoding="utf-8")
        else:
            logger.warning("Prompt file not found: %s", prompt_file)
            self.system_prompt = (
                f"You are a {self.__class__.__name__} data processing agent. "
                "Respond only in valid JSON."
            )

    async def process(self, data: dict | str) -> dict[str, Any]:
        """Send data to Ollama for processing and return parsed JSON.

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
                            {"role": "user", "content": str(data)},
                        ],
                        "stream": False,
                        "format": "json",  # forces Ollama to respond in valid JSON
                    },
                )
                response.raise_for_status()
        except (httpx.HTTPError, OSError) as exc:
            logger.error(
                "%s: Ollama request failed: %s", self.__class__.__name__, exc
            )
            return {}

        return self._parse(response.json())

    def _parse(self, response: dict[str, Any]) -> dict[str, Any]:
        """Extract and parse the JSON content from Ollama's response."""
        message = response.get("message", {})
        content = message.get("content", "")

        if not content:
            logger.warning(
                "%s: Empty response from Ollama", self.__class__.__name__
            )
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
                self.__class__.__name__,
                text[:200],
            )
            return {}
