"""Base class for all Ollama preprocessing agents.

Each agent is a plain Python class that:
1. Loads a task-specific system prompt from a .md file at runtime
2. Sends the prompt + raw pentest data to Ollama via the official ``ollama``
   Python package
3. Parses the JSON response into a Python dict

There is no agent framework involved — just ``ollama.AsyncClient`` calls to a
standard Ollama instance running unchanged as a Docker container.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Any

from ollama import AsyncClient, ResponseError

logger = logging.getLogger("blhackbox.agents.base")

# Resolve prompts directory relative to this file
_PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts" / "agents"

# Configurable via environment — mirrors the server defaults.
_OLLAMA_TIMEOUT = float(os.getenv("OLLAMA_TIMEOUT", "300"))
_OLLAMA_NUM_CTX = int(os.getenv("OLLAMA_NUM_CTX", "8192"))
_OLLAMA_KEEP_ALIVE = os.getenv("OLLAMA_KEEP_ALIVE", "10m")
_OLLAMA_RETRIES = int(os.getenv("OLLAMA_RETRIES", "2"))


def _serialize_data(data: dict | str) -> str:
    """Convert data to a proper JSON string for Ollama.

    Dicts are serialised with ``json.dumps`` so that Ollama receives valid
    JSON instead of the Python repr that ``str()`` would produce.
    """
    if isinstance(data, str):
        return data
    return json.dumps(data, default=str)


class BaseAgent:
    """Abstract base for Ollama preprocessing agents.

    Subclasses are named IngestionAgent, ProcessingAgent, SynthesisAgent.
    The prompt file is determined by lowercasing the class name
    (e.g. ``IngestionAgent`` loads ``prompts/agents/ingestionagent.md``).
    """

    def __init__(
        self,
        ollama_host: str = "http://localhost:11434",
        model: str = "llama3.1:8b",
    ) -> None:
        self.ollama_host = ollama_host.rstrip("/")
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

        Retries transient failures with exponential backoff.  If Ollama is
        unreachable or returns invalid JSON after all attempts, returns an
        empty dict — the caller is responsible for degraded handling.
        """
        user_content = _serialize_data(data)

        for attempt in range(1 + _OLLAMA_RETRIES):
            try:
                client = AsyncClient(
                    host=self.ollama_host, timeout=_OLLAMA_TIMEOUT,
                )
                response = await client.chat(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": self.system_prompt},
                        {"role": "user", "content": user_content},
                    ],
                    format="json",
                    options={"num_ctx": _OLLAMA_NUM_CTX},
                    keep_alive=_OLLAMA_KEEP_ALIVE,
                )
                return self._parse(response)
            except ResponseError as exc:
                logger.warning(
                    "%s: Ollama error (attempt %d/%d): %s",
                    self.__class__.__name__, attempt + 1, 1 + _OLLAMA_RETRIES, exc,
                )
            except Exception as exc:
                logger.warning(
                    "%s: Ollama request failed (attempt %d/%d): %s",
                    self.__class__.__name__, attempt + 1, 1 + _OLLAMA_RETRIES, exc,
                )

            if attempt < _OLLAMA_RETRIES:
                await asyncio.sleep(2 ** attempt)

        logger.error(
            "%s: all %d attempts failed", self.__class__.__name__, 1 + _OLLAMA_RETRIES,
        )
        return {}

    def _parse(self, response: Any) -> dict[str, Any]:
        """Extract and parse the JSON content from Ollama's response."""
        content = response.message.content or ""

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
