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

# Model fallback chain — if the primary model fails (e.g. OOM), try these
# in order. Set via OLLAMA_FALLBACK_MODELS (comma-separated).
_DEFAULT_FALLBACKS = "llama3.1:8b,mistral:7b,phi3:mini,tinyllama"
OLLAMA_FALLBACK_MODELS = [
    m.strip()
    for m in os.getenv("OLLAMA_FALLBACK_MODELS", _DEFAULT_FALLBACKS).split(",")
    if m.strip()
]

# Timeout (seconds) for Ollama requests — generous to cover cold-start model
# loading, which can take minutes on first invocation.
OLLAMA_TIMEOUT = float(os.getenv("OLLAMA_TIMEOUT", "300"))

# Context window size — large pentest outputs need more than the default 2048.
OLLAMA_NUM_CTX = int(os.getenv("OLLAMA_NUM_CTX", "8192"))

# Keep the model in memory between sequential agent calls to avoid repeated
# cold-start loading.  Default: 10 minutes.
OLLAMA_KEEP_ALIVE = os.getenv("OLLAMA_KEEP_ALIVE", "30m")

# Number of retries for transient Ollama failures.
OLLAMA_RETRIES = int(os.getenv("OLLAMA_RETRIES", "2"))

# Prompt directory — resolved at container build time
_PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts" / "agents"


def _get_available_ram_gb() -> float:
    """Return available system RAM in GiB, or -1 if unknown."""
    try:
        import psutil
        return psutil.virtual_memory().available / (1024 ** 3)
    except ImportError:
        pass
    # Fallback: read /proc/meminfo on Linux
    try:
        with open("/proc/meminfo") as f:
            for line in f:
                if line.startswith("MemAvailable:"):
                    kb = int(line.split()[1])
                    return kb / (1024 ** 2)
    except (OSError, ValueError):
        pass
    return -1.0


# Rough RAM requirements per model (GiB).  Used for pre-flight check.
_MODEL_RAM_REQUIREMENTS = {
    "llama3.3": 41.5,
    "llama3.1:70b": 41.5,
    "llama3.1:8b": 5.5,
    "llama3.2": 5.5,
    "mistral:7b": 5.5,
    "phi3:mini": 3.0,
    "phi3:medium": 8.5,
    "tinyllama": 1.5,
    "qwen2:7b": 5.5,
}


