"""MCP server for Blhackbox.

Exposes high-level pentesting capabilities (not individual tools) so that
any MCP-compatible LLM can drive autonomous reconnaissance, query the
knowledge graph, and generate reports.

Unlike HexStrike's MCP (which exposes ~98 individual tool endpoints),
Blhackbox MCP provides *orchestrated workflows*:
  - recon           → autonomous multi-tool reconnaissance
  - run_tool        → execute a single tool via best available backend
  - query_graph     → Cypher queries against the knowledge graph
  - get_findings    → retrieve structured findings for a target
  - list_tools      → discover available tools across all backends
  - generate_report → produce HTML/PDF reports from session data
"""

from __future__ import annotations

import json
import logging
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from blhackbox.backends import ToolBackend, get_backend

logger = logging.getLogger("blhackbox.mcp.server")

_server = Server("blhackbox")

# Lazily initialised backend and knowledge graph client
_backend: ToolBackend | None = None


async def _get_backend() -> ToolBackend:
    global _backend
    if _backend is None:
        _backend = await get_backend()
    return _backend


# ---------------------------------------------------------------------------
# Tool definitions
# ---------------------------------------------------------------------------

_TOOLS: list[Tool] = [
    Tool(
        name="recon",
        description=(
            "Run multi-tool reconnaissance against a target. "
            "Executes tools via HexStrike, stores results in the knowledge "
            "graph, and returns structured findings."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "target": {
                    "type": "string",
                    "description": "Target domain, IP address, or URL",
                },
                "max_iterations": {
                    "type": "integer",
                    "description": "Maximum planning iterations (default 10)",
                    "default": 10,
                },
            },
            "required": ["target"],
        },
    ),
    Tool(
        name="run_tool",
        description=(
            "Execute a single security tool (e.g. nmap, subfinder, nuclei). "
            "Automatically selects the best backend (HexStrike API or local CLI)."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "description": "Tool category: network, web, dns, intelligence",
                },
                "tool": {
                    "type": "string",
                    "description": "Tool name: nmap, subfinder, nuclei, httpx, etc.",
                },
                "params": {
                    "type": "object",
                    "description": "Tool parameters (must include 'target')",
                },
            },
            "required": ["category", "tool", "params"],
        },
    ),
    Tool(
        name="query_graph",
        description=(
            "Execute a Cypher query against the Neo4j knowledge graph. "
            "Use this to explore the attack surface, find relationships "
            "between targets, and correlate findings across tools."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "cypher": {
                    "type": "string",
                    "description": "Cypher query to execute",
                },
            },
            "required": ["cypher"],
        },
    ),
    Tool(
        name="get_findings",
        description=(
            "Retrieve all security findings for a target from the knowledge "
            "graph. Returns structured data including severity, tool source, "
            "and descriptions."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "target": {
                    "type": "string",
                    "description": "Target to retrieve findings for",
                },
            },
            "required": ["target"],
        },
    ),
    Tool(
        name="list_tools",
        description=(
            "List all available security tools across all backends. "
            "Shows which tools can be executed and on which backend."
        ),
        inputSchema={
            "type": "object",
            "properties": {},
        },
    ),
    Tool(
        name="generate_report",
        description=(
            "Generate a professional pentest report (HTML) from a session. "
            "Returns the report file path."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "session_id": {
                    "type": "string",
                    "description": "Session ID or path to session JSON file",
                },
                "format": {
                    "type": "string",
                    "enum": ["html", "pdf"],
                    "description": "Report format (default: html)",
                    "default": "html",
                },
            },
            "required": ["session_id"],
        },
    ),
]


@_server.list_tools()
async def handle_list_tools() -> list[Tool]:
    return _TOOLS


@_server.call_tool()
async def handle_call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    try:
        result = await _dispatch(name, arguments)
        return [TextContent(type="text", text=result)]
    except Exception as exc:
        logger.exception("MCP tool %s failed", name)
        return [TextContent(type="text", text=f"Error: {exc}")]


# ---------------------------------------------------------------------------
# Dispatch
# ---------------------------------------------------------------------------


