"""
blhackbox Ollama MCP Server
============================
Custom MCP server built for the blhackbox project.
NOT an official Ollama product.

This is a thin MCP orchestrator that receives data from Claude, calls each
of the 3 agent containers (Ingestion, Processing, Synthesis) via HTTP in
sequence, assembles the final AggregatedPayload, and returns it to Claude.

It does NOT call Ollama directly — each agent container handles its own
Ollama calls independently via the official ``ollama`` Python package.

Uses FastMCP for automatic tool schema generation and protocol handling.
"""

from __future__ import annotations

import json
import logging
import os
import sys
import time
from typing import Any

import httpx
from mcp.server.fastmcp import FastMCP

# Ensure the blhackbox package is importable when run as a standalone script
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from blhackbox.models.aggregated_payload import (  # noqa: E402
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

OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.3")

# Agent container URLs — each agent runs as a separate FastAPI container
AGENT_INGESTION_URL = os.environ.get(
    "AGENT_INGESTION_URL", "http://agent-ingestion:8001"
)
AGENT_PROCESSING_URL = os.environ.get(
    "AGENT_PROCESSING_URL", "http://agent-processing:8002"
)
AGENT_SYNTHESIS_URL = os.environ.get(
    "AGENT_SYNTHESIS_URL", "http://agent-synthesis:8003"
)

# ---------------------------------------------------------------------------
# FastMCP Server
# ---------------------------------------------------------------------------

mcp = FastMCP("blhackbox-ollama-mcp")


# ---------------------------------------------------------------------------
# Core processing logic — calls 3 agent containers sequentially via HTTP
# ---------------------------------------------------------------------------


async def _call_agent(
    client: httpx.AsyncClient,
    url: str,
    data: dict | str,
    session_id: str,
    target: str,
    agent_name: str,
    warnings: list[str],
) -> dict[str, Any]:
    """Call an agent container's POST /process endpoint."""
    payload = {"data": data, "session_id": session_id, "target": target}
    try:
        response = await client.post(f"{url}/process", json=payload)
        response.raise_for_status()
        return response.json()
    except httpx.ConnectError:
        msg = f"{agent_name} unreachable at {url}"
        logger.error(msg)
        warnings.append(msg)
        return {}
    except httpx.HTTPStatusError as exc:
        msg = f"{agent_name} returned HTTP {exc.response.status_code}"
        logger.error(msg)
        warnings.append(msg)
        return {}
    except Exception as exc:
        msg = f"{agent_name} failed: {exc}"
        logger.error(msg)
        warnings.append(msg)
        return {}


@mcp.tool()
async def process_scan_results(
    raw_outputs: dict[str, str],
    target: str,
    session_id: str,
) -> str:
    """Process raw pentest tool output through three sequential agent containers.

    Calls Ingestion -> Processing -> Synthesis agent containers via HTTP and
    returns a structured AggregatedPayload. Each agent container calls Ollama
    independently. THIS IS NOT AN OLLAMA PRODUCT — it is a custom blhackbox
    component that uses Ollama as its LLM backend.

    Args:
        raw_outputs: Dict mapping tool names to their raw output strings.
            E.g. {"nmap": "...", "nikto": "...", "hexstrike": "..."}
        target: The target domain, IP, or URL being assessed.
        session_id: Unique session identifier for this assessment.

    Returns:
        JSON string of the AggregatedPayload containing findings, error_log,
        and metadata from the preprocessing pipeline.
    """
    start_time = time.monotonic()
    warnings: list[str] = []

    # Calculate raw size
    raw_combined = ""
    for tool_name, output in raw_outputs.items():
        raw_combined += f"=== {tool_name} ===\n{output}\n\n"
    total_raw_size = len(raw_combined.encode("utf-8"))

    async with httpx.AsyncClient(timeout=180.0) as client:
        # ── Agent 1: Ingestion ────────────────────────────────────────
        ingestion_output = await _call_agent(
            client, AGENT_INGESTION_URL, raw_combined,
            session_id, target, "IngestionAgent", warnings,
        )
        if not ingestion_output:
            warnings.append("IngestionAgent returned empty output")

        # ── Agent 2: Processing ───────────────────────────────────────
        processing_output = await _call_agent(
            client, AGENT_PROCESSING_URL, ingestion_output,
            session_id, target, "ProcessingAgent", warnings,
        )
        if not processing_output:
            warnings.append("ProcessingAgent returned empty output")

        # ── Agent 3: Synthesis ────────────────────────────────────────
        synthesis_input = {
            "ingested": ingestion_output,
            "processed": processing_output,
        }
        synthesis_output = await _call_agent(
            client, AGENT_SYNTHESIS_URL, synthesis_input,
            session_id, target, "SynthesisAgent", warnings,
        )
        if not synthesis_output:
            warnings.append("SynthesisAgent returned empty output")

    duration = time.monotonic() - start_time

    # ── Assemble AggregatedPayload ────────────────────────────────────
    findings = _build_findings(
        synthesis_output, processing_output, ingestion_output, warnings,
    )
    error_log = _build_error_log(synthesis_output, processing_output)

    # Calculate compressed size
    payload_json_preview = json.dumps(findings.model_dump(), default=str)
    compressed_size = len(payload_json_preview.encode("utf-8"))
    compression_ratio = (
        compressed_size / total_raw_size if total_raw_size > 0 else 0.0
    )

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

if __name__ == "__main__":
    mcp.run(transport="stdio")
