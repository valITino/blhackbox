"""Tests for the blhackbox aggregator MCP server."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

# Ensure the mcp_servers directory is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "mcp_servers"))

from mcp_servers.blhackbox_aggregator_mcp import (
    _classify_raw_outputs,
    _do_aggregate,
    _looks_like_ip,
    _TOOLS,
)


class TestToolDefinitions:
    def test_has_aggregate_tool(self) -> None:
        names = [t.name for t in _TOOLS]
        assert "aggregate_pentest_data" in names

    def test_aggregate_tool_schema(self) -> None:
        tool = next(t for t in _TOOLS if t.name == "aggregate_pentest_data")
        schema = tool.inputSchema
        assert "raw_outputs" in schema["properties"]
        assert "target" in schema["properties"]
        assert "session_id" in schema["properties"]
        assert set(schema["required"]) == {"raw_outputs", "target", "session_id"}


class TestClassifyRawOutputs:
    def test_nmap_classified_as_network(self) -> None:
        classified = _classify_raw_outputs({"nmap": "scan output"})
        assert "nmap" in classified["network"].lower() or "scan output" in classified["network"]

    def test_nikto_classified_as_web(self) -> None:
        classified = _classify_raw_outputs({"nikto": "web scan"})
        assert "web scan" in classified["web"]

    def test_subfinder_classified_as_recon(self) -> None:
        classified = _classify_raw_outputs({"subfinder": "subdomains"})
        assert "subdomains" in classified["recon"]

    def test_nuclei_classified_as_vuln(self) -> None:
        classified = _classify_raw_outputs({"nuclei": "CVE findings"})
        assert "CVE findings" in classified["vuln"]

    def test_all_goes_to_all(self) -> None:
        classified = _classify_raw_outputs({"any_tool": "any output"})
        assert "any output" in classified["all"]

    def test_unknown_tool_goes_to_recon_and_web(self) -> None:
        classified = _classify_raw_outputs({"unknown_scanner": "output"})
        assert "output" in classified["recon"]
        assert "output" in classified["web"]


class TestLooksLikeIP:
    def test_valid_ip(self) -> None:
        assert _looks_like_ip("192.168.1.1") is True
        assert _looks_like_ip("10.0.0.1") is True

    def test_invalid_ip(self) -> None:
        assert _looks_like_ip("example.com") is False
        assert _looks_like_ip("256.1.1.1") is False
        assert _looks_like_ip("not.an.ip") is False


class TestDoAggregate:
    @pytest.mark.asyncio
    async def test_empty_inputs(self) -> None:
        """Aggregation with empty inputs returns valid degraded payload."""
        result_json = await _do_aggregate({
            "raw_outputs": {},
            "target": "example.com",
            "session_id": "test-session",
        })
        result = json.loads(result_json)
        assert result["session_id"] == "test-session"
        assert result["target"] == "example.com"
        assert "main_findings" in result
        assert "error_log" in result
        assert "metadata" in result

    @pytest.mark.asyncio
    async def test_ollama_unreachable_degraded_response(self) -> None:
        """When Ollama is unreachable, still returns a valid AggregatedPayload."""
        result_json = await _do_aggregate({
            "raw_outputs": {"nmap": "PORT   STATE SERVICE\n80/tcp open  http"},
            "target": "10.0.0.1",
            "session_id": "degraded-test",
        })
        result = json.loads(result_json)
        assert result["session_id"] == "degraded-test"
        assert "main_findings" in result
        # Even if Ollama is unreachable, the payload should be valid JSON
        assert isinstance(result["metadata"]["tools_run"], list)
