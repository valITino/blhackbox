"""Tests for the blhackbox Ollama MCP server (v2 architecture).

Tests the ollama_mcp_server.py which acts as a thin orchestrator that calls
3 agent containers (Ingestion, Processing, Synthesis) via HTTP and assembles
the final AggregatedPayload.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

# Ensure the mcp_servers directory is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "mcp_servers"))

from mcp_servers.ollama_mcp_server import (  # noqa: E402
    _TOOLS,
    _build_error_log,
    _build_findings,
    _call_agent,
    _looks_like_ip,
)

# ---------------------------------------------------------------------------
# Tool definitions
# ---------------------------------------------------------------------------


class TestToolDefinitions:
    def test_has_process_scan_results_tool(self) -> None:
        names = [t.name for t in _TOOLS]
        assert "process_scan_results" in names

    def test_only_one_tool(self) -> None:
        assert len(_TOOLS) == 1

    def test_tool_schema(self) -> None:
        tool = next(t for t in _TOOLS if t.name == "process_scan_results")
        schema = tool.inputSchema
        assert "raw_outputs" in schema["properties"]
        assert "target" in schema["properties"]
        assert "session_id" in schema["properties"]
        assert set(schema["required"]) == {"raw_outputs", "target", "session_id"}

    def test_tool_has_description(self) -> None:
        tool = _TOOLS[0]
        assert tool.description
        assert "agent" in tool.description.lower()

    def test_tool_description_mentions_containers(self) -> None:
        tool = _TOOLS[0]
        assert "container" in tool.description.lower()


# ---------------------------------------------------------------------------
# _looks_like_ip
# ---------------------------------------------------------------------------


class TestLooksLikeIP:
    def test_valid_ip(self) -> None:
        assert _looks_like_ip("192.168.1.1") is True
        assert _looks_like_ip("10.0.0.1") is True
        assert _looks_like_ip("0.0.0.0") is True
        assert _looks_like_ip("255.255.255.255") is True

    def test_invalid_ip(self) -> None:
        assert _looks_like_ip("example.com") is False
        assert _looks_like_ip("256.1.1.1") is False
        assert _looks_like_ip("not.an.ip") is False
        assert _looks_like_ip("1.2.3") is False
        assert _looks_like_ip("1.2.3.4.5") is False
        assert _looks_like_ip("") is False


# ---------------------------------------------------------------------------
# _call_agent
# ---------------------------------------------------------------------------


class TestCallAgent:
    @pytest.mark.asyncio
    async def test_successful_call(self) -> None:
        mock_response = MagicMock()
        mock_response.json.return_value = {"subdomains": ["a.example.com"]}
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response

        warnings: list[str] = []
        result = await _call_agent(
            mock_client, "http://agent:8001", "data",
            "session1", "example.com", "TestAgent", warnings,
        )
        assert result == {"subdomains": ["a.example.com"]}
        assert warnings == []

    @pytest.mark.asyncio
    async def test_connect_error(self) -> None:
        mock_client = AsyncMock()
        mock_client.post.side_effect = httpx.ConnectError("unreachable")

        warnings: list[str] = []
        result = await _call_agent(
            mock_client, "http://agent:8001", "data",
            "session1", "example.com", "TestAgent", warnings,
        )
        assert result == {}
        assert len(warnings) == 1
        assert "unreachable" in warnings[0]

    @pytest.mark.asyncio
    async def test_http_error(self) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 503

        mock_client = AsyncMock()
        mock_client.post.side_effect = httpx.HTTPStatusError(
            "error", request=MagicMock(), response=mock_response,
        )

        warnings: list[str] = []
        result = await _call_agent(
            mock_client, "http://agent:8001", "data",
            "session1", "example.com", "TestAgent", warnings,
        )
        assert result == {}
        assert len(warnings) == 1
        assert "HTTP" in warnings[0]


# ---------------------------------------------------------------------------
# _build_findings
# ---------------------------------------------------------------------------


class TestBuildFindings:
    def test_empty_data(self) -> None:
        """All empty agent outputs should produce an empty Findings."""
        warnings: list[str] = []
        result = _build_findings({}, {}, {}, warnings)
        assert result.hosts == []
        assert result.ports == []
        assert result.services == []
        assert result.vulnerabilities == []
        assert result.endpoints == []
        assert result.subdomains == []
        assert result.technologies == []

    def test_synthesis_output_preferred(self) -> None:
        """_build_findings prefers synthesis output > processing > ingestion."""
        warnings: list[str] = []
        synthesis = {
            "findings": {
                "subdomains": ["from-synthesis.example.com"],
            }
        }
        processing = {
            "findings": {
                "subdomains": ["from-processing.example.com"],
            }
        }
        ingestion = {
            "subdomains": ["from-ingestion.example.com"],
        }
        result = _build_findings(synthesis, processing, ingestion, warnings)
        assert "from-synthesis.example.com" in result.subdomains

    def test_falls_back_to_processing(self) -> None:
        warnings: list[str] = []
        processing = {
            "findings": {
                "subdomains": ["from-processing.example.com"],
            }
        }
        result = _build_findings({}, processing, {}, warnings)
        assert "from-processing.example.com" in result.subdomains

    def test_falls_back_to_ingestion(self) -> None:
        warnings: list[str] = []
        ingestion = {
            "subdomains": ["from-ingestion.example.com"],
        }
        result = _build_findings({}, {}, ingestion, warnings)
        assert "from-ingestion.example.com" in result.subdomains

    def test_malformed_findings_falls_back(self) -> None:
        """If findings data has wrong types, it should not crash."""
        warnings: list[str] = []
        synthesis = {
            "findings": {
                "subdomains": "not a list",
                "hosts": "also not a list",
            }
        }
        result = _build_findings(synthesis, {}, {}, warnings)
        # Should fall back gracefully without crashing
        assert result is not None


# ---------------------------------------------------------------------------
# _build_error_log
# ---------------------------------------------------------------------------


class TestBuildErrorLog:
    def test_valid_entries(self) -> None:
        entries = _build_error_log(
            {"error_log": [
                {"type": "timeout", "count": 3, "locations": ["10.0.0.1"]},
            ]},
            {},
        )
        assert len(entries) == 1
        assert entries[0].type == "timeout"
        assert entries[0].count == 3

    def test_falls_back_to_processing(self) -> None:
        entries = _build_error_log(
            {},
            {"error_log": [
                {"type": "dns_failure", "count": 1, "locations": ["ns1.example.com"]},
            ]},
        )
        assert len(entries) == 1
        assert entries[0].type == "dns_failure"

    def test_malformed_entry_skipped(self) -> None:
        entries = _build_error_log(
            {"error_log": [
                {"type": "timeout", "count": 3},
                "not a dict",  # should be skipped
            ]},
            {},
        )
        assert len(entries) == 1
        assert entries[0].type == "timeout"

    def test_empty_error_log(self) -> None:
        entries = _build_error_log({}, {})
        assert entries == []

    def test_entry_with_all_fields(self) -> None:
        entries = _build_error_log(
            {"error_log": [
                {
                    "type": "rate_limit",
                    "count": 10,
                    "locations": ["10.0.0.1:443", "10.0.0.1:8080"],
                    "likely_cause": "WAF rate limiting",
                    "security_relevance": "high",
                    "security_note": "Active rate limiting suggests WAF presence",
                },
            ]},
            {},
        )
        assert len(entries) == 1
        assert entries[0].security_relevance == "high"
        assert entries[0].security_note == "Active rate limiting suggests WAF presence"
