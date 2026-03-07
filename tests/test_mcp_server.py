"""Tests for the MCP server tool definitions and dispatch (v2 architecture).

The blhackbox MCP server exposes orchestrated workflows (run_tool,
query_graph, get_findings, list_tools, generate_report, list_templates,
get_template) plus screenshot tools (take_screenshot, take_element_screenshot,
list_screenshots, annotate_screenshot).
"""

from __future__ import annotations

from blhackbox.mcp.server import _TOOLS, handle_list_tools


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
            "list_tools", "generate_report", "list_templates",
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
        assert len(tools) == 13
        names = {t.name for t in tools}
        assert "run_tool" in names
        assert "list_templates" in names
        assert "get_template" in names
        assert "take_screenshot" in names
        assert "annotate_screenshot" in names