async def _dispatch(name: str, args: dict[str, Any]) -> str:
    if name == "recon":
        return await _do_recon(args)
    elif name == "run_tool":
        return await _do_run_tool(args)
    elif name == "query_graph":
        return await _do_query_graph(args)
    elif name == "get_findings":
        return await _do_get_findings(args)
    elif name == "list_tools":
        return await _do_list_tools()
    elif name == "generate_report":
        return await _do_generate_report(args)
    else:
        return f"Unknown tool: {name}"


async def _do_recon(args: dict[str, Any]) -> str:
    from blhackbox.clients.hexstrike_client import HexStrikeClient
    from blhackbox.core.runner import ReconRunner

    target = args["target"]
    async with HexStrikeClient() as client:
        runner = ReconRunner(client)
        session = await runner.run_recon(target)

    summary = {
        "session_id": session.id,
        "target": session.target.value,
        "tools_executed": session.tools_executed,
        "findings_count": len(session.findings),
        "severity_counts": session.severity_counts,
        "duration_seconds": session.duration_seconds,
        "findings": [
            {
                "title": f.title,
                "severity": f.severity.value if hasattr(f.severity, "value") else f.severity,
                "tool": f.tool,
                "description": f.description[:500] if f.description else "",
            }
            for f in session.findings[:20]
        ],
    }
    return json.dumps(summary, indent=2, default=str)


async def _do_run_tool(args: dict[str, Any]) -> str:
    backend = await _get_backend()
    result = await backend.run_tool(
        category=args["category"],
        tool=args["tool"],
        params=args.get("params"),
    )
    return json.dumps(result.model_dump(), indent=2, default=str)


async def _do_query_graph(args: dict[str, Any]) -> str:
    from blhackbox.core.knowledge_graph import KnowledgeGraphClient

    cypher = args["cypher"]
    async with KnowledgeGraphClient() as kg:
        records = await kg.run_query(cypher)
    return json.dumps(records, indent=2, default=str)


async def _do_get_findings(args: dict[str, Any]) -> str:
    from blhackbox.core.knowledge_graph import KnowledgeGraphClient

    target = args["target"]
    async with KnowledgeGraphClient() as kg:
        findings = await kg.get_findings_for_target(target)
        summary = await kg.get_target_summary(target)
    return json.dumps(
        {"target": target, "graph_summary": summary, "findings": findings},
        indent=2,
        default=str,
    )


async def _do_list_tools() -> str:
    backend = await _get_backend()
    tools = await backend.list_tools()
    return json.dumps(
        {"backend": backend.name, "tools": tools},
        indent=2,
    )


async def _do_generate_report(args: dict[str, Any]) -> str:
    import re
    from pathlib import Path

    from blhackbox.config import settings
    from blhackbox.models.base import ScanSession

    session_id = args["session_id"]
    fmt = args.get("format", "html")

    safe_id = re.sub(r"[^a-zA-Z0-9_\-]", "", session_id)
    if not safe_id:
        return json.dumps({"error": "Invalid session ID"})

    session_path = Path(session_id)
    if not session_path.exists():
        results_dir = settings.results_dir
        matches = list(results_dir.glob(f"*{safe_id}*"))
        if not matches:
            return json.dumps({"error": f"Session '{safe_id}' not found"})
        session_path = matches[0]

    session_data = ScanSession.model_validate_json(
        session_path.read_text(encoding="utf-8")
    )

    if fmt == "pdf":
        from blhackbox.reporting.pdf_generator import generate_pdf_report

        out = generate_pdf_report(session_data)
    else:
        from blhackbox.reporting.html_generator import generate_html_report

        out = generate_html_report(session_data)

    return json.dumps({"report_path": str(out), "format": fmt})


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


async def run_server() -> None:
    """Start the Blhackbox MCP server on stdio."""
    logger.info("Starting Blhackbox MCP server")
    async with stdio_server() as (read_stream, write_stream):
        await _server.run(
            read_stream,
            write_stream,
            _server.create_initialization_options(),
        )
