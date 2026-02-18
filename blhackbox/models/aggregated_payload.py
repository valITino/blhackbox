"""AggregatedPayload — structured output from the Ollama preprocessing pipeline.

This model represents the final assembled payload that the blhackbox
aggregator MCP server returns to Claude after all agent preprocessing
is complete.  Claude uses this payload to write the final pentest report.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Sub-models
# ---------------------------------------------------------------------------


class HostPort(BaseModel):
    """A single open port on a host."""

    port: int
    service: str = ""
    version: str = ""
    state: str = "open"
    banner: str = ""


class HostEntry(BaseModel):
    """A scanned host with its open ports."""

    ip: str
    ports: list[HostPort] = Field(default_factory=list)


class ASNInfo(BaseModel):
    """Autonomous System Number information."""

    asn: str = ""
    name: str = ""
    country: str = ""


class CertificateInfo(BaseModel):
    """TLS certificate metadata."""

    subject: str = ""
    issuer: str = ""
    not_before: str = ""
    not_after: str = ""
    san: list[str] = Field(default_factory=list)


class ReconFindings(BaseModel):
    """Output from the ReconAgent."""

    subdomains: list[str] = Field(default_factory=list)
    ips: list[str] = Field(default_factory=list)
    technologies: list[str] = Field(default_factory=list)
    asn: ASNInfo = Field(default_factory=ASNInfo)
    certificates: list[CertificateInfo] = Field(default_factory=list)


class NetworkFindings(BaseModel):
    """Output from the NetworkAgent."""

    hosts: list[HostEntry] = Field(default_factory=list)


class VulnerabilityEntry(BaseModel):
    """A single vulnerability finding."""

    cve: str = ""
    cvss: float = 0.0
    severity: str = "info"
    host: str = ""
    description: str = ""
    references: list[str] = Field(default_factory=list)


class VulnFindings(BaseModel):
    """Output from the VulnAgent."""

    vulnerabilities: list[VulnerabilityEntry] = Field(default_factory=list)


class WebFindings(BaseModel):
    """Output from the WebAgent."""

    endpoints: list[str] = Field(default_factory=list)
    technologies: list[str] = Field(default_factory=list)
    headers: dict[str, str] = Field(default_factory=dict)
    findings: list[str] = Field(default_factory=list)
    cms: str = ""


class ErrorLogEntry(BaseModel):
    """A single error/noise entry from the ErrorLogAgent."""

    type: str = "other"
    count: int = 0
    locations: list[str] = Field(default_factory=list)
    likely_cause: str = ""
    security_relevance: str = "none"
    security_note: str = ""


# ---------------------------------------------------------------------------
# Main findings container
# ---------------------------------------------------------------------------


class MainFindings(BaseModel):
    """Aggregated findings from all preprocessing agents."""

    recon: ReconFindings = Field(default_factory=ReconFindings)
    network: NetworkFindings = Field(default_factory=NetworkFindings)
    vulnerabilities: VulnFindings = Field(default_factory=VulnFindings)
    web: WebFindings = Field(default_factory=WebFindings)


# ---------------------------------------------------------------------------
# Metadata
# ---------------------------------------------------------------------------


class AggregatedMetadata(BaseModel):
    """Metadata about the aggregation run."""

    tools_run: list[str] = Field(default_factory=list)
    agents_run: list[str] = Field(default_factory=list)
    total_raw_lines_processed: int = 0
    compressed_to_lines: int = 0
    compression_ratio: float = 0.0
    ollama_model_used: str = ""
    aggregation_duration_seconds: float = 0.0
    warning: str = ""


# ---------------------------------------------------------------------------
# Top-level payload
# ---------------------------------------------------------------------------


class AggregatedPayload(BaseModel):
    """The complete aggregated pentest data payload.

    Returned by the blhackbox aggregator MCP server to Claude after
    all Ollama preprocessing agents have run.
    """

    session_id: str
    target: str
    scan_timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    main_findings: MainFindings = Field(default_factory=MainFindings)
    error_log: list[ErrorLogEntry] = Field(default_factory=list)
    metadata: AggregatedMetadata = Field(default_factory=AggregatedMetadata)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a JSON-compatible dict."""
        return self.model_dump(mode="json")
