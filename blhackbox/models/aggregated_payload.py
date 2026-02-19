"""AggregatedPayload — structured output from the Ollama preprocessing pipeline.

This model represents the final assembled payload that the blhackbox
Ollama MCP server returns to Claude after all three agents (Ingestion,
Processing, Synthesis) have run.  Claude uses this payload to write the
final pentest report.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Sub-models for findings
# ---------------------------------------------------------------------------


class HostPort(BaseModel):
    """A single open port on a host."""

    port: int = 0
    protocol: str = "tcp"
    state: str = "open"
    service: str = ""
    version: str = ""
    banner: str = ""


class HostEntry(BaseModel):
    """A scanned host with its open ports."""

    ip: str = ""
    hostname: str = ""
    ports: list[HostPort] = Field(default_factory=list)


class ServiceEntry(BaseModel):
    """A detected service."""

    name: str = ""
    version: str = ""
    host: str = ""
    port: int = 0


class VulnerabilityEntry(BaseModel):
    """A single vulnerability finding."""

    id: str = ""
    title: str = ""
    severity: str = "info"
    cvss: float = 0.0
    host: str = ""
    port: int = 0
    description: str = ""
    references: list[str] = Field(default_factory=list)


class EndpointEntry(BaseModel):
    """A discovered web endpoint."""

    url: str = ""
    method: str = "GET"
    status_code: int = 0
    content_length: int = 0


class TechnologyEntry(BaseModel):
    """A detected technology."""

    name: str = ""
    version: str = ""
    category: str = ""


# ---------------------------------------------------------------------------
# Findings container
# ---------------------------------------------------------------------------


class Findings(BaseModel):
    """All structured findings from the preprocessing pipeline."""

    hosts: list[HostEntry] = Field(default_factory=list)
    ports: list[HostPort] = Field(default_factory=list)
    services: list[ServiceEntry] = Field(default_factory=list)
    vulnerabilities: list[VulnerabilityEntry] = Field(default_factory=list)
    endpoints: list[EndpointEntry] = Field(default_factory=list)
    subdomains: list[str] = Field(default_factory=list)
    technologies: list[TechnologyEntry] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Error log
# ---------------------------------------------------------------------------


class ErrorLogEntry(BaseModel):
    """A single error/noise entry with security relevance annotation."""

    type: str = "other"
    count: int = 0
    locations: list[str] = Field(default_factory=list)
    likely_cause: str = ""
    security_relevance: str = "none"
    security_note: str = ""


# ---------------------------------------------------------------------------
# Metadata
# ---------------------------------------------------------------------------


class AggregatedMetadata(BaseModel):
    """Metadata about the aggregation run."""

    tools_run: list[str] = Field(default_factory=list)
    total_raw_size_bytes: int = 0
    compressed_size_bytes: int = 0
    compression_ratio: float = 0.0
    ollama_model: str = ""
    duration_seconds: float = 0.0
    warning: str = ""


# ---------------------------------------------------------------------------
# Top-level payload
# ---------------------------------------------------------------------------


class AggregatedPayload(BaseModel):
    """The complete aggregated pentest data payload.

    Returned by the blhackbox Ollama MCP server to Claude after all three
    preprocessing agents (Ingestion, Processing, Synthesis) have run.
    """

    session_id: str
    target: str
    scan_timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    findings: Findings = Field(default_factory=Findings)
    error_log: list[ErrorLogEntry] = Field(default_factory=list)
    metadata: AggregatedMetadata = Field(default_factory=AggregatedMetadata)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a JSON-compatible dict."""
        return self.model_dump(mode="json")
