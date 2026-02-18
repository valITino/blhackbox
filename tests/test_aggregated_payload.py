"""Tests for AggregatedPayload Pydantic model validation."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from blhackbox.models.aggregated_payload import (
    AggregatedMetadata,
    AggregatedPayload,
    ErrorLogEntry,
    HostEntry,
    HostPort,
    MainFindings,
    NetworkFindings,
    ReconFindings,
    VulnFindings,
    VulnerabilityEntry,
    WebFindings,
)


class TestAggregatedPayload:
    def test_minimal_creation(self) -> None:
        payload = AggregatedPayload(
            session_id="test123",
            target="example.com",
        )
        assert payload.session_id == "test123"
        assert payload.target == "example.com"
        assert payload.main_findings.recon.subdomains == []
        assert payload.error_log == []
        assert payload.metadata.warning == ""

    def test_full_creation(self) -> None:
        payload = AggregatedPayload(
            session_id="full-test",
            target="10.0.0.1",
            main_findings=MainFindings(
                recon=ReconFindings(
                    subdomains=["api.example.com"],
                    ips=["10.0.0.1"],
                    technologies=["Apache/2.4.41"],
                ),
                network=NetworkFindings(
                    hosts=[
                        HostEntry(
                            ip="10.0.0.1",
                            ports=[HostPort(port=80, service="http", version="Apache/2.4.41")],
                        )
                    ]
                ),
                vulnerabilities=VulnFindings(
                    vulnerabilities=[
                        VulnerabilityEntry(
                            cve="CVE-2021-44228",
                            cvss=10.0,
                            severity="critical",
                            host="10.0.0.1",
                            description="Log4Shell",
                        )
                    ]
                ),
                web=WebFindings(
                    endpoints=["/admin", "/api"],
                    cms="WordPress 6.2",
                ),
            ),
            error_log=[
                ErrorLogEntry(
                    type="timeout",
                    count=5,
                    locations=["10.0.0.1:8080"],
                    likely_cause="Firewall",
                    security_relevance="high",
                    security_note="Possible WAF",
                )
            ],
            metadata=AggregatedMetadata(
                tools_run=["nmap", "nikto"],
                agents_run=["ReconAgent", "NetworkAgent"],
                total_raw_lines_processed=1000,
                compressed_to_lines=50,
                compression_ratio=0.05,
                ollama_model_used="llama3.3",
                aggregation_duration_seconds=12.5,
            ),
        )
        assert len(payload.main_findings.vulnerabilities.vulnerabilities) == 1
        assert payload.main_findings.vulnerabilities.vulnerabilities[0].cvss == 10.0
        assert payload.error_log[0].security_relevance == "high"
        assert payload.metadata.compression_ratio == 0.05

    def test_to_dict(self) -> None:
        payload = AggregatedPayload(
            session_id="dict-test",
            target="example.com",
        )
        data = payload.to_dict()
        assert isinstance(data, dict)
        assert data["session_id"] == "dict-test"
        assert data["target"] == "example.com"
        assert "main_findings" in data
        assert "error_log" in data
        assert "metadata" in data

    def test_error_log_entry_defaults(self) -> None:
        entry = ErrorLogEntry()
        assert entry.type == "other"
        assert entry.count == 0
        assert entry.locations == []
        assert entry.security_relevance == "none"

    def test_host_port_defaults(self) -> None:
        port = HostPort(port=443)
        assert port.service == ""
        assert port.version == ""
        assert port.state == "open"

    def test_metadata_warning(self) -> None:
        meta = AggregatedMetadata(warning="Ollama unreachable")
        assert meta.warning == "Ollama unreachable"
        assert meta.tools_run == []


class TestVulnerabilityEntry:
    def test_minimal(self) -> None:
        vuln = VulnerabilityEntry()
        assert vuln.cve == ""
        assert vuln.cvss == 0.0
        assert vuln.severity == "info"

    def test_full(self) -> None:
        vuln = VulnerabilityEntry(
            cve="CVE-2023-44487",
            cvss=7.5,
            severity="high",
            host="10.0.0.1",
            description="HTTP/2 Rapid Reset",
            references=["https://nvd.nist.gov/vuln/detail/CVE-2023-44487"],
        )
        assert vuln.cve == "CVE-2023-44487"
        assert len(vuln.references) == 1
