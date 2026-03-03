"""HexStrike AI MCP Server for blhackbox.

Thin MCP adapter over the HexStrike AI REST API (Flask on port 8888).
Translates MCP tool calls into HTTP requests so that Claude Code and
other MCP clients can discover and invoke HexStrike natively — just
like Kali MCP, Metasploit MCP, WireMCP, and Screenshot MCP.

Source API: https://github.com/0x4m4/hexstrike-ai

Tools:
  - health_check     → Server status, tool availability, telemetry
  - list_tools       → Available tools with category and status
  - run_tool         → Execute a specific security tool against a target
  - list_agents      → Available AI security agents
  - run_agent        → Invoke an AI agent against a target
  - analyze_target   → AI-driven target analysis and risk scoring

Transport: FastMCP SSE on port 9005 (Docker), or stdio for local use.
"""

from __future__ import annotations

import json
import logging
import os
import re
from typing import Any

import httpx
from mcp.server.fastmcp import FastMCP

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)
logger = logging.getLogger("hexstrike-mcp")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

HEXSTRIKE_URL = os.environ.get("HEXSTRIKE_URL", "http://hexstrike:8888").rstrip("/")
HEXSTRIKE_TIMEOUT = int(os.environ.get("HEXSTRIKE_TIMEOUT", "300"))
MCP_PORT = int(os.environ.get("HEXSTRIKE_MCP_PORT", "9005"))

# URL path segment validation to prevent SSRF and path traversal
_SAFE_PATH_SEGMENT = re.compile(r"^[a-zA-Z0-9_\-]+$")


def _validate_segment(value: str, context: str) -> str:
    """Validate a URL path segment contains only safe characters."""
    if not _SAFE_PATH_SEGMENT.match(value):
        raise ValueError(
            f"Invalid characters in {context}: {value!r}. "
            "Only alphanumeric characters, hyphens, and underscores are allowed."
        )
    return value


# ---------------------------------------------------------------------------
# HTTP client helpers
# ---------------------------------------------------------------------------

_http_client: httpx.AsyncClient | None = None


async def _get_client() -> httpx.AsyncClient:
    """Return a shared async HTTP client, creating it lazily."""
    global _http_client
    if _http_client is None or _http_client.is_closed:
        _http_client = httpx.AsyncClient(
            base_url=HEXSTRIKE_URL,
            timeout=httpx.Timeout(HEXSTRIKE_TIMEOUT, connect=10.0),
            headers={
                "Content-Type": "application/json",
                "User-Agent": "blhackbox-hexstrike-mcp/1.0.0",
            },
        )
        logger.info("HTTP client initialised for %s", HEXSTRIKE_URL)
    return _http_client


async def _api_get(path: str) -> dict[str, Any]:
    """Perform a GET request to HexStrike and return parsed JSON."""
    client = await _get_client()
    try:
        resp = await client.get(path)
        resp.raise_for_status()
        return resp.json()
    except httpx.TimeoutException:
        return {"error": f"Timeout after {HEXSTRIKE_TIMEOUT}s calling GET {path}"}
    except httpx.HTTPStatusError as exc:
        return {
            "error": f"HTTP {exc.response.status_code} from GET {path}",
            "detail": exc.response.text[:500],
        }
    except httpx.TransportError as exc:
        return {"error": f"Connection error calling GET {path}: {exc}"}
    except Exception as exc:
        return {"error": f"Unexpected error calling GET {path}: {exc}"}


