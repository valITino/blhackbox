"""MCP server for Blhackbox.

Exposes high-level pentesting capabilities (not individual tools) so that
any MCP-compatible LLM can drive autonomous reconnaissance, query the
knowledge graph, and generate reports.

Blhackbox MCP provides *orchestrated workflows*:
  - run_tool           → execute a single tool via best available backend
  - query_graph        → Cypher queries against the knowledge graph
  - get_findings       → retrieve structured findings for a target
  - list_tools         → discover available tools across all backends
  - generate_report    → produce HTML/PDF reports from session data
  - list_templates     → discover available prompt templates
  - get_template       → retrieve a prompt template for autonomous pentesting
  - aggregate_results  → validate & store structured findings (MCP host does the analysis)
  - get_payload_schema → return the AggregatedPayload JSON schema
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
        name="run_tool",
        description=(
            "Execute a single security tool (e.g. nmap, subfinder, nuclei) "
            "via the local CLI backend."
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
            "Generate a professional pentest report from a session. "
            "Reports are saved to an organized folder structure: "
            "reports/reports-DDMMYYYY/report-<target>-DDMMYYYY.<ext>. "
            "Use format 'both' to generate .md and .pdf together."
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
                    "enum": ["html", "pdf", "md", "both"],
                    "description": "Report format. Use 'both' for .md + .pdf (default: both)",
                    "default": "both",
                },
            },
            "required": ["session_id"],
        },
    ),
    Tool(
        name="list_templates",
        description=(
            "List all available prompt templates for autonomous pentesting. "
            "Templates provide structured workflows for different assessment "
            "types (full pentest, recon, web app, network, OSINT, vuln assessment, "
            "API security, bug bounty, quick scan)."
        ),
        inputSchema={
            "type": "object",
            "properties": {},
        },
    ),
    Tool(
        name="get_template",
        description=(
            "Retrieve a prompt template by name. Returns the full template "
            "content with [TARGET] placeholders replaced if a target is provided. "
            "Each template instructs the AI to use all available MCP servers "
            "(Kali MCP, WireMCP, Screenshot MCP) and aggregate results directly."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": (
                        "Template name: full-pentest, full-attack-chain, quick-scan, "
                        "recon-deep, web-app-assessment, network-infrastructure, "
                        "osint-gathering, vuln-assessment, api-security, bug-bounty"
                    ),
                },
                "target": {
                    "type": "string",
                    "description": "Target to replace [TARGET] placeholders with",
                },
            },
            "required": ["name"],
        },
    ),
    Tool(
        name="aggregate_results",
        description=(
            "Validate and store structured pentest findings produced by the "
            "MCP host (Claude). The MCP host parses raw tool outputs, "
            "deduplicates, correlates, and structures them into an "
            "AggregatedPayload — then calls this tool to validate and persist "
            "the payload for report generation and optional Neo4j storage. "
            "Use get_payload_schema first to see the expected JSON schema."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "payload": {
                    "type": "object",
                    "description": (
                        "Complete AggregatedPayload JSON object. Must include "
                        "session_id, target, and at least one of: findings, "
                        "error_log, executive_summary, remediation."
                    ),
                },
            },
            "required": ["payload"],
        },
    ),
    Tool(
        name="get_payload_schema",
        description=(
            "Return the AggregatedPayload JSON schema so the MCP host knows "
            "exactly what structure to produce when aggregating raw tool "
            "outputs. Call this before aggregate_results to understand the "
            "expected format."
        ),
        inputSchema={
            "type": "object",
            "properties": {},
        },
    ),
    Tool(
        name="take_screenshot",
        description=(
            "Capture a web page screenshot via headless Chromium for PoC "
            "evidence. Supports full-page capture, custom viewport, and "
            "CSS selector wait conditions. Returns path, dimensions, and "
            "base64 PNG data."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "Web page URL (http:// or https://)",
                },
                "width": {
                    "type": "integer",
                    "description": "Viewport width in pixels (1-3840, default 1280)",
                    "default": 1280,
                },
                "height": {
                    "type": "integer",
                    "description": "Viewport height in pixels (1-2160, default 720)",
                    "default": 720,
                },
                "full_page": {
                    "type": "boolean",
                    "description": "Capture the full scrollable page (default false)",
                    "default": False,
                },
                "wait_for_selector": {
                    "type": "string",
                    "description": "CSS selector to wait for before capture",
                },
                "wait_timeout": {
                    "type": "integer",
                    "description": "Extra milliseconds to wait after page load (0-30000)",
                    "default": 0,
                },
            },
            "required": ["url"],
        },
    ),
    Tool(
        name="take_element_screenshot",
        description=(
            "Screenshot a specific page element by CSS selector. Useful for "
            "capturing vulnerability evidence like XSS payloads, error messages, "
            "or exposed admin panels in bug bounty PoC documentation."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "Web page URL (http:// or https://)",
                },
                "selector": {
                    "type": "string",
                    "description": "CSS selector for the target element",
                },
                "width": {
                    "type": "integer",
                    "description": "Viewport width in pixels (1-3840, default 1280)",
                    "default": 1280,
                },
                "height": {
                    "type": "integer",
                    "description": "Viewport height in pixels (1-2160, default 720)",
                    "default": 720,
                },
            },
            "required": ["url", "selector"],
        },
    ),
    Tool(
        name="list_screenshots",
        description=(
            "List captured screenshots with metadata (path, size, timestamp). "
            "Use to review evidence collected during a pentesting session."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Maximum screenshots to return (1-200, default 50)",
                    "default": 50,
                },
            },
        },
    ),
    Tool(
        name="annotate_screenshot",
        description=(
            "Add text labels and highlight boxes to a screenshot for PoC "
            "documentation. Annotate vulnerability evidence with arrows, "
            "labels, and colored bounding boxes."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "screenshot_path": {
                    "type": "string",
                    "description": "Path to the source screenshot PNG file",
                },
                "annotations": {
                    "type": "string",
                    "description": (
                        "JSON array of annotations. Each: "
                        '{"type":"text","x":10,"y":10,"text":"XSS!","color":"red","size":20} or '
                        '{"type":"box","x":100,"y":200,"width":300,"height":50,"color":"red"}'
                    ),
                },
            },
            "required": ["screenshot_path", "annotations"],
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
    if name == "run_tool":
        return await _do_run_tool(args)
    elif name == "query_graph":
        return await _do_query_graph(args)
    elif name == "get_findings":
        return await _do_get_findings(args)
    elif name == "list_tools":
        return await _do_list_tools()
    elif name == "generate_report":
        return await _do_generate_report(args)
    elif name == "list_templates":
        return await _do_list_templates()
    elif name == "get_template":
        return await _do_get_template(args)
    elif name == "aggregate_results":
        return await _do_aggregate_results(args)
    elif name == "get_payload_schema":
        return await _do_get_payload_schema()
    elif name == "take_screenshot":
        return await _do_take_screenshot(args)
    elif name == "take_element_screenshot":
        return await _do_take_element_screenshot(args)
    elif name == "list_screenshots":
        return await _do_list_screenshots(args)
    elif name == "annotate_screenshot":
        return await _do_annotate_screenshot(args)
    else:
        return f"Unknown tool: {name}"


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
    fmt = args.get("format", "both")

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

    if fmt == "both":
        from blhackbox.reporting.md_generator import generate_md_report
        from blhackbox.reporting.pdf_generator import generate_pdf_report

        md_out = generate_md_report(session_data)
        pdf_out = generate_pdf_report(session_data)
        return json.dumps({
            "reports": [
                {"path": str(md_out), "format": "md"},
                {"path": str(pdf_out), "format": "pdf"},
            ],
        })
    elif fmt == "md":
        from blhackbox.reporting.md_generator import generate_md_report

        out = generate_md_report(session_data)
    elif fmt == "pdf":
        from blhackbox.reporting.pdf_generator import generate_pdf_report

        out = generate_pdf_report(session_data)
    else:
        from blhackbox.reporting.html_generator import generate_html_report

        out = generate_html_report(session_data)

    return json.dumps({"report_path": str(out), "format": fmt})


async def _do_list_templates() -> str:
    from blhackbox.prompts import list_templates

    templates = list_templates()
    return json.dumps({"templates": templates}, indent=2)


async def _do_get_template(args: dict[str, Any]) -> str:
    from blhackbox.prompts import load_template, load_verification

    name = args["name"]
    target = args.get("target")
    try:
        content = load_template(name, target=target)
    except (ValueError, FileNotFoundError) as exc:
        return json.dumps({"error": str(exc)})

    # Append active verification document as authorization context
    verification = load_verification()
    if verification:
        content += (
            "\n\n---\n\n"
            "## ACTIVE AUTHORIZATION DOCUMENT\n\n"
            "The following verification document confirms explicit written "
            "authorization for all activities described above.\n\n"
            + verification
        )
    else:
        content += (
            "\n\n---\n\n"
            "## ⚠ NO ACTIVE AUTHORIZATION DOCUMENT\n\n"
            "No verification document found. Before executing this template, "
            "the operator must:\n\n"
            "1. Edit `verification.env` with engagement details\n"
            "2. Set `AUTHORIZATION_STATUS=ACTIVE`\n"
            "3. Run `make inject-verification`\n\n"
            "This generates the explicit written authorization required "
            "for penetration testing activities.\n"
        )

    return content


# ---------------------------------------------------------------------------
# Aggregate results — MCP host (Claude) does the analysis, this validates
# ---------------------------------------------------------------------------


async def _do_aggregate_results(args: dict[str, Any]) -> str:
    from blhackbox.models.aggregated_payload import AggregatedPayload

    raw_payload = args["payload"]
    if not isinstance(raw_payload, dict):
        return json.dumps({"error": "payload must be a JSON object"})

    # Require at minimum session_id and target
    if "session_id" not in raw_payload or "target" not in raw_payload:
        return json.dumps({
            "error": "payload must include 'session_id' and 'target'"
        })

    try:
        payload = AggregatedPayload(**raw_payload)
    except Exception as exc:
        return json.dumps({
            "error": f"Payload validation failed: {exc}",
            "hint": "Use get_payload_schema to see the expected format.",
        })

    # Persist as JSON for report generation
    from blhackbox.config import settings

    results_dir = settings.results_dir
    results_dir.mkdir(parents=True, exist_ok=True)
    session_file = results_dir / f"session-{payload.session_id}.json"
    session_file.write_text(
        json.dumps(payload.to_dict(), indent=2, default=str),
        encoding="utf-8",
    )

    # Optional Neo4j storage — auto-populate full knowledge graph (best-effort)
    graph_stats: dict[str, int] = {}
    try:
        from blhackbox.core.knowledge_graph import KnowledgeGraphClient

        async with KnowledgeGraphClient() as kg:
            graph_stats = await _populate_knowledge_graph(kg, payload)
    except Exception:
        logger.debug("Neo4j storage skipped (not available or failed)")

    vuln_count = len(payload.findings.vulnerabilities)
    host_count = len(payload.findings.hosts)
    result: dict[str, Any] = {
        "status": "ok",
        "session_id": payload.session_id,
        "session_file": str(session_file),
        "summary": {
            "hosts": host_count,
            "vulnerabilities": vuln_count,
            "endpoints": len(payload.findings.endpoints),
            "subdomains": len(payload.findings.subdomains),
            "risk_level": payload.executive_summary.risk_level,
        },
        "hint": f"Use generate_report with session_id='{session_file}' to create the report.",
    }
    if graph_stats:
        result["knowledge_graph"] = graph_stats
    return json.dumps(result)


async def _populate_knowledge_graph(
    kg: Any,
    payload: Any,
) -> dict[str, int]:
    """Auto-populate Neo4j knowledge graph from AggregatedPayload.

    Creates nodes for hosts, services, vulnerabilities, endpoints, and
    subdomains, plus relationships between them.  Returns a dict of
    node-type counts that were merged into the graph.

    Inspired by PentAGI's Graphiti auto-extraction — but leveraging the
    structured AggregatedPayload we already have instead of LLM-based
    entity extraction.
    """
    stats: dict[str, int] = {}

    # 1. Merge the session node and link to target
    await kg.merge_aggregated_session(
        session_id=payload.session_id,
        target_value=payload.target,
        scan_timestamp=payload.scan_timestamp.isoformat(),
        tools_run=payload.metadata.tools_run,
    )
    stats["sessions"] = 1

    # 2. Merge hosts and their ports/services
    host_count = 0
    for host in payload.findings.hosts:
        ip = host.ip or host.hostname
        if not ip:
            continue
        await kg.merge_ip(ip)
        if host.hostname and host.hostname != ip:
            await kg.link_domain_to_ip(host.hostname, ip)
        for port in host.ports:
            port_node = await kg.merge_port(ip, port.port, port.protocol)
            if port.service:
                await kg.merge_service(
                    ip, port.port, port.service, port.version
                )
        host_count += 1
    stats["hosts"] = host_count

    # 3. Merge standalone services (from findings.services)
    svc_count = 0
    for svc in payload.findings.services:
        if svc.host and svc.port:
            await kg.merge_service(svc.host, svc.port, svc.name, svc.version)
            svc_count += 1
    stats["services"] = svc_count

    # 4. Merge vulnerabilities and link to hosts
    vuln_count = 0
    for vuln in payload.findings.vulnerabilities:
        identifier = vuln.id or f"VULN-{vuln.title[:40]}"
        await kg.merge_vulnerability(
            target_value=vuln.host or payload.target,
            identifier=identifier,
            severity=vuln.severity,
            title=vuln.title,
        )
        vuln_count += 1
    stats["vulnerabilities"] = vuln_count

    # 5. Merge subdomains
    sub_count = 0
    for subdomain in payload.findings.subdomains:
        if subdomain:
            await kg.link_subdomain(subdomain, payload.target)
            sub_count += 1
    stats["subdomains"] = sub_count

    # 6. Merge endpoints as findings
    ep_count = 0
    for ep in payload.findings.endpoints:
        if ep.url:
            finding_id = f"EP-{ep.method}-{ep.url[:80]}"
            await kg.merge_finding(
                target_value=payload.target,
                finding_id=finding_id,
                tool="endpoint_discovery",
                title=f"{ep.method} {ep.url}",
                severity="info",
                description=f"Status {ep.status_code}" if ep.status_code else "",
            )
            ep_count += 1
    stats["endpoints"] = ep_count

    logger.info(
        "Knowledge graph populated: %s",
        ", ".join(f"{k}={v}" for k, v in stats.items()),
    )
    return stats


async def _do_get_payload_schema() -> str:
    from blhackbox.models.aggregated_payload import AggregatedPayload

    schema = AggregatedPayload.model_json_schema()
    return json.dumps(schema, indent=2)


# ---------------------------------------------------------------------------
# Screenshot helpers — proxy to screenshot-mcp via HTTP
# ---------------------------------------------------------------------------


async def _screenshot_request(endpoint: str, payload: dict[str, Any]) -> str:
    """Send a request to the screenshot-mcp SSE server's tool endpoint."""
    import httpx

    from blhackbox.config import settings

    base_url = settings.screenshot_mcp_url
    url = f"{base_url}/mcp/v1/tools/{endpoint}"

    try:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            return resp.text
    except Exception:
        # Fallback: call the tool directly if the HTTP proxy fails.
        # This happens when running the MCP server standalone (not in Docker).
        logger.debug("Screenshot MCP HTTP proxy unavailable, trying direct call")
        return json.dumps({
            "error": (
                "Screenshot MCP server not reachable. "
                "Use the screenshot MCP server directly via SSE at "
                f"{base_url}/sse or ensure the screenshot-mcp container is running."
            ),
        })


async def _do_take_screenshot(args: dict[str, Any]) -> str:
    return await _screenshot_request("take_screenshot", args)


async def _do_take_element_screenshot(args: dict[str, Any]) -> str:
    return await _screenshot_request("take_element_screenshot", args)


async def _do_list_screenshots(args: dict[str, Any]) -> str:
    return await _screenshot_request("list_screenshots", args)


async def _do_annotate_screenshot(args: dict[str, Any]) -> str:
    return await _screenshot_request("annotate_screenshot", args)


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
