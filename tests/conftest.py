"""Shared test fixtures."""

from __future__ import annotations

import asyncio
import importlib.util
import inspect

import pytest

from blhackbox.config import Settings
from blhackbox.models.base import Finding, ScanSession, Severity, Target


@pytest.fixture
def test_settings() -> Settings:
    """Settings with test-friendly defaults."""
    return Settings(
        neo4j_uri="bolt://localhost:7687",
        neo4j_user="neo4j",
        neo4j_password="testpass",
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

# Lightweight fallback for environments where the optional pytest-asyncio
# dependency cannot be installed (for example, offline CI sandboxes). The
# project still declares pytest-asyncio in pyproject.toml for normal dev setups.
_HAS_PYTEST_ASYNCIO = importlib.util.find_spec("pytest_asyncio") is not None

def pytest_addoption(parser: pytest.Parser) -> None:
    if not _HAS_PYTEST_ASYNCIO:
        parser.addini("asyncio_mode", "Fallback asyncio mode setting", default="auto")


def pytest_configure(config: pytest.Config) -> None:
    if not _HAS_PYTEST_ASYNCIO:
        config.addinivalue_line("markers", "asyncio: run async tests with asyncio")


def pytest_pyfunc_call(pyfuncitem: pytest.Function) -> bool | None:
    if _HAS_PYTEST_ASYNCIO:
        return None

    testfunction = pyfuncitem.obj
    if not inspect.iscoroutinefunction(testfunction):
        return None

    fixture_names = pyfuncitem._fixtureinfo.argnames  # noqa: SLF001
    funcargs = {name: pyfuncitem.funcargs[name] for name in fixture_names}
    asyncio.run(testfunction(**funcargs))
    return True
