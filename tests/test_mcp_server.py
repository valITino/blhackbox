"""Tests for the MCP server tool definitions and dispatch (v2 architecture).

The blhackbox MCP server exposes orchestrated workflows (run_tool,
query_graph, get_findings, list_tools, generate_report, list_templates,
get_template) plus screenshot tools (take_screenshot, take_element_screenshot,
list_screenshots, annotate_screenshot).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from blhackbox.mcp.server import (
    _TOOLS,
    _do_aggregate_results,
    _do_generate_report,
    handle_list_tools,
)


class TestMCPToolDefinitions:
    """Verify the MCP tools are correctly defined."""

    def test_all_tools_have_names(self) -> None:
        for tool in _TOOLS:
            assert tool.name, f"Tool missing name: {tool}"

    def test_all_tools_have_descriptions(self) -> None:
        for tool in _TOOLS:
            assert tool.description, f"Tool {tool.name} missing description"

    def test_all_tools_have_input_schema(self) -> None:
        for tool in _TOOLS:
            assert tool.inputSchema is not None

    def test_expected_tools_present(self) -> None:
        names = {t.name for t in _TOOLS}
        expected = {
            "run_tool", "query_graph", "get_findings",
            "list_tools", "search_tools", "get_tool_details", "recommend_workflow",
            "generate_report", "list_templates",
            "get_template", "take_screenshot", "take_element_screenshot",
            "list_screenshots", "annotate_screenshot",
            "aggregate_results", "get_payload_schema",
        }
        assert expected == names

    def test_run_tool_requires_category_tool_params(self) -> None:
        rt = next(t for t in _TOOLS if t.name == "run_tool")
        assert set(rt.inputSchema["required"]) == {"category", "tool", "params"}

    def test_generate_report_requires_session_id(self) -> None:
        report = next(t for t in _TOOLS if t.name == "generate_report")
        assert "session_id" in report.inputSchema["required"]

    def test_query_graph_requires_cypher(self) -> None:
        qg = next(t for t in _TOOLS if t.name == "query_graph")
        assert "cypher" in qg.inputSchema["required"]


class TestMCPListTools:
    async def test_list_tools_returns_all(self) -> None:
        tools = await handle_list_tools()
        assert len(tools) == 16
        names = {t.name for t in tools}
        assert "run_tool" in names
        assert "list_templates" in names
        assert "get_template" in names
        assert "take_screenshot" in names
        assert "annotate_screenshot" in names

class TestMCPDiscoveryTools:
    def test_search_tools_schema(self) -> None:
        tool = next(t for t in _TOOLS if t.name == "search_tools")
        props = tool.inputSchema["properties"]
        assert {"query", "limit", "phase", "category"}.issubset(props)
        assert "max_risk" not in props

    def test_get_tool_details_requires_tool(self) -> None:
        tool = next(t for t in _TOOLS if t.name == "get_tool_details")
        assert tool.inputSchema["required"] == ["tool"]

    def test_recommend_workflow_requires_workflow(self) -> None:
        tool = next(t for t in _TOOLS if t.name == "recommend_workflow")
        assert tool.inputSchema["required"] == ["workflow"]


class TestGenerateReportRoundTrip:
    """End-to-end: aggregate_results persists an AggregatedPayload, and
    generate_report must consume that same file successfully.
    """

    async def test_aggregate_then_generate_report(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from blhackbox.config import settings

        monkeypatch.setattr(settings, "results_dir", tmp_path / "sessions")
        monkeypatch.setattr(settings, "reports_dir", tmp_path / "reports")

        agg = await _do_aggregate_results({
            "payload": {
                "session_id": "e2e-001",
                "target": "example.com",
                "findings": {
                    "vulnerabilities": [
                        {
                            "id": "CVE-2021-44228",
                            "title": "Log4Shell",
                            "severity": "critical",
                            "host": "example.com",
                        }
                    ]
                },
            }
        })
        agg_data = json.loads(agg)
        assert agg_data["status"] == "ok", agg_data
        session_file = agg_data["session_file"]
        assert Path(session_file).exists()

        rep = await _do_generate_report({"session_id": session_file, "format": "md"})
        rep_data = json.loads(rep)
        assert "report_path" in rep_data, rep_data
        assert rep_data["format"] == "md"
        assert Path(rep_data["report_path"]).exists()
        assert "Log4Shell" in Path(rep_data["report_path"]).read_text()
