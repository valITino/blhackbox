"""Async HTTP client for the HexStrike AI MCP Server."""

from __future__ import annotations

import logging
import re
from typing import Any
from urllib.parse import urlparse

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from blhackbox.config import Settings
from blhackbox.config import settings as default_settings
from blhackbox.exceptions import (
    HexStrikeAPIError,
    HexStrikeConnectionError,
    HexStrikeTimeoutError,
)
from blhackbox.models.hexstrike import (
    HexStrikeAgentInfo,
    HexStrikeAgentResponse,
    HexStrikeAnalysisResponse,
    HexStrikeToolResponse,
)

logger = logging.getLogger("blhackbox.clients.hexstrike")

# URL path segment validation to prevent SSRF and path traversal
_SAFE_PATH_SEGMENT = re.compile(r"^[a-zA-Z0-9_\-]+$")
_ALLOWED_SCHEMES = frozenset({"http", "https"})


def _validate_path_segment(value: str, context: str) -> str:
    """Validate that a value is safe for use in a URL path segment."""
    if not _SAFE_PATH_SEGMENT.match(value):
        raise ValueError(
            f"Invalid characters in {context}: {value!r}. "
            "Only alphanumeric characters, hyphens, and underscores are allowed."
        )
    return value


def _validate_base_url(url: str) -> str:
    """Validate that the base URL uses an allowed scheme and has a valid host."""
    parsed = urlparse(url)
    if parsed.scheme not in _ALLOWED_SCHEMES:
        raise ValueError(f"URL scheme must be http or https, got: {parsed.scheme!r}")
    if not parsed.hostname:
        raise ValueError(f"URL must have a valid hostname: {url!r}")
    return url.rstrip("/")


