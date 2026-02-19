"""Tests for AggregatedPayload Pydantic model validation (v2 architecture).

The v2 AggregatedPayload has a flat Findings container (not split into
ReconFindings / NetworkFindings / etc.) and uses AggregatedMetadata with
bytes-based size tracking.
"""

from __future__ import annotations

from blhackbox.models.aggregated_payload import (
    AggregatedMetadata,
    AggregatedPayload,
    EndpointEntry,
    ErrorLogEntry,
    Findings,
    HostEntry,
    HostPort,
    ServiceEntry,
    TechnologyEntry,
    VulnerabilityEntry,
)


class TestAggregatedPayload:
    def test_minimal_creation(self) -> None:
        payload = AggregatedPayload(
            session_id="test123",
            target="example.com",
        )
        assert payload.session_id == "test123"
        assert payload.target == "example.com"
        assert payload.findings.hosts == []
        assert payload.findings.subdomains == []
        assert payload.findings.vulnerabilities == []
        assert payload.error_log == []
        assert payload.metadata.warning == ""

    def test_full_creation(self) -> None:
        payload = AggregatedPayload(
            session_id="full-test",
            target="10.0.0.1",
            findings=Findings(
                hosts=[
                    HostEntry(
                        ip="10.0.0.1",
                        hostname="target.com",
                        ports=[
                            HostPort(
                                port=80,
                                service="http",
                                version="Apache/2.4.41",
                            )
                        ],
                    )
                ],
                ports=[HostPort(port=443, service="https")],
                services=[
                    ServiceEntry(
                        name="http",
                        version="Apache/2.4.41",
                        host="10.0.0.1",
                        port=80,
                    )
                ],
                vulnerabilities=[
                    VulnerabilityEntry(
                        id="CVE-2021-44228",
                        title="Log4Shell",
                        cvss=10.0,
                        severity="critical",
                        host="10.0.0.1",
                        port=443,
                        description="Log4Shell RCE",
                        references=["https://nvd.nist.gov/vuln/detail/CVE-2021-44228"],
                    )
                ],
                endpoints=[
                    EndpointEntry(url="/admin", method="GET", status_code=200)
                ],
                subdomains=["api.example.com", "mail.example.com"],
                technologies=[
                    TechnologyEntry(
                        name="Apache", version="2.4.41", category="web-server"
                    )
                ],
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
                total_raw_size_bytes=50000,
                compressed_size_bytes=2500,
                compression_ratio=0.05,
                ollama_model="llama3.3",
                duration_seconds=12.5,
            ),
        )
        assert len(payload.findings.vulnerabilities) == 1
        assert payload.findings.vulnerabilities[0].cvss == 10.0
        assert payload.findings.subdomains == ["api.example.com", "mail.example.com"]
        assert payload.error_log[0].security_relevance == "high"
        assert payload.metadata.compression_ratio == 0.05
        assert payload.metadata.total_raw_size_bytes == 50000

    def test_to_dict(self) -> None:
        payload = AggregatedPayload(
            session_id="dict-test",
            target="example.com",
        )
        data = payload.to_dict()
        assert isinstance(data, dict)
        assert data["session_id"] == "dict-test"
        assert data["target"] == "example.com"
        assert "findings" in data
        assert "error_log" in data
        assert "metadata" in data
        # Verify scan_timestamp is serialized
        assert "scan_timestamp" in data

    def test_to_dict_round_trip(self) -> None:
        """to_dict() should produce JSON-serializable data."""
        import json

        payload = AggregatedPayload(
            session_id="round-trip",
            target="10.0.0.1",
            findings=Findings(
                subdomains=["a.example.com"],
                vulnerabilities=[VulnerabilityEntry(id="CVE-2023-1234")],
            ),
        )
        data = payload.to_dict()
        json_str = json.dumps(data)
        assert '"CVE-2023-1234"' in json_str

    def test_scan_timestamp_auto_set(self) -> None:
        payload = AggregatedPayload(session_id="ts-test", target="example.com")
        assert payload.scan_timestamp is not None


class TestErrorLogEntry:
    def test_defaults(self) -> None:
        entry = ErrorLogEntry()
        assert entry.type == "other"
        assert entry.count == 0
        assert entry.locations == []
        assert entry.likely_cause == ""
        assert entry.security_relevance == "none"
        assert entry.security_note == ""

    def test_full_entry(self) -> None:
        entry = ErrorLogEntry(
            type="timeout",
            count=3,
            locations=["10.0.0.1:443"],
            likely_cause="WAF blocking probes",
            security_relevance="medium",
            security_note="Systematic timeouts suggest active WAF",
        )
        assert entry.type == "timeout"
        assert entry.count == 3
        assert entry.security_note == "Systematic timeouts suggest active WAF"