async def _api_post(path: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Perform a POST request to HexStrike and return parsed JSON."""
    client = await _get_client()
    try:
        resp = await client.post(path, json=payload)
        resp.raise_for_status()
        return resp.json()
    except httpx.TimeoutException:
        return {"error": f"Timeout after {HEXSTRIKE_TIMEOUT}s calling POST {path}"}
    except httpx.HTTPStatusError as exc:
        return {
            "error": f"HTTP {exc.response.status_code} from POST {path}",
            "detail": exc.response.text[:500],
        }
    except httpx.TransportError as exc:
        return {"error": f"Connection error calling POST {path}: {exc}"}
    except Exception as exc:
        return {"error": f"Unexpected error calling POST {path}: {exc}"}


# ---------------------------------------------------------------------------
# MCP Server
# ---------------------------------------------------------------------------

mcp = FastMCP(
    "hexstrike-mcp",
    host="0.0.0.0",
    port=MCP_PORT,
    instructions=(
        "HexStrike AI MCP Server — provides access to 150+ security tools "
        "and 12+ AI agents via the HexStrike REST API. Execute individual "
        "tools (nmap, httpx, nuclei, etc.), run AI-driven agents (bug bounty, "
        "CTF, recon, web app assessment), or perform comprehensive target "
        "analysis with risk scoring."
    ),
)


# ---------------------------------------------------------------------------
# Health check endpoint (for Docker healthcheck / readiness probes)
# ---------------------------------------------------------------------------


@mcp.custom_route("/health", methods=["GET"])
async def mcp_health_check(request):
    """Lightweight health probe for Docker and Makefile checks."""
    from starlette.responses import JSONResponse

    # Check if we can reach HexStrike
    client = await _get_client()
    hexstrike_ok = False
    try:
        resp = await client.get("/health", timeout=5.0)
        hexstrike_ok = resp.status_code == 200
    except Exception:
        pass

    return JSONResponse({
        "status": "healthy",
        "service": "hexstrike-mcp",
        "port": MCP_PORT,
        "hexstrike_url": HEXSTRIKE_URL,
        "hexstrike_reachable": hexstrike_ok,
    })


# ---------------------------------------------------------------------------
# MCP Tools
# ---------------------------------------------------------------------------


@mcp.tool()
async def health_check() -> str:
    """Check HexStrike server status, tool availability, and telemetry.

    Returns:
        JSON with server version, available tools count, categories,
        and deployment status.
    """
    data = await _api_get("/health")
    return json.dumps(data, indent=2, default=str)


@mcp.tool()
async def list_tools() -> str:
    """List all available security tools on this HexStrike instance.

    Returns tools grouped by category (web_security, network, binary,
    forensics, osint, exploitation, etc.) with availability status.

    Returns:
        JSON with tool categories and individual tool availability.
    """
    data = await _api_get("/health")
    if "error" in data:
        return json.dumps(data, indent=2)

    # Extract tool information from the health endpoint
    tools_info = data.get("tools", {})
    categories = data.get("categories", {})
    total = data.get("total_tools", 0)
    available = data.get("available_tools", 0)

    # Also try the dedicated tools listing endpoint
    tools_list = await _api_get("/api/tools")
    if "error" not in tools_list:
        tools_info = tools_list.get("tools", tools_info)

    result = {
        "total_tools": total,
        "available_tools": available,
        "categories": categories,
        "tools": tools_info,
    }
    return json.dumps(result, indent=2, default=str)


@mcp.tool()
async def run_tool(
    tool: str,
    target: str,
    options: str = "{}",
) -> str:
    """Execute a specific security tool against a target.

    Runs one of HexStrike's 150+ security tool wrappers. The tool runs
    server-side inside the HexStrike container and returns structured output.

    Args:
        tool: Tool name (e.g. httpx, nmap, nuclei, subfinder, ffuf, sqlmap,
              angr, checksec, objdump, strings, nikto, gobuster, etc.)
        target: Target domain, IP address, URL, or file path
        options: JSON string of additional tool-specific options
                 (e.g. '{"flags": ["-F", "-sV"], "ports": "1-1000"}')

    Returns:
        JSON with tool output, execution time, and any errors.
    """
    safe_tool = _validate_segment(tool, "tool name")

    try:
        extra_opts = json.loads(options) if options else {}
    except json.JSONDecodeError:
        return json.dumps({"error": f"Invalid options JSON: {options}"})

    payload: dict[str, Any] = {"target": target}
    payload.update(extra_opts)

    logger.info("Running tool '%s' against %s", safe_tool, target)
    data = await _api_post(f"/api/tools/{safe_tool}", payload)

    # Normalise the response
    result = {
        "tool": safe_tool,
        "target": target,
        "success": data.get("success", "error" not in data),
        "output": data.get("output") or data.get("result") or data.get("stdout"),
        "raw_output": data.get("raw_output") or data.get("stdout", ""),
        "execution_time": data.get("execution_time"),
        "errors": data.get("errors", []),
    }

    if "error" in data:
        result["success"] = False
        result["errors"] = [data["error"]]
        if "detail" in data:
            result["errors"].append(data["detail"])

    if data.get("stderr"):
        result.setdefault("errors", [])
        if data["stderr"] not in result["errors"]:
            result["errors"].append(data["stderr"])

    return json.dumps(result, indent=2, default=str)


@mcp.tool()
async def list_agents() -> str:
    """List available HexStrike AI security agents.

    Returns the set of AI-driven agents that can orchestrate multiple tools
    for specific assessment types (bug bounty, CTF, recon, web app, etc.).

    Returns:
        JSON array of agents with name, description, capabilities, and status.
    """
    data = await _api_get("/api/agents/list")
    if "error" in data:
        return json.dumps(data, indent=2)

    agents = data if isinstance(data, list) else data.get("agents", [])
    return json.dumps({"agents": agents}, indent=2, default=str)


@mcp.tool()
async def run_agent(
    agent: str,
    target: str,
    options: str = "{}",
) -> str:
    """Invoke a HexStrike AI agent against a target.

    AI agents orchestrate multiple security tools to perform comprehensive
    assessments. Each agent specialises in a different assessment type.

    Args:
        agent: Agent name (e.g. bug_bounty, ctf, recon, web_app, network,
               osint, vuln_assessment, api_security, cloud_security,
               social_engineering, wireless, red_team)
        target: Target domain, IP, URL, or scope definition
        options: JSON string of additional agent-specific options
                 (e.g. '{"scope": "*.example.com", "intensity": "aggressive"}')

    Returns:
        JSON with agent results, findings, and execution metadata.
    """
    safe_agent = _validate_segment(agent, "agent name")

    try:
        extra_opts = json.loads(options) if options else {}
    except json.JSONDecodeError:
        return json.dumps({"error": f"Invalid options JSON: {options}"})

    payload: dict[str, Any] = {"target": target}
    payload.update(extra_opts)

    logger.info("Running agent '%s' against %s", safe_agent, target)
    data = await _api_post(f"/api/agents/{safe_agent}/run", payload)

    result = {
        "agent": safe_agent,
        "target": target,
        "success": data.get("success", "error" not in data),
        "results": data.get("results", {}),
        "findings": data.get("findings", []),
        "execution_time": data.get("execution_time"),
        "errors": data.get("errors", []),
    }

    if "error" in data:
        result["success"] = False
        result["errors"] = [data["error"]]

    return json.dumps(result, indent=2, default=str)


@mcp.tool()
async def analyze_target(
    target: str,
    analysis_type: str = "comprehensive",
) -> str:
    """Run AI-driven target analysis with risk scoring.

    Performs an intelligent analysis of a target using HexStrike's AI
    pipeline. Combines OSINT, fingerprinting, and vulnerability correlation
    to produce a risk assessment with actionable recommendations.

    Args:
        target: Target domain, IP address, or URL
        analysis_type: Analysis depth — one of:
            - comprehensive: Full analysis with all available tools
            - quick: Fast surface-level assessment
            - passive: OSINT-only, no active scanning

    Returns:
        JSON with analysis results, risk score, and recommendations.
    """
    payload = {"target": target, "analysis_type": analysis_type}
    logger.info("Analyzing target %s (type=%s)", target, analysis_type)

    data = await _api_post("/api/intelligence/analyze-target", payload)

    # Normalise the response
    profile = data.get("target_profile", {})
    results = data.get("results") or profile

    risk_score = (
        data.get("risk_score")
        or profile.get("risk_level")
        or profile.get("confidence_score")
    )

    result = {
        "target": target,
        "analysis_type": analysis_type,
        "success": data.get("success", "error" not in data),
        "results": results,
        "recommendations": data.get("recommendations", []),
        "risk_score": risk_score,
        "errors": data.get("errors", []),
    }

    if "error" in data:
        result["success"] = False
        result["errors"] = [data["error"]]

    return json.dumps(result, indent=2, default=str)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    transport = os.environ.get("MCP_TRANSPORT", "sse")
    logger.info(
        "Starting HexStrike MCP server (%s on port %d, backend: %s)",
        transport,
        MCP_PORT,
        HEXSTRIKE_URL,
    )
    mcp.run(transport=transport)
