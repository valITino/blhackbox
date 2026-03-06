"""Tests for the Screenshot MCP server integration.

Validates that:
- Screenshot tools are correctly defined in the blhackbox MCP server
- Tool definitions have proper schemas and descriptions
- The screenshot MCP server module is importable and well-formed
"""

from __future__ import annotations

from blhackbox.mcp.server import _TOOLS, handle_list_tools


class TestScreenshotToolDefinitions:
    """Verify screenshot tools are registered in the blhackbox MCP server."""

    def test_take_screenshot_present(self) -> None:
        names = {t.name for t in _TOOLS}
        assert "take_screenshot" in names

    def test_take_element_screenshot_present(self) -> None:
        names = {t.name for t in _TOOLS}
        assert "take_element_screenshot" in names

    def test_list_screenshots_present(self) -> None:
        names = {t.name for t in _TOOLS}
        assert "list_screenshots" in names

    def test_annotate_screenshot_present(self) -> None:
        names = {t.name for t in _TOOLS}
        assert "annotate_screenshot" in names

    def test_take_screenshot_requires_url(self) -> None:
        tool = next(t for t in _TOOLS if t.name == "take_screenshot")
        assert "url" in tool.inputSchema["required"]

    def test_take_element_screenshot_requires_url_and_selector(self) -> None:
        tool = next(t for t in _TOOLS if t.name == "take_element_screenshot")
        required = set(tool.inputSchema["required"])
        assert required == {"url", "selector"}

    def test_annotate_screenshot_requires_path_and_annotations(self) -> None:
        tool = next(t for t in _TOOLS if t.name == "annotate_screenshot")
        required = set(tool.inputSchema["required"])
        assert required == {"screenshot_path", "annotations"}

    def test_list_screenshots_has_limit_param(self) -> None:
        tool = next(t for t in _TOOLS if t.name == "list_screenshots")
        assert "limit" in tool.inputSchema["properties"]

    def test_all_screenshot_tools_have_descriptions(self) -> None:
        screenshot_names = {
            "take_screenshot",
            "take_element_screenshot",
            "list_screenshots",
            "annotate_screenshot",
        }
        for tool in _TOOLS:
            if tool.name in screenshot_names:
                assert tool.description, f"Screenshot tool {tool.name} missing description"
                assert len(tool.description) > 20, (
                    f"Screenshot tool {tool.name} description too short"
                )


class TestScreenshotToolCount:
    """Verify the total tool count is updated correctly."""

    async def test_list_tools_includes_screenshot_tools(self) -> None:
        tools = await handle_list_tools()
        # 7 core tools + 4 screenshot tools = 11
        assert len(tools) == 11

    async def test_list_tools_has_all_expected_names(self) -> None:
        tools = await handle_list_tools()
        names = {t.name for t in tools}
        expected = {
            "run_tool",
            "query_graph",
            "get_findings",
            "list_tools",
            "generate_report",
            "list_templates",
            "get_template",
            "take_screenshot",
            "take_element_screenshot",
            "list_screenshots",
            "annotate_screenshot",
        }
        assert expected == names


class TestScreenshotMCPServerModule:
    """Verify the screenshot-mcp server module is well-formed."""

    def test_server_module_importable(self) -> None:
        """The screenshot-mcp server.py can be parsed as valid Python."""
        from pathlib import Path

        server_path = Path(__file__).parent.parent / "screenshot-mcp" / "server.py"
        assert server_path.exists(), f"screenshot-mcp/server.py not found at {server_path}"

        source = server_path.read_text()
        # Should compile without SyntaxError
        compile(source, str(server_path), "exec")

    def test_requirements_file_exists(self) -> None:
        from pathlib import Path

        req_path = Path(__file__).parent.parent / "screenshot-mcp" / "requirements.txt"
        assert req_path.exists()
        content = req_path.read_text()
        assert "playwright" in content
        assert "mcp" in content
        assert "Pillow" in content

    def test_dockerfile_exists(self) -> None:
        from pathlib import Path

        dockerfile = Path(__file__).parent.parent / "docker" / "screenshot-mcp.Dockerfile"
        assert dockerfile.exists()
        content = dockerfile.read_text()
        assert "playwright" in content.lower()
        assert "9004" in content