def _select_model(requested: str) -> str:
    """Select the best model that fits in available RAM.

    If the requested model fits, use it. Otherwise, walk the fallback chain
    and pick the first model that fits. If nothing fits, return the
    smallest fallback (best-effort).
    """
    avail_ram = _get_available_ram_gb()
    if avail_ram < 0:
        logger.info("Cannot determine available RAM — using requested model %s", requested)
        return requested

    logger.info("Available RAM: %.1f GiB", avail_ram)

    # Check if requested model fits
    req_ram = _MODEL_RAM_REQUIREMENTS.get(requested, 0)
    if req_ram == 0 or req_ram <= avail_ram:
        logger.info("Model %s (%.1f GiB) fits in available RAM", requested, req_ram)
        return requested

    logger.warning(
        "Model %s requires %.1f GiB but only %.1f GiB available — checking fallbacks",
        requested, req_ram, avail_ram,
    )

    # Try fallback chain
    for fallback in OLLAMA_FALLBACK_MODELS:
        fb_ram = _MODEL_RAM_REQUIREMENTS.get(fallback, 0)
        if fb_ram == 0 or fb_ram <= avail_ram:
            logger.info(
                "Selected fallback model %s (%.1f GiB) — fits in %.1f GiB RAM",
                fallback, fb_ram, avail_ram,
            )
            return fallback

    # Nothing fits — use smallest fallback as best-effort
    smallest = OLLAMA_FALLBACK_MODELS[-1] if OLLAMA_FALLBACK_MODELS else requested
    logger.warning(
        "No model fits in %.1f GiB RAM — using %s as best-effort fallback",
        avail_ram, smallest,
    )
    return smallest


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

        # Select model based on available RAM
        self.model = _select_model(OLLAMA_MODEL)
        if self.model != OLLAMA_MODEL:
            logger.warning(
                "Model override: %s -> %s (RAM constraint)",
                OLLAMA_MODEL, self.model,
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
        logger.info("Warming up Ollama model %s at %s …", self.model, OLLAMA_HOST)
        try:
            client = AsyncClient(host=OLLAMA_HOST, timeout=OLLAMA_TIMEOUT)
            await client.chat(
                model=self.model,
                messages=[{"role": "user", "content": "hello"}],
                keep_alive=OLLAMA_KEEP_ALIVE,
            )
            logger.info("Model %s is warm and ready", self.model)
        except ResponseError as exc:
            # Check if it's an OOM error — try a smaller model
            err_msg = str(exc).lower()
            if "memory" in err_msg or "oom" in err_msg:
                logger.warning(
                    "Model %s OOM during warmup: %s — trying fallbacks",
                    self.model, exc,
                )
                for fallback in OLLAMA_FALLBACK_MODELS:
                    if fallback == self.model:
                        continue
                    try:
                        await client.chat(
                            model=fallback,
                            messages=[{"role": "user", "content": "hello"}],
                            keep_alive=OLLAMA_KEEP_ALIVE,
                        )
                        logger.info("Fallback model %s loaded successfully", fallback)
                        self.model = fallback
                        return
                    except Exception:
                        continue
                logger.error("All model fallbacks failed during warmup")
            else:
                logger.warning("Model warmup failed (will retry on first request): %s", exc)
        except Exception as exc:
            logger.warning("Model warmup failed (will retry on first request): %s", exc)

    def _register_routes(self) -> None:
        app = self.app
        agent_name = self.agent_name
        system_prompt = self.system_prompt

        # Store reference to self for model access in closures
        agent_server = self

        @app.get("/health")
        async def health() -> dict:
            """Liveness check — also verifies Ollama is reachable."""
            result: dict[str, Any] = {
                "status": "ok",
                "agent": agent_name,
                "model": agent_server.model,
                "available_ram_gb": round(_get_available_ram_gb(), 1),
            }
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
                        model=agent_server.model,
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
                    err_msg = str(exc).lower()
                    # Handle OOM by trying fallback models
                    if "memory" in err_msg or "oom" in err_msg:
                        logger.warning(
                            "%s: Model %s OOM — trying fallback models",
                            agent_name, agent_server.model,
                        )
                        fallback_success = False
                        for fallback in OLLAMA_FALLBACK_MODELS:
                            if fallback == agent_server.model:
                                continue
                            try:
                                response = await client.chat(
                                    model=fallback,
                                    messages=[
                                        {"role": "system", "content": system_prompt},
                                        {"role": "user", "content": user_content},
                                    ],
                                    format="json",
                                    options={"num_ctx": OLLAMA_NUM_CTX},
                                    keep_alive=OLLAMA_KEEP_ALIVE,
                                )
                                agent_server.model = fallback
                                logger.info(
                                    "%s: Switched to fallback model %s",
                                    agent_name, fallback,
                                )
                                fallback_success = True
                                break
                            except Exception:
                                continue
                        if fallback_success:
                            break
                        raise HTTPException(
                            status_code=502,
                            detail=(
                                f"Ollama OOM: model {agent_server.model} requires more RAM "
                                f"than available ({_get_available_ram_gb():.1f} GiB). "
                                f"All fallback models also failed. "
                                f"Set OLLAMA_MODEL to a smaller model or add more RAM."
                            ),
                        ) from exc

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
                logger.warning(
                    "%s: Ollama returned empty content for model %s",
                    agent_name, agent_server.model,
                )
                raise HTTPException(
                    status_code=502,
                    detail=(
                        f"{agent_name} received empty response from Ollama "
                        f"(model: {agent_server.model}). The model may have "
                        f"failed to generate output for the given input size."
                    ),
                )

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
    logger.info("Starting %s agent on port %d (model: %s)", agent_name, port, server.model)
    uvicorn.run(server.app, host="0.0.0.0", port=port)