class HexStrikeClient:
    """Async client for interacting with the HexStrike AI API.

    Supports automatic retries with exponential backoff and configurable
    timeouts.  All public methods return typed Pydantic models.
    """

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or default_settings
        self._base_url = _validate_base_url(self._settings.hexstrike_url)
        self._client: httpx.AsyncClient | None = None

    # -- lifecycle -----------------------------------------------------------

    async def __aenter__(self) -> HexStrikeClient:
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            timeout=httpx.Timeout(self._settings.hexstrike_timeout, connect=10.0),
            headers={"Content-Type": "application/json", "User-Agent": "blhackbox/1.0.0"},
        )
        return self

    async def __aexit__(self, *exc: Any) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None:
            raise HexStrikeConnectionError(
                "Client not initialised. Use 'async with HexStrikeClient() as c:'"
            )
        return self._client

    # -- health --------------------------------------------------------------

    async def health_check(self) -> bool:
        """Return True if HexStrike is reachable."""
        try:
            resp = await self.client.get("/health")
            return resp.status_code == 200
        except httpx.HTTPError:
            return False

    # -- tools ---------------------------------------------------------------

    @retry(
        retry=retry_if_exception_type((httpx.TransportError, httpx.TimeoutException)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=16),
        reraise=True,
    )
    async def run_tool(
        self,
        category: str,
        tool: str,
        params: dict[str, Any] | None = None,
    ) -> HexStrikeToolResponse:
        """Execute a HexStrike tool.

        Args:
            category: Tool category (network, web, intelligence, etc.)
            tool: Tool name (nmap, nuclei, ffuf, etc.)
            params: Tool-specific parameters

        Returns:
            Typed response with output, errors, and execution time.
        """
        safe_category = _validate_path_segment(category, "tool category")
        safe_tool = _validate_path_segment(tool, "tool name")
        url = f"/api/tools/{safe_tool}"
        payload = params or {}
        logger.info("Running tool %s/%s with params: %s", safe_category, safe_tool, payload)

        try:
            resp = await self.client.post(url, json=payload)
        except httpx.TimeoutException as exc:
            raise HexStrikeTimeoutError(
                f"Timeout calling {category}/{tool} after {self._settings.hexstrike_timeout}s"
            ) from exc
        except httpx.TransportError as exc:
            raise HexStrikeConnectionError(f"Cannot reach HexStrike at {self._base_url}") from exc

        if resp.status_code >= 400:
            detail = resp.text[:500]
            raise HexStrikeAPIError(resp.status_code, detail)

        data = resp.json()
        return HexStrikeToolResponse(
            success=data.get("success", True),
            tool=tool,
            category=category,
            output=data.get("output", data.get("result")),
            raw_output=data.get("raw_output", ""),
            execution_time=data.get("execution_time"),
            errors=data.get("errors", []),
        )

    # -- intelligence --------------------------------------------------------

    @retry(
        retry=retry_if_exception_type((httpx.TransportError, httpx.TimeoutException)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=16),
        reraise=True,
    )
    async def analyze_target(
        self,
        target: str,
        analysis_type: str = "comprehensive",
    ) -> HexStrikeAnalysisResponse:
        """Request an AI-driven target analysis from HexStrike.

        Args:
            target: The target (domain, IP, URL).
            analysis_type: Analysis depth (comprehensive, quick, passive).
        """
        url = "/api/intelligence/analyze-target"
        payload = {"target": target, "analysis_type": analysis_type}
        logger.info("Analyzing target %s (type=%s)", target, analysis_type)

        try:
            resp = await self.client.post(url, json=payload)
        except httpx.TimeoutException as exc:
            raise HexStrikeTimeoutError(
                f"Timeout during analysis of {target}"
            ) from exc
        except httpx.TransportError as exc:
            raise HexStrikeConnectionError(f"Cannot reach HexStrike at {self._base_url}") from exc

        if resp.status_code >= 400:
            raise HexStrikeAPIError(resp.status_code, resp.text[:500])

        data = resp.json()
        return HexStrikeAnalysisResponse(
            success=data.get("success", True),
            target=target,
            analysis_type=analysis_type,
            results=data.get("results", {}),
            recommendations=data.get("recommendations", []),
            risk_score=data.get("risk_score"),
            errors=data.get("errors", []),
        )

    # -- agents --------------------------------------------------------------

    @retry(
        retry=retry_if_exception_type((httpx.TransportError, httpx.TimeoutException)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=16),
        reraise=True,
    )
    async def list_agents(self) -> list[HexStrikeAgentInfo]:
        """Retrieve the list of available HexStrike AI agents."""
        logger.info("Listing HexStrike agents")

        try:
            resp = await self.client.get("/api/agents/list")
        except httpx.TransportError as exc:
            raise HexStrikeConnectionError(f"Cannot reach HexStrike at {self._base_url}") from exc

        if resp.status_code >= 400:
            raise HexStrikeAPIError(resp.status_code, resp.text[:500])

        data = resp.json()
        agents_raw = data if isinstance(data, list) else data.get("agents", [])
        return [HexStrikeAgentInfo(**a) for a in agents_raw]

    @retry(
        retry=retry_if_exception_type((httpx.TransportError, httpx.TimeoutException)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=16),
        reraise=True,
    )
    async def run_agent(
        self,
        agent_name: str,
        target: str,
        params: dict[str, Any] | None = None,
    ) -> HexStrikeAgentResponse:
        """Invoke a HexStrike AI agent against a target.

        Args:
            agent_name: Agent identifier (e.g. "bug_bounty", "ctf").
            target: The scan target.
            params: Extra agent-specific parameters.
        """
        safe_agent = _validate_path_segment(agent_name, "agent name")
        url = f"/api/agents/{safe_agent}/run"
        payload: dict[str, Any] = {"target": target}
        if params:
            payload.update(params)
        logger.info("Running agent '%s' against %s", safe_agent, target)

        try:
            resp = await self.client.post(url, json=payload)
        except httpx.TimeoutException as exc:
            raise HexStrikeTimeoutError(
                f"Timeout running agent {agent_name} on {target}"
            ) from exc
        except httpx.TransportError as exc:
            raise HexStrikeConnectionError(f"Cannot reach HexStrike at {self._base_url}") from exc

        if resp.status_code >= 400:
            raise HexStrikeAPIError(resp.status_code, resp.text[:500])

        data = resp.json()
        return HexStrikeAgentResponse(
            success=data.get("success", True),
            agent=agent_name,
            target=target,
            results=data.get("results", {}),
            findings=data.get("findings", []),
            execution_time=data.get("execution_time"),
            errors=data.get("errors", []),
        )