class TestVulnerabilityEntry:
    def test_minimal(self) -> None:
        vuln = VulnerabilityEntry()
        assert vuln.id == ""
        assert vuln.title == ""
        assert vuln.cvss == 0.0
        assert vuln.severity == "info"
        assert vuln.references == []

    def test_full(self) -> None:
        vuln = VulnerabilityEntry(
            id="CVE-2023-44487",
            title="HTTP/2 Rapid Reset",
            cvss=7.5,
            severity="high",
            host="10.0.0.1",
            port=443,
            description="HTTP/2 Rapid Reset attack",
            references=["https://nvd.nist.gov/vuln/detail/CVE-2023-44487"],
        )
        assert vuln.id == "CVE-2023-44487"
        assert len(vuln.references) == 1
        assert vuln.port == 443


class TestHostPort:
    def test_defaults(self) -> None:
        port = HostPort(port=443)
        assert port.service == ""
        assert port.version == ""
        assert port.state == "open"
        assert port.protocol == "tcp"
        assert port.banner == ""

    def test_full(self) -> None:
        port = HostPort(
            port=80,
            protocol="tcp",
            state="open",
            service="http",
            version="nginx/1.18",
            banner="Welcome to nginx",
        )
        assert port.port == 80
        assert port.banner == "Welcome to nginx"


class TestFindings:
    def test_empty_findings(self) -> None:
        findings = Findings()
        assert findings.hosts == []
        assert findings.ports == []
        assert findings.services == []
        assert findings.vulnerabilities == []
        assert findings.endpoints == []
        assert findings.subdomains == []
        assert findings.technologies == []

    def test_findings_with_all_sublists(self) -> None:
        findings = Findings(
            hosts=[HostEntry(ip="10.0.0.1")],
            ports=[HostPort(port=80)],
            services=[ServiceEntry(name="http")],
            vulnerabilities=[VulnerabilityEntry(id="CVE-2021-1234")],
            endpoints=[EndpointEntry(url="/api")],
            subdomains=["sub.example.com"],
            technologies=[TechnologyEntry(name="nginx")],
        )
        assert len(findings.hosts) == 1
        assert len(findings.ports) == 1
        assert len(findings.services) == 1
        assert len(findings.vulnerabilities) == 1
        assert len(findings.endpoints) == 1
        assert len(findings.subdomains) == 1
        assert len(findings.technologies) == 1


class TestAggregatedMetadata:
    def test_defaults(self) -> None:
        meta = AggregatedMetadata()
        assert meta.tools_run == []
        assert meta.total_raw_size_bytes == 0
        assert meta.compressed_size_bytes == 0
        assert meta.compression_ratio == 0.0
        assert meta.ollama_model == ""
        assert meta.duration_seconds == 0.0
        assert meta.warning == ""

    def test_warning(self) -> None:
        meta = AggregatedMetadata(warning="Ollama unreachable")
        assert meta.warning == "Ollama unreachable"
        assert meta.tools_run == []

    def test_full_metadata(self) -> None:
        meta = AggregatedMetadata(
            tools_run=["nmap", "nikto", "subfinder"],
            total_raw_size_bytes=100000,
            compressed_size_bytes=5000,
            compression_ratio=0.05,
            ollama_model="llama3.3",
            duration_seconds=25.3,
            warning="",
        )
        assert len(meta.tools_run) == 3
        assert meta.compression_ratio == 0.05


class TestSubModels:
    def test_host_entry(self) -> None:
        host = HostEntry(
            ip="192.168.1.1",
            hostname="server.local",
            ports=[HostPort(port=22, service="ssh")],
        )
        assert host.ip == "192.168.1.1"
        assert host.hostname == "server.local"
        assert len(host.ports) == 1

    def test_service_entry(self) -> None:
        svc = ServiceEntry(name="ssh", version="OpenSSH 8.4", host="10.0.0.1", port=22)
        assert svc.name == "ssh"
        assert svc.port == 22

    def test_endpoint_entry(self) -> None:
        ep = EndpointEntry(url="/admin", method="POST", status_code=403, content_length=512)
        assert ep.url == "/admin"
        assert ep.method == "POST"
        assert ep.status_code == 403

    def test_technology_entry(self) -> None:
        tech = TechnologyEntry(name="WordPress", version="6.2", category="cms")
        assert tech.name == "WordPress"
        assert tech.category == "cms"
