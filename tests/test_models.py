"""Tests for data models."""

from __future__ import annotations

from blhackbox.models.base import Finding, ScanSession, Severity, Target
from blhackbox.models.hexstrike import (
    HexStrikeAgentResponse,
    HexStrikeAnalysisResponse,
    HexStrikeToolResponse,
)
from blhackbox.models.graph import (
    DomainNode,
    FindingNode,
    GraphRelationship,
    IPAddressNode,
    PortNode,
    RelationshipType,
    ServiceNode,
    VulnerabilityNode,
)


class TestTarget:
    def test_create_target(self) -> None:
        t = Target(value="example.com")
        assert t.value == "example.com"
        assert t.target_type == "auto"
        assert str(t) == "example.com"

    def test_target_with_type(self) -> None:
        t = Target(value="192.168.1.1", target_type="ip")
        assert t.target_type == "ip"


class TestFinding:
    def test_create_finding(self) -> None:
        f = Finding(
            target="example.com",
            tool="nmap",
            title="Open Port",
            severity=Severity.HIGH,
        )
        assert f.target == "example.com"
        assert f.severity == Severity.HIGH
        assert f.id  # auto-generated
        assert f.timestamp

    def test_finding_defaults(self) -> None:
        f = Finding(target="x", tool="t", title="t")
        assert f.severity == Severity.INFO
        assert f.description == ""
        assert f.evidence == ""


class TestScanSession:
    def test_session_lifecycle(self, sample_target: Target) -> None:
        session = ScanSession(target=sample_target)
        assert session.status == "running"
        assert session.finished_at is None

        session.mark_tool_done("nmap")
        assert "nmap" in session.tools_executed

        # Duplicate mark should not create duplicate
        session.mark_tool_done("nmap")
        assert session.tools_executed.count("nmap") == 1

        f = Finding(target="example.com", tool="nmap", title="test", severity=Severity.LOW)
        session.add_finding(f)
        assert len(session.findings) == 1

        session.finish()
        assert session.status == "completed"
        assert session.finished_at is not None
        assert session.duration_seconds is not None
        assert session.duration_seconds >= 0

    def test_severity_counts(self, sample_session: ScanSession) -> None:
        counts = sample_session.severity_counts
        assert isinstance(counts, dict)
        assert counts.get("info", 0) >= 1


class TestHexStrikeModels:
    def test_tool_response(self) -> None:
        r = HexStrikeToolResponse(
            success=True, tool="nmap", category="network", output={"ports": [80]}
        )
        assert not r.has_errors
        assert r.output == {"ports": [80]}

    def test_tool_response_with_errors(self) -> None:
        r = HexStrikeToolResponse(success=False, errors=["timeout"])
        assert r.has_errors

    def test_analysis_response(self) -> None:
        r = HexStrikeAnalysisResponse(
            target="example.com",
            results={"score": 5},
            risk_score=5.0,
        )
        assert r.risk_score == 5.0

    def test_agent_response(self) -> None:
        r = HexStrikeAgentResponse(
            agent="bug_bounty", target="example.com", results={"found": True}
        )
        assert not r.has_errors


class TestGraphModels:
    def test_domain_node(self) -> None:
        d = DomainNode(name="example.com")
        assert d.label == "Domain"
        assert d.merge_key == "name"
        assert d.merge_value == "example.com"
        props = d.to_cypher_properties()
        assert props["name"] == "example.com"
        assert "created_at" in props

    def test_ip_node(self) -> None:
        ip = IPAddressNode(address="1.2.3.4")
        assert ip.label == "IPAddress"
        assert ip.merge_value == "1.2.3.4"

    def test_port_node(self) -> None:
        p = PortNode(number=443, protocol="tcp")
        assert p.merge_value == 443
        assert p.properties["protocol"] == "tcp"

    def test_service_node(self) -> None:
        s = ServiceNode(name="http", version="2.4.41")
        assert s.properties["version"] == "2.4.41"

    def test_vulnerability_node(self) -> None:
        v = VulnerabilityNode(identifier="CVE-2021-44228", severity="critical", title="Log4Shell")
        assert v.merge_value == "CVE-2021-44228"
        assert v.properties["severity"] == "critical"

    def test_finding_node(self) -> None:
        f = FindingNode(
            finding_id="abc123",
            tool="nuclei",
            title="XSS Found",
            severity="high",
        )
        assert f.merge_value == "abc123"
        assert f.properties["tool"] == "nuclei"

    def test_relationship(self) -> None:
        d = DomainNode(name="example.com")
        ip = IPAddressNode(address="1.2.3.4")
        rel = GraphRelationship(
            source=d,
            target=ip,
            rel_type=RelationshipType.RESOLVES_TO,
        )
        assert rel.rel_type == RelationshipType.RESOLVES_TO
        assert rel.source.merge_value == "example.com"
        assert rel.target.merge_value == "1.2.3.4"
