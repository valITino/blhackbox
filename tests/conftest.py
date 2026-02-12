"""Shared test fixtures."""

from __future__ import annotations

import pytest

from blhackbox.config import Settings
from blhackbox.models.base import Finding, ScanSession, Severity, Target


@pytest.fixture
def test_settings() -> Settings:
    """Settings with test-friendly defaults."""
    return Settings(
        hexstrike_url="http://localhost:8888",
        neo4j_uri="bolt://localhost:7687",
        neo4j_user="neo4j",
        neo4j_password="testpass",
        openai_api_key="",
        anthropic_api_key="",
        results_dir="/tmp/blhackbox_test_results",
    )


@pytest.fixture
def sample_target() -> Target:
    return Target(value="example.com", target_type="domain")


@pytest.fixture
def sample_finding() -> Finding:
    return Finding(
        target="example.com",
        tool="network/nmap",
        category="network",
        title="Open Port 80",
        description="Port 80/tcp open http",
        severity=Severity.INFO,
        evidence="80/tcp open http Apache/2.4.41",
    )


@pytest.fixture
def sample_session(sample_target: Target, sample_finding: Finding) -> ScanSession:
    session = ScanSession(target=sample_target)
    session.add_finding(sample_finding)
    session.mark_tool_done("network/nmap")
    session.finish()
    return session
