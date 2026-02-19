"""Base FastAPI agent server for blhackbox Ollama preprocessing agents.

Each agent subclass exposes POST /process that accepts raw data,
calls Ollama /api/chat with a task-specific system prompt, and
returns structured JSON.

These run as separate Docker containers, NOT inside the ollama-mcp server.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path

import httpx
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

logger = logging.getLogger("blhackbox.agent_server")

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://ollama:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.3")

# Prompt directory — resolved at container build time
_PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts" / "agents"


class ProcessRequest(BaseModel):
    """Request body for the /process endpoint."""

    data: dict | str
    session_id: str = ""
    target: str = ""


class BaseAgentServer:
    """Create a FastAPI app for a named agent.

    The agent loads its system prompt from
    ``blhackbox/prompts/agents/<agent_name>.md`` and exposes:
      - GET  /health   — lightweight liveness check (does NOT call Ollama)
      - POST /process  — send data to Ollama and return structured JSON
    """

    def __init__(self, agent_name: str) -> None:
        self.agent_name = agent_name
        self.app = FastAPI(title=f"blhackbox {agent_name} Agent")

        prompt_file = _PROMPTS_DIR / f"{agent_name.lower()}.md"
        if prompt_file.exists():
            self.system_prompt = prompt_file.read_text(encoding="utf-8")
        else:
            logger.warning("Prompt file not found: %s — using fallback", prompt_file)
            self.system_prompt = (
                f"You are a {agent_name} data processing agent. "
                "Respond only in valid JSON."
            )

        # Register routes
        self._register_routes()

    def _register_routes(self) -> None:
        app = self.app
        agent_name = self.agent_name
        system_prompt = self.system_prompt

        @app.get("/health")
        async def health() -> dict:
            return {"status": "ok", "agent": agent_name}

        @app.post("/process")
        async def process(req: ProcessRequest) -> dict:
            try:
                async with httpx.AsyncClient(timeout=180.0) as client:
                    response = await client.post(
                        f"{OLLAMA_URL}/api/chat",
                        json={
                            "model": OLLAMA_MODEL,
                            "messages": [
                                {"role": "system", "content": system_prompt},
                                {"role": "user", "content": str(req.data)},
                            ],
                            "stream": False,
                            "format": "json",
                        },
                    )
                    response.raise_for_status()
            except httpx.ConnectError as exc:
                raise HTTPException(
                    status_code=503,
                    detail=f"Ollama unreachable at {OLLAMA_URL}",
                ) from exc
            except httpx.HTTPStatusError as exc:
                raise HTTPException(
                    status_code=502,
                    detail=f"Ollama returned {exc.response.status_code}",
                ) from exc

            content = response.json().get("message", {}).get("content", "")
            if not content:
                return {}

            try:
                return json.loads(content)
            except json.JSONDecodeError:
                # Try to extract JSON from preamble text
                text = content.strip()
                start = text.find("{")
                end = text.rfind("}") + 1
                if start >= 0 and end > start:
                    try:
                        return json.loads(text[start:end])
                    except json.JSONDecodeError:
                        pass
                raise HTTPException(
                    status_code=500,
                    detail=f"Agent returned invalid JSON: {text[:200]}",
                ) from None


def run_agent(agent_name: str, port: int) -> None:
    """Entry point to start an agent server."""
    server = BaseAgentServer(agent_name)
    logging.basicConfig(level=logging.INFO)
    logger.info("Starting %s agent on port %d", agent_name, port)
    uvicorn.run(server.app, host="0.0.0.0", port=port)
