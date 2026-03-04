"""HexStrike MCP Adapter for blhackbox.

Bridges the HexStrike Flask REST API (http://hexstrike:8888) to the MCP
protocol so that Claude Code and other MCP clients can discover and invoke
HexStrike tools natively.

Transport: FastMCP SSE on port 9005.
"""

from __future__ import annotations

import json
import logging
import os

import httpx
from mcp.server.fastmcp import FastMCP

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("hexstrike-mcp")

HEXSTRIKE_URL = os.environ.get("HEXSTRIKE_URL", "http://hexstrike:8888")
MCP_PORT = int(os.environ.get("MCP_PORT", "9005"))
TOOL_TIMEOUT = int(os.environ.get("HEXSTRIKE_TIMEOUT", "300"))

mcp = FastMCP("hexstrike-mcp", host="0.0.0.0", port=MCP_PORT)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_client: httpx.AsyncClient | None = None


def _get_client() -> httpx.AsyncClient:
    global _client
    if _client is None:
        _client = httpx.AsyncClient(base_url=HEXSTRIKE_URL, timeout=TOOL_TIMEOUT)
    return _client


async def _hexstrike_health() -> dict:
    """Fetch HexStrike health status."""
    resp = await _get_client().get("/health")
    resp.raise_for_status()
    return resp.json()


# ---------------------------------------------------------------------------
# MCP Tools
# ---------------------------------------------------------------------------

@mcp.tool()
async def hexstrike_health() -> str:
    """Check HexStrike API health and list available tools.

    Returns the server version, total tool count, and per-tool availability.
    """
    try:
        data = await _hexstrike_health()
        return json.dumps(data, indent=2)
    except Exception as exc:
        return json.dumps({"error": str(exc)})


@mcp.tool()
async def hexstrike_list_tools(only_available: bool = True) -> str:
    """List all HexStrike tools and their availability status.

    Args:
        only_available: If True, only return tools that are installed and usable.
    """
    try:
        data = await _hexstrike_health()
        tools_status = data.get("tools_status", {})
        if only_available:
            tools_status = {k: v for k, v in tools_status.items() if v}
        return json.dumps({
            "tools": tools_status,
            "count": len(tools_status),
            "total": data.get("total_tools_count", 0),
        }, indent=2)
    except Exception as exc:
        return json.dumps({"error": str(exc)})


@mcp.tool()
async def hexstrike_run_tool(
    tool: str,
    args: str = "",
    target: str = "",
    timeout: int = 300,
) -> str:
    """Execute a HexStrike security tool via the REST API.

    Args:
        tool: Tool name (e.g. 'httpx', 'strings', 'checksec', 'angr', 'objdump').
        args: Arguments to pass to the tool as a string.
        target: Target URL, IP, or file path for the tool.
        timeout: Execution timeout in seconds (default 300).
    """
    client = _get_client()
    payload = {
        "tool": tool,
        "args": args,
        "target": target,
    }

    # Try known HexStrike API endpoints
    endpoints = [
        "/api/tools/run",
        "/api/run",
        f"/api/tools/{tool}/run",
    ]

    last_error = ""
    for endpoint in endpoints:
        try:
            resp = await client.post(
                endpoint,
                json=payload,
                timeout=timeout,
            )
            if resp.status_code == 404:
                last_error = f"{endpoint} returned 404"
                continue
            resp.raise_for_status()
            return json.dumps(resp.json(), indent=2)
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                last_error = f"{endpoint} returned 404"
                continue
            return json.dumps({"error": str(exc), "endpoint": endpoint})
        except Exception as exc:
            last_error = str(exc)
            continue

    return json.dumps({
        "error": f"Could not find a working HexStrike API endpoint. Last error: {last_error}",
        "tried_endpoints": endpoints,
        "hint": "HexStrike REST API routes may need to be configured. Check HexStrike documentation.",
    })


@mcp.tool()
async def hexstrike_run_agent(
    agent: str,
    target: str,
    options: str = "{}",
    timeout: int = 600,
) -> str:
    """Execute a HexStrike AI agent for automated security analysis.

    Args:
        agent: Agent name (e.g. 'recon', 'vuln_scan', 'exploit').
        target: Target URL, IP, or domain for the agent.
        options: JSON string of additional agent options.
        timeout: Execution timeout in seconds (default 600).
    """
    client = _get_client()

    try:
        opts = json.loads(options) if options else {}
    except json.JSONDecodeError:
        return json.dumps({"error": f"Invalid JSON in options: {options}"})

    payload = {
        "agent": agent,
        "target": target,
        "options": opts,
    }

    endpoints = [
        "/api/agents/run",
        f"/api/agents/{agent}/run",
        "/api/run_agent",
    ]

    last_error = ""
    for endpoint in endpoints:
        try:
            resp = await client.post(
                endpoint,
                json=payload,
                timeout=timeout,
            )
            if resp.status_code == 404:
                last_error = f"{endpoint} returned 404"
                continue
            resp.raise_for_status()
            return json.dumps(resp.json(), indent=2)
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                last_error = f"{endpoint} returned 404"
                continue
            return json.dumps({"error": str(exc), "endpoint": endpoint})
        except Exception as exc:
            last_error = str(exc)
            continue

    return json.dumps({
        "error": f"Could not find a working HexStrike agent endpoint. Last error: {last_error}",
        "tried_endpoints": endpoints,
        "hint": "HexStrike agent API routes may need to be configured.",
    })


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    transport = os.environ.get("MCP_TRANSPORT", "sse")
    logger.info(
        "Starting HexStrike MCP Adapter (%s on port %d, backend: %s)",
        transport, MCP_PORT, HEXSTRIKE_URL,
    )
    mcp.run(transport=transport)
