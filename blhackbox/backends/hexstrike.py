"""HexStrike API backend – delegates tool execution to a remote HexStrike server."""

from __future__ import annotations

import logging
from typing import Any

from blhackbox.backends.base import ToolBackend, ToolResult
from blhackbox.clients.hexstrike_client import HexStrikeClient
from blhackbox.utils.catalog import load_tools_catalog

logger = logging.getLogger("blhackbox.backends.hexstrike")


class HexStrikeBackend(ToolBackend):
    """Execute tools via the HexStrike AI API."""

    name = "hexstrike"

    def __init__(self) -> None:
        self._client: HexStrikeClient | None = None

    async def connect(self) -> None:
        self._client = HexStrikeClient()
        await self._client.__aenter__()

    async def close(self) -> None:
        if self._client:
            await self._client.__aexit__(None, None, None)
            self._client = None

    async def health_check(self) -> bool:
        if not self._client:
            return False
        return await self._client.health_check()

    async def run_tool(
        self,
        category: str,
        tool: str,
        params: dict[str, Any] | None = None,
    ) -> ToolResult:
        assert self._client is not None

        # Route intelligence tools to the dedicated endpoint
        if category == "intelligence" and tool == "analyze-target":
            target = (params or {}).get("target", "")
            analysis = await self._client.analyze_target(
                target=target,
                analysis_type=(params or {}).get(
                    "analysis_type", "comprehensive"
                ),
            )
            import json

            return ToolResult(
                success=analysis.success,
                tool=f"{category}/{tool}",
                category=category,
                output=json.dumps(analysis.results, indent=2, default=str),
                errors=analysis.errors,
                raw_data={
                    "results": analysis.results,
                    "recommendations": analysis.recommendations,
                    "risk_score": analysis.risk_score,
                },
            )

        result = await self._client.run_tool(category, tool, params)
        return ToolResult(
            success=result.success,
            tool=f"{category}/{tool}",
            category=category,
            output=result.raw_output or str(result.output),
            errors=result.errors,
            execution_time=result.execution_time,
            raw_data={"output": result.output},
        )

    async def list_tools(self) -> list[dict[str, str]]:
        """Return tools from the local catalogue (the server doesn't list tools)."""
        try:
            catalog = load_tools_catalog()
            return [
                {"category": t["category"], "tool": t["tool_name"]}
                for t in catalog
            ]
        except Exception:
            return [{"category": "network", "tool": "nmap"}]
