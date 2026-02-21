"""Tests for AggregatedPayload Pydantic model validation (v2 architecture).

The v2 AggregatedPayload has a flat Findings container (not split into
ReconFindings / NetworkFindings / etc.) and uses AggregatedMetadata with
bytes-based size tracking.
"""

from __future__ import annotations

from blhackbox.models.aggregated_payload import (
    AggregatedMetadata,
    AggregatedPayload,
    AttackChain,
    AttackSurface,
    CredentialEntry,
    DNSRecordEntry,
    EndpointEntry,
    ErrorLogEntry,
    ExecutiveSummary,
    Findings,
    HostEntry,
    HostPort,
    HTTPHeaderEntry,
    RemediationEntry,
    ServiceEntry,
    SSLCertEntry,
    TechnologyEntry,
    TopFinding,
    VulnerabilityCounts,
    VulnerabilityEntry,
    WhoisRecord,
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
        assert payload.findings.ssl_certs == []
        assert payload.findings.credentials == []
        assert payload.findings.http_headers == []
        assert payload.findings.dns_records == []
        assert payload.error_log == []
        assert payload.attack_surface.external_services == 0
        assert payload.executive_summary.risk_level == "info"
        assert payload.remediation == []
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
                        os="Linux 5.4",
                        ports=[
                            HostPort(
                                port=80,
                                service="http",
                                version="Apache/2.4.41",
                                nse_scripts={"http-title": "Welcome"},
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
                        cpe="cpe:/a:apache:http_server:2.4.41",
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
                        evidence="JNDI lookup triggered",
                        tool_source="nuclei",
                    )
                ],
                endpoints=[
                    EndpointEntry(url="/admin", method="GET", status_code=200, redirect="")
                ],
                subdomains=["api.example.com", "mail.example.com"],
                technologies=[
                    TechnologyEntry(
                        name="Apache", version="2.4.41", category="web-server"
                    )
                ],
                ssl_certs=[
                    SSLCertEntry(
                        host="example.com",
                        port=443,
                        issuer="Let's Encrypt",
                        subject="example.com",
                        not_after="2025-01-01",
                        issues=["expired"],
                    )
                ],
                credentials=[
                    CredentialEntry(
                        host="10.0.0.1",
                        port=22,
                        service="ssh",
                        username="admin",
                        password="admin",
                        tool_source="hydra",
                    )
                ],
                http_headers=[
                    HTTPHeaderEntry(
                        host="example.com",
                        port=80,
                        missing_security_headers=["X-Frame-Options", "CSP"],
                        server="Apache/2.4.41",
                    )
                ],
                dns_records=[
                    DNSRecordEntry(type="A", name="example.com", value="10.0.0.1")
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
            attack_surface=AttackSurface(
                external_services=3,
                web_applications=1,
                login_panels=1,
                high_value_targets=["Admin panel at /admin"],
            ),
            executive_summary=ExecutiveSummary(
                risk_level="critical",
                headline="Log4Shell RCE found",
                summary="Critical vulnerability discovered.",
                total_vulnerabilities=VulnerabilityCounts(critical=1),
                top_findings=[
                    TopFinding(
                        title="Log4Shell",
                        severity="critical",
                        impact="Full RCE",
                        exploitability="easy",
                        remediation="Upgrade Log4j",
                    )
                ],
                attack_chains=[
                    AttackChain(
                        name="RCE chain",
                        steps=["1. JNDI lookup", "2. RCE"],
                        overall_severity="critical",
                    )
                ],
            ),
            remediation=[
                RemediationEntry(
                    priority=1,
                    finding_id="CVE-2021-44228",
                    title="Upgrade Log4j",
                    description="Upgrade to Log4j 2.17.1+",
                    effort="low",
                    category="patch",
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
        assert payload.findings.vulnerabilities[0].tool_source == "nuclei"
        assert payload.findings.hosts[0].os == "Linux 5.4"
        assert payload.findings.hosts[0].ports[0].nse_scripts == {"http-title": "Welcome"}
        assert payload.findings.services[0].cpe == "cpe:/a:apache:http_server:2.4.41"
        assert len(payload.findings.ssl_certs) == 1
        assert payload.findings.ssl_certs[0].issues == ["expired"]
        assert len(payload.findings.credentials) == 1
        assert payload.findings.credentials[0].username == "admin"
        assert len(payload.findings.http_headers) == 1
        assert len(payload.findings.dns_records) == 1
        assert payload.attack_surface.external_services == 3
        assert payload.executive_summary.risk_level == "critical"
        assert len(payload.executive_summary.top_findings) == 1
        assert len(payload.executive_summary.attack_chains) == 1
        assert len(payload.remediation) == 1
        assert payload.remediation[0].effort == "low"
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
        assert "attack_surface" in data
        assert "executive_summary" in data
        assert "remediation" in data
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
        assert vuln.evidence == ""
        assert vuln.tool_source == ""
        assert vuln.likely_false_positive is False

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
            evidence="Confirmed via crafted HTTP/2 frames",
            tool_source="nuclei",
        )
        assert vuln.id == "CVE-2023-44487"
        assert len(vuln.references) == 1
        assert vuln.port == 443
        assert vuln.evidence == "Confirmed via crafted HTTP/2 frames"
        assert vuln.tool_source == "nuclei"


class TestHostPort:
    def test_defaults(self) -> None:
        port = HostPort(port=443)
        assert port.service == ""
        assert port.version == ""
        assert port.state == "open"
        assert port.protocol == "tcp"
        assert port.banner == ""
        assert port.nse_scripts == {}

    def test_full(self) -> None:
        port = HostPort(
            port=80,
            protocol="tcp",
            state="open",
            service="http",
            version="nginx/1.18",
            banner="Welcome to nginx",
            nse_scripts={"http-title": "Default Page"},
        )
        assert port.port == 80
        assert port.banner == "Welcome to nginx"
        assert port.nse_scripts == {"http-title": "Default Page"}


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
        assert findings.ssl_certs == []
        assert findings.credentials == []
        assert findings.http_headers == []
        assert findings.dns_records == []

    def test_findings_with_all_sublists(self) -> None:
        findings = Findings(
            hosts=[HostEntry(ip="10.0.0.1")],
            ports=[HostPort(port=80)],
            services=[ServiceEntry(name="http")],
            vulnerabilities=[VulnerabilityEntry(id="CVE-2021-1234")],
            endpoints=[EndpointEntry(url="/api")],
            subdomains=["sub.example.com"],
            technologies=[TechnologyEntry(name="nginx")],
            ssl_certs=[SSLCertEntry(host="example.com")],
            credentials=[CredentialEntry(host="10.0.0.1", service="ssh")],
            http_headers=[HTTPHeaderEntry(host="example.com", port=80)],
            dns_records=[DNSRecordEntry(type="A", name="example.com", value="10.0.0.1")],
        )
        assert len(findings.hosts) == 1
        assert len(findings.ports) == 1
        assert len(findings.services) == 1
        assert len(findings.vulnerabilities) == 1
        assert len(findings.endpoints) == 1
        assert len(findings.subdomains) == 1
        assert len(findings.technologies) == 1
        assert len(findings.ssl_certs) == 1
        assert len(findings.credentials) == 1
        assert len(findings.http_headers) == 1
        assert len(findings.dns_records) == 1


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
            os="Linux 5.4",
            ports=[HostPort(port=22, service="ssh")],
        )
        assert host.ip == "192.168.1.1"
        assert host.hostname == "server.local"
        assert host.os == "Linux 5.4"
        assert len(host.ports) == 1

    def test_service_entry(self) -> None:
        svc = ServiceEntry(
            name="ssh", version="OpenSSH 8.4", host="10.0.0.1", port=22,
            cpe="cpe:/a:openbsd:openssh:8.4",
        )
        assert svc.name == "ssh"
        assert svc.port == 22
        assert svc.cpe == "cpe:/a:openbsd:openssh:8.4"

    def test_endpoint_entry(self) -> None:
        ep = EndpointEntry(url="/admin", method="POST", status_code=403, content_length=512)
        assert ep.url == "/admin"
        assert ep.method == "POST"
        assert ep.status_code == 403
        assert ep.redirect == ""

    def test_technology_entry(self) -> None:
        tech = TechnologyEntry(name="WordPress", version="6.2", category="cms")
        assert tech.name == "WordPress"
        assert tech.category == "cms"

    def test_ssl_cert_entry(self) -> None:
        cert = SSLCertEntry(
            host="example.com",
            port=443,
            issuer="Let's Encrypt",
            subject="example.com",
            san=["example.com", "www.example.com"],
            not_after="2025-01-01",
            issues=["expired"],
        )
        assert cert.issuer == "Let's Encrypt"
        assert cert.issues == ["expired"]
        assert len(cert.san) == 2

    def test_credential_entry(self) -> None:
        cred = CredentialEntry(
            host="10.0.0.1", port=22, service="ssh",
            username="root", password="toor", tool_source="hydra",
        )
        assert cred.username == "root"
        assert cred.tool_source == "hydra"

    def test_http_header_entry(self) -> None:
        hdr = HTTPHeaderEntry(
            host="example.com", port=443,
            missing_security_headers=["CSP", "HSTS"],
            server="nginx/1.18",
        )
        assert len(hdr.missing_security_headers) == 2
        assert hdr.server == "nginx/1.18"

    def test_dns_record_entry(self) -> None:
        rec = DNSRecordEntry(type="MX", name="example.com", value="mail.example.com", priority=10)
        assert rec.type == "MX"
        assert rec.priority == 10

    def test_whois_record(self) -> None:
        whois = WhoisRecord(
            domain="example.com", registrar="GoDaddy",
            creation_date="2020-01-01", nameservers=["ns1.example.com"],
        )
        assert whois.registrar == "GoDaddy"
        assert len(whois.nameservers) == 1


class TestAttackSurface:
    def test_defaults(self) -> None:
        surface = AttackSurface()
        assert surface.external_services == 0
        assert surface.web_applications == 0
        assert surface.high_value_targets == []

    def test_full(self) -> None:
        surface = AttackSurface(
            external_services=5,
            web_applications=2,
            login_panels=1,
            api_endpoints=3,
            outdated_software=2,
            default_credentials=1,
            missing_security_headers=4,
            ssl_issues=1,
            high_value_targets=["Admin panel", "phpMyAdmin"],
        )
        assert surface.external_services == 5
        assert len(surface.high_value_targets) == 2


class TestExecutiveSummary:
    def test_defaults(self) -> None:
        summary = ExecutiveSummary()
        assert summary.risk_level == "info"
        assert summary.headline == ""
        assert summary.top_findings == []
        assert summary.attack_chains == []
        assert summary.total_vulnerabilities.critical == 0

    def test_full(self) -> None:
        summary = ExecutiveSummary(
            risk_level="critical",
            headline="Critical RCE found",
            summary="A critical vulnerability was discovered.",
            total_vulnerabilities=VulnerabilityCounts(critical=1, high=2),
            top_findings=[
                TopFinding(title="RCE", severity="critical", impact="Full compromise")
            ],
            attack_chains=[
                AttackChain(name="Chain 1", steps=["Step 1", "Step 2"], overall_severity="critical")
            ],
        )
        assert summary.risk_level == "critical"
        assert summary.total_vulnerabilities.high == 2
        assert len(summary.top_findings) == 1
        assert len(summary.attack_chains) == 1


class TestRemediationEntry:
    def test_defaults(self) -> None:
        rem = RemediationEntry()
        assert rem.priority == 0
        assert rem.effort == "medium"
        assert rem.category == "patch"

    def test_full(self) -> None:
        rem = RemediationEntry(
            priority=1,
            finding_id="CVE-2021-44228",
            title="Upgrade Log4j",
            description="Upgrade to 2.17.1+",
            effort="low",
            category="patch",
        )
        assert rem.priority == 1
        assert rem.category == "patch"
