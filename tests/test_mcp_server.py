"""Tests for the MCP server tool definitions and dispatch."""

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
        expected = {"recon", "run_tool", "query_graph", "get_findings",
                    "list_tools", "generate_report"}
        assert expected == names

    def test_recon_requires_target(self) -> None:
        recon = next(t for t in _TOOLS if t.name == "recon")
        assert "target" in recon.inputSchema["required"]

    def test_run_tool_requires_category_tool_params(self) -> None:
        rt = next(t for t in _TOOLS if t.name == "run_tool")
        assert set(rt.inputSchema["required"]) == {"category", "tool", "params"}


class TestMCPListTools:
    async def test_list_tools_returns_all(self) -> None:
        tools = await handle_list_tools()
        assert len(tools) == 6
        names = {t.name for t in tools}
        assert "recon" in names
        assert "run_tool" in names
