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
    nse_scripts: dict[str, str] = Field(default_factory=dict)


class HostEntry(BaseModel):
    """A scanned host with its open ports."""

    ip: str = ""
    hostname: str = ""
    os: str = ""
    ports: list[HostPort] = Field(default_factory=list)


class ServiceEntry(BaseModel):
    """A detected service."""

    name: str = ""
    version: str = ""
    host: str = ""
    port: int = 0
    cpe: str = ""


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
    evidence: str = ""
    tool_source: str = ""
    likely_false_positive: bool = False


class EndpointEntry(BaseModel):
    """A discovered web endpoint."""

    url: str = ""
    method: str = "GET"
    status_code: int = 0
    content_length: int = 0
    redirect: str = ""


class TechnologyEntry(BaseModel):
    """A detected technology."""

    name: str = ""
    version: str = ""
    category: str = ""


class SSLCertEntry(BaseModel):
    """An SSL/TLS certificate finding."""

    host: str = ""
    port: int = 443
    issuer: str = ""
    subject: str = ""
    san: list[str] = Field(default_factory=list)
    not_before: str = ""
    not_after: str = ""
    protocol: str = ""
    cipher: str = ""
    issues: list[str] = Field(default_factory=list)


class CredentialEntry(BaseModel):
    """A discovered credential."""

    host: str = ""
    port: int = 0
    service: str = ""
    username: str = ""
    password: str = ""
    tool_source: str = ""


class HTTPHeaderEntry(BaseModel):
    """HTTP header analysis for a host."""

    host: str = ""
    port: int = 0
    missing_security_headers: list[str] = Field(default_factory=list)
    server: str = ""
    x_powered_by: str = ""


class DNSRecordEntry(BaseModel):
    """A DNS record."""

    type: str = ""
    name: str = ""
    value: str = ""
    priority: int = 0


class WhoisRecord(BaseModel):
    """WHOIS domain information."""

    domain: str = ""
    registrar: str = ""
    creation_date: str = ""
    expiration_date: str = ""
    nameservers: list[str] = Field(default_factory=list)
    registrant_org: str = ""


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
    ssl_certs: list[SSLCertEntry] = Field(default_factory=list)
    credentials: list[CredentialEntry] = Field(default_factory=list)
    http_headers: list[HTTPHeaderEntry] = Field(default_factory=list)
    whois: WhoisRecord = Field(default_factory=WhoisRecord)
    dns_records: list[DNSRecordEntry] = Field(default_factory=list)


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
# Attack surface summary
# ---------------------------------------------------------------------------


class AttackSurface(BaseModel):
    """Summary of the attack surface discovered during scanning."""

    external_services: int = 0
    web_applications: int = 0
    login_panels: int = 0
    api_endpoints: int = 0
    outdated_software: int = 0
    default_credentials: int = 0
    missing_security_headers: int = 0
    ssl_issues: int = 0
    high_value_targets: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Executive summary
# ---------------------------------------------------------------------------


class TopFinding(BaseModel):
    """A top finding for the executive summary."""

    title: str = ""
    severity: str = "info"
    impact: str = ""
    exploitability: str = "moderate"
    remediation: str = ""


class AttackChain(BaseModel):
    """A chain of findings that can be combined for greater impact."""

    name: str = ""
    steps: list[str] = Field(default_factory=list)
    overall_severity: str = "info"


class VulnerabilityCounts(BaseModel):
    """Counts of vulnerabilities by severity."""

    critical: int = 0
    high: int = 0
    medium: int = 0
    low: int = 0
    info: int = 0


class ExecutiveSummary(BaseModel):
    """Executive summary of the assessment."""

    risk_level: str = "info"
    headline: str = ""
    summary: str = ""
    total_vulnerabilities: VulnerabilityCounts = Field(
        default_factory=VulnerabilityCounts
    )
    top_findings: list[TopFinding] = Field(default_factory=list)
    attack_chains: list[AttackChain] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Remediation
# ---------------------------------------------------------------------------


class RemediationEntry(BaseModel):
    """A prioritized remediation recommendation."""

    priority: int = 0
    finding_id: str = ""
    title: str = ""
    description: str = ""
    effort: str = "medium"
    category: str = "patch"


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
    attack_surface: AttackSurface = Field(default_factory=AttackSurface)
    executive_summary: ExecutiveSummary = Field(default_factory=ExecutiveSummary)
    remediation: list[RemediationEntry] = Field(default_factory=list)
    metadata: AggregatedMetadata = Field(default_factory=AggregatedMetadata)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a JSON-compatible dict."""
        return self.model_dump(mode="json")
