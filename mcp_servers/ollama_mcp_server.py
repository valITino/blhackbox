"""
blhackbox Ollama MCP Server
============================
Custom MCP server built for the blhackbox project.
NOT an official Ollama product.

Ollama runs as a standard unchanged Docker container (ollama/ollama:latest).
This server uses Ollama's /api/chat endpoint as its LLM inference backend.
The MCP layer, agent orchestration, and AggregatedPayload assembly are
entirely custom blhackbox components.
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

from blhackbox.agents.ingestion_agent import IngestionAgent
from blhackbox.agents.processing_agent import ProcessingAgent
from blhackbox.agents.synthesis_agent import SynthesisAgent
from blhackbox.models.aggregated_payload import (
    AggregatedMetadata,
    AggregatedPayload,
    ErrorLogEntry,
    Findings,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("blhackbox.ollama_mcp")

# ---------------------------------------------------------------------------
# Configuration from environment
# ---------------------------------------------------------------------------

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.3")

# ---------------------------------------------------------------------------
# MCP Server
# ---------------------------------------------------------------------------

_server = Server("blhackbox-ollama-mcp")

_TOOLS: list[Tool] = [
    Tool(
        name="process_scan_results",
        description=(
            "Process raw pentest tool output through three sequential Ollama agents "
            "(Ingestion -> Processing -> Synthesis) and return a structured "
            "AggregatedPayload. THIS IS NOT AN OLLAMA PRODUCT — it is a custom "
            "blhackbox component that uses Ollama as its LLM backend."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "raw_outputs": {
                    "type": "object",
                    "description": (
                        "Dict mapping tool names to their raw output strings. "
                        'E.g. {"nmap": "...", "nikto": "...", "hexstrike": "..."}'
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
        logger.exception("Ollama MCP tool %s failed", name)
        return [TextContent(type="text", text=f"Error: {exc}")]


async def _dispatch(name: str, args: dict[str, Any]) -> str:
    if name == "process_scan_results":
        return await _do_process_scan_results(args)
    return f"Unknown tool: {name}"


# ---------------------------------------------------------------------------
# Core processing logic — 3-agent sequential pipeline
# ---------------------------------------------------------------------------


async def _do_process_scan_results(args: dict[str, Any]) -> str:
    """Run Ingestion -> Processing -> Synthesis agents sequentially."""
    raw_outputs: dict[str, str] = args.get("raw_outputs", {})
    target: str = args.get("target", "unknown")
    session_id: str = args.get("session_id", "unknown")

    start_time = time.monotonic()
    warnings: list[str] = []

    # Calculate raw size
    raw_combined = ""
    for tool_name, output in raw_outputs.items():
        raw_combined += f"=== {tool_name} ===\n{output}\n\n"
    total_raw_size = len(raw_combined.encode("utf-8"))

    # ── Agent 1: Ingestion ────────────────────────────────────────────────
    ingestion_agent = IngestionAgent(ollama_url=OLLAMA_URL, model=OLLAMA_MODEL)
    try:
        ingestion_output = await ingestion_agent.process(raw_combined)
        if not ingestion_output:
            warnings.append("IngestionAgent returned empty output")
    except Exception as exc:
        logger.error("IngestionAgent failed: %s", exc)
        warnings.append(f"IngestionAgent failed: {exc}")
        ingestion_output = {}

    # ── Agent 2: Processing ───────────────────────────────────────────────
    processing_agent = ProcessingAgent(ollama_url=OLLAMA_URL, model=OLLAMA_MODEL)
    try:
        processing_input = json.dumps(ingestion_output) if ingestion_output else "{}"
        processing_output = await processing_agent.process(processing_input)
        if not processing_output:
            warnings.append("ProcessingAgent returned empty output")
    except Exception as exc:
        logger.error("ProcessingAgent failed: %s", exc)
        warnings.append(f"ProcessingAgent failed: {exc}")
        processing_output = {}

    # ── Agent 3: Synthesis ────────────────────────────────────────────────
    synthesis_agent = SynthesisAgent(ollama_url=OLLAMA_URL, model=OLLAMA_MODEL)
    try:
        synthesis_input = json.dumps({
            "ingestion_output": ingestion_output,
            "processing_output": processing_output,
        })
        synthesis_output = await synthesis_agent.process(synthesis_input)
        if not synthesis_output:
            warnings.append("SynthesisAgent returned empty output")
    except Exception as exc:
        logger.error("SynthesisAgent failed: %s", exc)
        warnings.append(f"SynthesisAgent failed: {exc}")
        synthesis_output = {}

    duration = time.monotonic() - start_time

    # ── Assemble AggregatedPayload ────────────────────────────────────────
    findings = _build_findings(synthesis_output, processing_output, ingestion_output, warnings)
    error_log = _build_error_log(synthesis_output, processing_output)

    # Calculate compressed size
    payload_json_preview = json.dumps(findings.model_dump(), default=str)
    compressed_size = len(payload_json_preview.encode("utf-8"))
    compression_ratio = compressed_size / total_raw_size if total_raw_size > 0 else 0.0

    payload = AggregatedPayload(
        session_id=session_id,
        target=target,
        findings=findings,
        error_log=error_log,
        metadata=AggregatedMetadata(
            tools_run=list(raw_outputs.keys()),
            total_raw_size_bytes=total_raw_size,
            compressed_size_bytes=compressed_size,
            compression_ratio=round(compression_ratio, 4),
            ollama_model=OLLAMA_MODEL,
            duration_seconds=round(duration, 2),
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


def _build_findings(
    synthesis_output: dict[str, Any],
    processing_output: dict[str, Any],
    ingestion_output: dict[str, Any],
    warnings: list[str],
) -> Findings:
    """Build Findings from agent outputs, preferring synthesis > processing > ingestion."""
    # Try synthesis output first
    findings_data = synthesis_output.get("findings", {})
    if not findings_data:
        findings_data = processing_output.get("findings", {})
    if not findings_data:
        findings_data = ingestion_output

    if not findings_data:
        return Findings()

    try:
        return Findings(**findings_data)
    except Exception as exc:
        logger.warning("Could not parse findings data: %s", exc)
        warnings.append(f"Findings parse failed: {exc}")
        # Try building with individual fields
        try:
            return Findings(
                hosts=findings_data.get("hosts", []),
                ports=findings_data.get("ports", []),
                services=findings_data.get("services", []),
                vulnerabilities=findings_data.get("vulnerabilities", []),
                endpoints=findings_data.get("endpoints", []),
                subdomains=findings_data.get("subdomains", []),
                technologies=findings_data.get("technologies", []),
            )
        except Exception:
            return Findings()


def _build_error_log(
    synthesis_output: dict[str, Any],
    processing_output: dict[str, Any],
) -> list[ErrorLogEntry]:
    """Build error log entries from agent outputs."""
    raw_entries = synthesis_output.get("error_log", [])
    if not raw_entries:
        raw_entries = processing_output.get("error_log", [])

    entries: list[ErrorLogEntry] = []
    for entry in raw_entries:
        if not isinstance(entry, dict):
            continue
        try:
            entries.append(ErrorLogEntry(**entry))
        except Exception:
            logger.warning("Could not parse error log entry: %s", entry)
    return entries


async def _store_in_neo4j(payload: AggregatedPayload) -> None:
    """Best-effort storage of the AggregatedPayload in Neo4j."""
    from blhackbox.core.knowledge_graph import KnowledgeGraphClient

    async with KnowledgeGraphClient() as kg:
        cypher = """
        MERGE (s:AggregatedSession {session_id: $session_id})
        SET s.target = $target,
            s.scan_timestamp = $scan_timestamp,
            s.tools_run = $tools_run,
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
            "compression_ratio": payload.metadata.compression_ratio,
            "ollama_model": payload.metadata.ollama_model,
            "duration_seconds": payload.metadata.duration_seconds,
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
        for vuln in payload.findings.vulnerabilities:
            if vuln.id:
                vuln_cypher = """
                MERGE (v:Vulnerability {identifier: $vid})
                SET v.severity = $severity,
                    v.cvss = $cvss,
                    v.description = $description
                WITH v
                MATCH (s:AggregatedSession {session_id: $session_id})
                MERGE (s)-[:HAS_FINDING]->(v)
                """
                await kg.run_query(vuln_cypher, {
                    "vid": vuln.id,
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
    """Start the blhackbox Ollama MCP server on stdio."""
    logger.info(
        "Starting blhackbox Ollama MCP Server (Ollama: %s, Model: %s)",
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
