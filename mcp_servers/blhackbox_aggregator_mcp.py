"""
blhackbox Aggregator MCP Server
================================
A custom MCP server built specifically for the blhackbox project.

THIS IS NOT AN OFFICIAL OLLAMA PRODUCT.

It uses Ollama as its local LLM inference backend — Ollama runs
unchanged on localhost:11434. The MCP server layer, agent dispatch
logic, and AggregatedPayload assembly are entirely custom components
of the blhackbox project.

Purpose: receive raw pentest tool output from Claude, dispatch it to
specialized Python agent classes (each of which calls Ollama's standard
/api/chat endpoint with a task-specific system prompt), assemble the
cleaned structured outputs into an AggregatedPayload, and return it
to Claude for final analysis and report generation.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
import time
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

# Ensure the blhackbox package is importable when run as a standalone script
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from blhackbox.agents.error_log_agent import ErrorLogAgent
from blhackbox.agents.network_agent import NetworkAgent
from blhackbox.agents.recon_agent import ReconAgent
from blhackbox.agents.structure_agent import StructureAgent
from blhackbox.agents.vuln_agent import VulnAgent
from blhackbox.agents.web_agent import WebAgent
from blhackbox.models.aggregated_payload import (
    AggregatedMetadata,
    AggregatedPayload,
    ErrorLogEntry,
    MainFindings,
    NetworkFindings,
    ReconFindings,
    VulnFindings,
    WebFindings,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("blhackbox.aggregator_mcp")

# ---------------------------------------------------------------------------
# Configuration from environment
# ---------------------------------------------------------------------------

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.3")

# ---------------------------------------------------------------------------
# MCP Server
# ---------------------------------------------------------------------------

_server = Server("blhackbox-aggregator")

_TOOLS: list[Tool] = [
    Tool(
        name="aggregate_pentest_data",
        description=(
            "Aggregate raw pentest tool output via local Ollama preprocessing agents. "
            "Dispatches data to specialized agents (recon, network, vuln, web, error_log), "
            "assembles cleaned structured outputs into an AggregatedPayload, and returns it. "
            "THIS IS NOT AN OLLAMA PRODUCT — it is a custom blhackbox component that uses "
            "Ollama as its LLM backend."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "raw_outputs": {
                    "type": "object",
                    "description": (
                        "Dict mapping tool names to their raw output strings. "
                        'E.g. {"nmap": "...", "nikto": "...", "hexstrike_recon": "..."}'
                    ),
                },
                "target": {
                    "type": "string",
                    "description": "The target domain, IP, or URL being assessed",
                },
                "session_id": {
                    "type": "string",
                    "description": "Unique session identifier for this assessment",
                },
            },
            "required": ["raw_outputs", "target", "session_id"],
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
        logger.exception("Aggregator MCP tool %s failed", name)
        return [TextContent(type="text", text=f"Error: {exc}")]


async def _dispatch(name: str, args: dict[str, Any]) -> str:
    if name == "aggregate_pentest_data":
        return await _do_aggregate(args)
    return f"Unknown tool: {name}"


# ---------------------------------------------------------------------------
# Core aggregation logic
# ---------------------------------------------------------------------------


def _classify_raw_outputs(raw_outputs: dict[str, str]) -> dict[str, str]:
    """Classify raw tool outputs into agent categories.

    Returns a dict mapping category names to combined raw output strings.
    """
    categories: dict[str, list[str]] = {
        "recon": [],
        "network": [],
        "vuln": [],
        "web": [],
        "all": [],  # everything goes to error_log agent
    }

    # Keyword-based classification
    recon_tools = {
        "subfinder", "amass", "whois", "fierce", "dnsenum", "dnsrecon",
        "theharvester", "shodan", "censys", "crtsh", "ct", "osint",
        "hexstrike_recon", "recon",
    }
    network_tools = {
        "nmap", "masscan", "rustscan", "ping", "traceroute",
        "hexstrike_network", "network",
    }
    vuln_tools = {
        "nuclei", "sqlmap", "wpscan_vuln", "hexstrike_vuln", "vuln",
        "vulnerability", "cve",
    }
    web_tools = {
        "nikto", "gobuster", "dirb", "whatweb", "wafw00f", "httpx",
        "katana", "wpscan", "dirsearch", "ffuf",
        "hexstrike_web", "web",
    }

    for tool_name, output in raw_outputs.items():
        tool_lower = tool_name.lower()
        categories["all"].append(f"=== {tool_name} ===\n{output}")

        classified = False
        for keyword in recon_tools:
            if keyword in tool_lower:
                categories["recon"].append(f"=== {tool_name} ===\n{output}")
                classified = True
                break

        if not classified:
            for keyword in network_tools:
                if keyword in tool_lower:
                    categories["network"].append(f"=== {tool_name} ===\n{output}")
                    classified = True
                    break

        if not classified:
            for keyword in vuln_tools:
                if keyword in tool_lower:
                    categories["vuln"].append(f"=== {tool_name} ===\n{output}")
                    classified = True
                    break

        if not classified:
            for keyword in web_tools:
                if keyword in tool_lower:
                    categories["web"].append(f"=== {tool_name} ===\n{output}")
                    classified = True
                    break

        # If not classified, send to both recon and web as a best-effort
        if not classified:
            categories["recon"].append(f"=== {tool_name} ===\n{output}")
            categories["web"].append(f"=== {tool_name} ===\n{output}")

    return {
        "recon": "\n\n".join(categories["recon"]),
        "network": "\n\n".join(categories["network"]),
        "vuln": "\n\n".join(categories["vuln"]),
        "web": "\n\n".join(categories["web"]),
        "all": "\n\n".join(categories["all"]),
    }


async def _do_aggregate(args: dict[str, Any]) -> str:
    """Run all preprocessing agents and assemble the AggregatedPayload."""
    raw_outputs: dict[str, str] = args.get("raw_outputs", {})
    target: str = args.get("target", "unknown")
    session_id: str = args.get("session_id", "unknown")

    start_time = time.monotonic()
    warnings: list[str] = []
    agents_run: list[str] = []

    # Count raw lines
    total_raw_lines = sum(
        output.count("\n") + 1 for output in raw_outputs.values()
    )

    # Classify outputs by category
    classified = _classify_raw_outputs(raw_outputs)

    # Instantiate agents
    recon_agent = ReconAgent(ollama_url=OLLAMA_URL, model=OLLAMA_MODEL)
    network_agent = NetworkAgent(ollama_url=OLLAMA_URL, model=OLLAMA_MODEL)
    vuln_agent = VulnAgent(ollama_url=OLLAMA_URL, model=OLLAMA_MODEL)
    web_agent = WebAgent(ollama_url=OLLAMA_URL, model=OLLAMA_MODEL)
    error_log_agent = ErrorLogAgent(ollama_url=OLLAMA_URL, model=OLLAMA_MODEL)

    # Run all agents concurrently
    results = await asyncio.gather(
        _run_agent("ReconAgent", recon_agent, classified["recon"], agents_run, warnings),
        _run_agent("NetworkAgent", network_agent, classified["network"], agents_run, warnings),
        _run_agent("VulnAgent", vuln_agent, classified["vuln"], agents_run, warnings),
        _run_agent("WebAgent", web_agent, classified["web"], agents_run, warnings),
        _run_agent("ErrorLogAgent", error_log_agent, classified["all"], agents_run, warnings),
        return_exceptions=True,
    )

    recon_data, network_data, vuln_data, web_data, error_data = [
        r if isinstance(r, dict) else {} for r in results
    ]

    # Build the structured findings — wrap in try/except because Ollama may
    # return data that doesn't match the Pydantic schema (wrong types, etc.)
    main_findings = _build_main_findings(
        recon_data, network_data, vuln_data, web_data, warnings
    )

    # Build error log
    error_log_entries = _build_error_log(error_data)

    # Optionally run the StructureAgent for final merge/cleanup
    # (only if we got data from multiple agents)
    if sum(1 for d in [recon_data, network_data, vuln_data, web_data] if d) >= 2:
        structure_agent = StructureAgent(ollama_url=OLLAMA_URL, model=OLLAMA_MODEL)
        merge_input = json.dumps({
            "recon": recon_data,
            "network": network_data,
            "vulnerabilities": vuln_data,
            "web": web_data,
            "error_log": error_data.get("error_log", []),
        })
        try:
            merged = await structure_agent.process(merge_input)
            agents_run.append("StructureAgent")
            if merged and "main_findings" in merged:
                mf = merged["main_findings"]
                merged_findings = _build_main_findings(
                    mf.get("recon", {}),
                    mf.get("network", {}),
                    mf.get("vulnerabilities", {}),
                    mf.get("web", {}),
                    warnings,
                    fallback=main_findings,
                )
                main_findings = merged_findings
                if "error_log" in merged:
                    merged_log = _build_error_log(merged)
                    if merged_log:
                        error_log_entries = merged_log
        except Exception as exc:
            logger.warning("StructureAgent failed (using unmerged data): %s", exc)
            warnings.append(f"StructureAgent failed: {exc}")

    duration = time.monotonic() - start_time

    # Calculate compressed lines
    payload_json = main_findings.model_dump_json()
    compressed_lines = payload_json.count("\n") + 1
    compression_ratio = (
        compressed_lines / total_raw_lines if total_raw_lines > 0 else 0.0
    )

    # Assemble the final payload
    payload = AggregatedPayload(
        session_id=session_id,
        target=target,
        main_findings=main_findings,
        error_log=error_log_entries,
        metadata=AggregatedMetadata(
            tools_run=list(raw_outputs.keys()),
            agents_run=agents_run,
            total_raw_lines_processed=total_raw_lines,
            compressed_to_lines=compressed_lines,
            compression_ratio=round(compression_ratio, 4),
            ollama_model_used=OLLAMA_MODEL,
            aggregation_duration_seconds=round(duration, 2),
            warning="; ".join(warnings) if warnings else "",
        ),
    )

    # Optionally store in Neo4j (best-effort, non-blocking)
    neo4j_uri = os.environ.get("NEO4J_URI", "")
    if neo4j_uri:
        try:
            await _store_in_neo4j(payload)
        except Exception as exc:
            logger.warning("Neo4j storage failed (non-fatal): %s", exc)

    return json.dumps(payload.to_dict(), indent=2, default=str)


def _build_main_findings(
    recon_data: dict[str, Any],
    network_data: dict[str, Any],
    vuln_data: dict[str, Any],
    web_data: dict[str, Any],
    warnings: list[str],
    fallback: MainFindings | None = None,
) -> MainFindings:
    """Safely construct MainFindings from agent output dicts.

    Wraps each sub-model construction in try/except to handle malformed
    data from Ollama (wrong types, unexpected nesting, etc.).
    """
    fb = fallback or MainFindings()

    def _safe_build(model_cls: type, data: dict, fallback_val: Any, label: str) -> Any:
        if not data:
            return fallback_val
        try:
            return model_cls(**data)
        except Exception as exc:
            logger.warning("Could not parse %s data: %s", label, exc)
            warnings.append(f"{label} parse failed: {exc}")
            return fallback_val

    return MainFindings(
        recon=_safe_build(ReconFindings, recon_data, fb.recon, "recon"),
        network=_safe_build(NetworkFindings, network_data, fb.network, "network"),
        vulnerabilities=_safe_build(VulnFindings, vuln_data, fb.vulnerabilities, "vuln"),
        web=_safe_build(WebFindings, web_data, fb.web, "web"),
    )


def _build_error_log(error_data: dict[str, Any]) -> list[ErrorLogEntry]:
    """Safely construct ErrorLogEntry list from agent output."""
    entries: list[ErrorLogEntry] = []
    for entry in error_data.get("error_log", []):
        if not isinstance(entry, dict):
            continue
        try:
            entries.append(ErrorLogEntry(**entry))
        except Exception:
            logger.warning("Could not parse error log entry: %s", entry)
    return entries


async def _run_agent(
    name: str,
    agent: Any,
    raw_data: str,
    agents_run: list[str],
    warnings: list[str],
) -> dict[str, Any]:
    """Run a single agent with error handling."""
    if not raw_data.strip():
        logger.info("%s: No data to process, skipping", name)
        return {}

    try:
        result = await agent.process(raw_data)
        agents_run.append(name)
        return result
    except Exception as exc:
        logger.error("%s failed: %s", name, exc)
        warnings.append(f"{name} failed: {exc}")
        return {}


async def _store_in_neo4j(payload: AggregatedPayload) -> None:
    """Best-effort storage of the AggregatedPayload in Neo4j."""
    from blhackbox.core.knowledge_graph import KnowledgeGraphClient

    async with KnowledgeGraphClient() as kg:
        # Store as an AggregatedSession node
        cypher = """
        MERGE (s:AggregatedSession {session_id: $session_id})
        SET s.target = $target,
            s.scan_timestamp = $scan_timestamp,
            s.tools_run = $tools_run,
            s.agents_run = $agents_run,
            s.total_raw_lines = $total_raw_lines,
            s.compression_ratio = $compression_ratio,
            s.ollama_model = $ollama_model,
            s.duration_seconds = $duration_seconds,
            s.warning = $warning
        """
        await kg.run_query(cypher, {
            "session_id": payload.session_id,
            "target": payload.target,
            "scan_timestamp": payload.scan_timestamp.isoformat(),
            "tools_run": payload.metadata.tools_run,
            "agents_run": payload.metadata.agents_run,
            "total_raw_lines": payload.metadata.total_raw_lines_processed,
            "compression_ratio": payload.metadata.compression_ratio,
            "ollama_model": payload.metadata.ollama_model_used,
            "duration_seconds": payload.metadata.aggregation_duration_seconds,
            "warning": payload.metadata.warning,
        })

        # Link to Domain or IP node
        target = payload.target
        if _looks_like_ip(target):
            link_cypher = """
            MERGE (t:IPAddress {address: $target})
            WITH t
            MATCH (s:AggregatedSession {session_id: $session_id})
            MERGE (t)-[:HAS_AGGREGATED_SESSION]->(s)
            """
        else:
            link_cypher = """
            MERGE (t:Domain {name: $target})
            WITH t
            MATCH (s:AggregatedSession {session_id: $session_id})
            MERGE (t)-[:HAS_AGGREGATED_SESSION]->(s)
            """
        await kg.run_query(link_cypher, {
            "target": target,
            "session_id": payload.session_id,
        })

        # Store vulnerability findings as linked nodes
        for vuln in payload.main_findings.vulnerabilities.vulnerabilities:
            if vuln.cve:
                vuln_cypher = """
                MERGE (v:Vulnerability {identifier: $cve})
                SET v.severity = $severity,
                    v.cvss = $cvss,
                    v.description = $description
                WITH v
                MATCH (s:AggregatedSession {session_id: $session_id})
                MERGE (s)-[:HAS_FINDING]->(v)
                """
                await kg.run_query(vuln_cypher, {
                    "cve": vuln.cve,
                    "severity": vuln.severity,
                    "cvss": vuln.cvss,
                    "description": vuln.description[:5000],
                    "session_id": payload.session_id,
                })

    logger.info("Stored AggregatedPayload in Neo4j for session %s", payload.session_id)


def _looks_like_ip(value: str) -> bool:
    parts = value.split(".")
    if len(parts) != 4:
        return False
    return all(p.isdigit() and 0 <= int(p) <= 255 for p in parts)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


async def run_server() -> None:
    """Start the blhackbox aggregator MCP server on stdio."""
    logger.info(
        "Starting blhackbox Aggregator MCP Server (Ollama: %s, Model: %s)",
        OLLAMA_URL,
        OLLAMA_MODEL,
    )
    async with stdio_server() as (read_stream, write_stream):
        await _server.run(
            read_stream,
            write_stream,
            _server.create_initialization_options(),
        )


if __name__ == "__main__":
    asyncio.run(run_server())
