"""Base FastAPI agent server for blhackbox Ollama preprocessing agents.

Each agent subclass exposes POST /process that accepts raw data,
calls Ollama via the official ``ollama`` Python package, and
returns structured JSON.

These run as separate Docker containers, NOT inside the ollama-mcp server.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import uvicorn
from fastapi import FastAPI, HTTPException
from ollama import AsyncClient, ResponseError
from pydantic import BaseModel

logger = logging.getLogger("blhackbox.agent_server")

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://ollama:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1:8b")

# Timeout (seconds) for Ollama requests — generous to cover cold-start model
# loading, which can take minutes on first invocation.
OLLAMA_TIMEOUT = float(os.getenv("OLLAMA_TIMEOUT", "300"))

# Context window size — large pentest outputs need more than the default 2048.
OLLAMA_NUM_CTX = int(os.getenv("OLLAMA_NUM_CTX", "8192"))

# Keep the model in memory between sequential agent calls to avoid repeated
# cold-start loading.  Default: 10 minutes.
OLLAMA_KEEP_ALIVE = os.getenv("OLLAMA_KEEP_ALIVE", "10m")

# Number of retries for transient Ollama failures.
OLLAMA_RETRIES = int(os.getenv("OLLAMA_RETRIES", "2"))

# Prompt directory — resolved at container build time
_PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts" / "agents"


def _serialize_data(data: dict | str) -> str:
    """Convert request data to a proper JSON string for Ollama.

    If *data* is already a string it is returned as-is.  If it is a dict
    (the typical case for Processing / Synthesis agents), it is serialised
    with ``json.dumps`` so that Ollama receives valid JSON — **not** the
    Python repr that ``str()`` would produce.
    """
    if isinstance(data, str):
        return data
    return json.dumps(data, default=str)


class ProcessRequest(BaseModel):
    """Request body for the /process endpoint."""

    data: dict | str
    session_id: str = ""
    target: str = ""


class BaseAgentServer:
    """Create a FastAPI app for a named agent.

    The agent loads its system prompt from
    ``blhackbox/prompts/agents/<agent_name>.md`` and exposes:
      - GET  /health   — liveness check (also verifies Ollama reachability)
      - POST /process  — send data to Ollama and return structured JSON
    """

    def __init__(self, agent_name: str) -> None:
        self.agent_name = agent_name

        prompt_file = _PROMPTS_DIR / f"{agent_name.lower()}.md"
        if prompt_file.exists():
            self.system_prompt = prompt_file.read_text(encoding="utf-8")
        else:
            logger.warning("Prompt file not found: %s — using fallback", prompt_file)
            self.system_prompt = (
                f"You are a {agent_name} data processing agent. "
                "Respond only in valid JSON."
            )

        # Create FastAPI app with lifespan for model warmup
        self.app = FastAPI(
            title=f"blhackbox {agent_name} Agent",
            lifespan=self._lifespan,
        )

        # Register routes
        self._register_routes()

    @asynccontextmanager
    async def _lifespan(self, app: FastAPI):
        """Warm up Ollama model on startup to avoid cold-start 502s."""
        await self._warmup_model()
        yield

    async def _warmup_model(self) -> None:
        """Send a tiny request to Ollama to trigger model loading.

        This runs during FastAPI startup so the model is already in memory
        by the time the first real /process request arrives.
        """
        logger.info("Warming up Ollama model %s at %s …", OLLAMA_MODEL, OLLAMA_HOST)
        try:
            client = AsyncClient(host=OLLAMA_HOST, timeout=OLLAMA_TIMEOUT)
            await client.chat(
                model=OLLAMA_MODEL,
                messages=[{"role": "user", "content": "hello"}],
                keep_alive=OLLAMA_KEEP_ALIVE,
            )
            logger.info("Model %s is warm and ready", OLLAMA_MODEL)
        except Exception as exc:
            # Non-fatal — the model will load on first real request.
            logger.warning("Model warmup failed (will retry on first request): %s", exc)

    def _register_routes(self) -> None:
        app = self.app
        agent_name = self.agent_name
        system_prompt = self.system_prompt

        @app.get("/health")
        async def health() -> dict:
            """Liveness check — also verifies Ollama is reachable."""
            result: dict[str, Any] = {"status": "ok", "agent": agent_name}
            try:
                client = AsyncClient(host=OLLAMA_HOST, timeout=10.0)
                models = await client.list()
                result["ollama"] = "reachable"
                result["models_loaded"] = len(models.get("models", []))
            except Exception:
                result["ollama"] = "unreachable"
            return result

        @app.post("/process")
        async def process(req: ProcessRequest) -> dict:
            user_content = _serialize_data(req.data)

            for attempt in range(1 + OLLAMA_RETRIES):
                try:
                    client = AsyncClient(
                        host=OLLAMA_HOST, timeout=OLLAMA_TIMEOUT,
                    )
                    response = await client.chat(
                        model=OLLAMA_MODEL,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_content},
                        ],
                        format="json",
                        options={"num_ctx": OLLAMA_NUM_CTX},
                        keep_alive=OLLAMA_KEEP_ALIVE,
                    )
                    # Success — break out of retry loop
                    break
                except ResponseError as exc:
                    logger.warning(
                        "%s: Ollama ResponseError (attempt %d/%d): %s",
                        agent_name, attempt + 1, 1 + OLLAMA_RETRIES, exc,
                    )
                    if attempt < OLLAMA_RETRIES:
                        await asyncio.sleep(2 ** attempt)
                        continue
                    raise HTTPException(
                        status_code=502,
                        detail=f"Ollama error after {1 + OLLAMA_RETRIES} attempts: {exc}",
                    ) from exc
                except Exception as exc:
                    logger.warning(
                        "%s: Ollama request failed (attempt %d/%d): %s",
                        agent_name, attempt + 1, 1 + OLLAMA_RETRIES, exc,
                    )
                    if attempt < OLLAMA_RETRIES:
                        await asyncio.sleep(2 ** attempt)
                        continue
                    raise HTTPException(
                        status_code=503,
                        detail=(
                            f"Ollama unreachable at {OLLAMA_HOST} after "
                            f"{1 + OLLAMA_RETRIES} attempts: {exc}"
                        ),
                    ) from exc

            content = response.message.content or ""
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
