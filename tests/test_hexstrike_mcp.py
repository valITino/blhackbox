"""Tests for the HexStrike MCP server.

Validates that:
- The hexstrike_mcp module is importable and well-formed
- MCP tools are correctly defined with proper signatures
- HTTP proxy logic correctly maps tool calls to HexStrike API requests
- Error handling and input validation work correctly
- Infrastructure files (requirements.txt, Dockerfile, catalog, compose) exist
"""

from __future__ import annotations

import importlib.util
import json
import re
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

import httpx
import pytest

# ---------------------------------------------------------------------------
# Load the hexstrike-mcp server module via importlib (hyphen in dir name)
# ---------------------------------------------------------------------------

_SERVER_PATH = Path(__file__).parent.parent / "hexstrike-mcp" / "server.py"


def _load_hexstrike_mcp():
    """Import hexstrike-mcp/server.py as a module named 'hexstrike_mcp'."""
    if "hexstrike_mcp" in sys.modules:
        return sys.modules["hexstrike_mcp"]
    spec = importlib.util.spec_from_file_location("hexstrike_mcp", _SERVER_PATH)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules["hexstrike_mcp"] = mod
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------------------
# Module-level tests (no imports from hexstrike_mcp to avoid FastMCP startup)
# ---------------------------------------------------------------------------


class TestHexStrikeMCPModuleStructure:
    """Verify the hexstrike-mcp module files are well-formed."""

    def test_server_module_compiles(self) -> None:
        """hexstrike-mcp/server.py can be parsed as valid Python."""
        assert _SERVER_PATH.exists(), f"hexstrike-mcp/server.py not found at {_SERVER_PATH}"
        source = _SERVER_PATH.read_text()
        compile(source, str(_SERVER_PATH), "exec")

    def test_requirements_file_exists(self) -> None:
        req_path = Path(__file__).parent.parent / "hexstrike-mcp" / "requirements.txt"
        assert req_path.exists()
        content = req_path.read_text()
        assert "mcp" in content
        assert "httpx" in content

    def test_dockerfile_exists(self) -> None:
        dockerfile = Path(__file__).parent.parent / "docker" / "hexstrike-mcp.Dockerfile"
        assert dockerfile.exists()
        content = dockerfile.read_text()
        assert "9005" in content
        assert "server.py" in content
        assert "requirements.txt" in content

    def test_catalog_includes_hexstrike_mcp(self) -> None:
        catalog = Path(__file__).parent.parent / "blhackbox-mcp-catalog.yaml"
        assert catalog.exists()
        content = catalog.read_text()
        assert "hexstrike-mcp" in content
        assert "9005" in content

    def test_mcp_json_includes_hexstrike(self) -> None:
        mcp_json = Path(__file__).parent.parent / "blhackbox-mcp.json"
        assert mcp_json.exists()
        data = json.loads(mcp_json.read_text())
        assert "hexstrike" in data["mcpServers"]
        hs = data["mcpServers"]["hexstrike"]
        assert hs["args"] == ["hexstrike-mcp/server.py"]

    def test_docker_compose_includes_hexstrike_mcp(self) -> None:
        compose = Path(__file__).parent.parent / "docker-compose.yml"
        assert compose.exists()
        content = compose.read_text()
        assert "hexstrike-mcp:" in content
        assert "blhackbox-hexstrike-mcp" in content
        assert "hexstrike-mcp.Dockerfile" in content


# ---------------------------------------------------------------------------
# Path segment validation tests
# ---------------------------------------------------------------------------


class TestPathSegmentValidation:
    """Verify input validation prevents SSRF and path traversal."""

    _SAFE_PATH_SEGMENT = re.compile(r"^[a-zA-Z0-9_\-]+$")

    def _validate(self, value: str, context: str = "test") -> str:
        if not self._SAFE_PATH_SEGMENT.match(value):
            raise ValueError(f"Invalid characters in {context}: {value!r}")
        return value

    def test_valid_tool_names(self) -> None:
        for name in ["nmap", "httpx", "nuclei", "nmap-advanced", "enum4linux-ng"]:
            assert self._validate(name) == name

    def test_rejects_path_traversal(self) -> None:
        with pytest.raises(ValueError):
            self._validate("../etc/passwd")

    def test_rejects_url_characters(self) -> None:
        with pytest.raises(ValueError):
            self._validate("nmap?target=evil")

    def test_rejects_slashes(self) -> None:
        with pytest.raises(ValueError):
            self._validate("tools/nmap")

    def test_rejects_spaces(self) -> None:
        with pytest.raises(ValueError):
            self._validate("nmap ; rm -rf /")

    def test_rejects_empty(self) -> None:
        with pytest.raises(ValueError):
            self._validate("")


# ---------------------------------------------------------------------------
# HTTP proxy logic tests (using mocked httpx)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestHexStrikeMCPHTTPProxy:
    """Test the HTTP proxy functions that map MCP calls to HexStrike API."""

    @pytest.fixture(autouse=True)
    def _setup(self):
        """Reset the global HTTP client between tests."""
        mod = _load_hexstrike_mcp()
        self.mod = mod
        mod._http_client = None

    async def test_api_get_success(self) -> None:
        mock_response = httpx.Response(
            200,
            json={"status": "ok", "version": "6.0.0"},
            request=httpx.Request("GET", "http://test:8888/health"),
        )
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.is_closed = False

        self.mod._http_client = mock_client
        result = await self.mod._api_get("/health")
        assert result["status"] == "ok"
        mock_client.get.assert_called_once_with("/health")

    async def test_api_get_timeout(self) -> None:
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get = AsyncMock(side_effect=httpx.TimeoutException("timeout"))
        mock_client.is_closed = False

        self.mod._http_client = mock_client
        result = await self.mod._api_get("/health")
        assert "error" in result
        assert "Timeout" in result["error"]

    async def test_api_get_connection_error(self) -> None:
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get = AsyncMock(
            side_effect=httpx.ConnectError("Connection refused")
        )
        mock_client.is_closed = False

        self.mod._http_client = mock_client
        result = await self.mod._api_get("/health")
        assert "error" in result
        assert "Connection error" in result["error"]

    async def test_api_post_success(self) -> None:
        mock_response = httpx.Response(
            200,
            json={"success": True, "stdout": "22/tcp open ssh"},
            request=httpx.Request("POST", "http://test:8888/api/tools/nmap"),
        )
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.is_closed = False

        self.mod._http_client = mock_client
        result = await self.mod._api_post("/api/tools/nmap", {"target": "example.com"})
        assert result["success"] is True
        mock_client.post.assert_called_once_with(
            "/api/tools/nmap", json={"target": "example.com"}
        )

    async def test_api_post_http_error(self) -> None:
        mock_response = httpx.Response(
            400,
            text="Bad request",
            request=httpx.Request("POST", "http://test:8888/api/tools/nmap"),
        )
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.post = AsyncMock(
            side_effect=httpx.HTTPStatusError(
                "Bad request", request=mock_response.request, response=mock_response
            )
        )
        mock_client.is_closed = False

        self.mod._http_client = mock_client
        result = await self.mod._api_post("/api/tools/nmap", {"target": "x"})
        assert "error" in result
        assert "400" in result["error"]


# ---------------------------------------------------------------------------
# MCP tool function tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestHexStrikeMCPTools:
    """Test the MCP tool functions themselves."""

    @pytest.fixture(autouse=True)
    def _setup(self):
        mod = _load_hexstrike_mcp()
        self.mod = mod
        mod._http_client = None

    async def test_health_check_tool(self) -> None:
        with patch.object(self.mod, "_api_get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = {
                "status": "ok",
                "version": "6.0.0",
                "total_tools_available": 5,
            }
            result = json.loads(await self.mod.health_check())
            assert result["status"] == "ok"
            mock_get.assert_called_once_with("/health")

    async def test_list_tools_tool(self) -> None:
        with patch.object(self.mod, "_api_get", new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = [
                {
                    "total_tools": 127,
                    "available_tools": 5,
                    "categories": {"web_security": {"available": 1, "total": 19}},
                    "tools": {"httpx": "available"},
                },
                {"error": "not found"},  # /api/tools endpoint doesn't exist
            ]
            result = json.loads(await self.mod.list_tools())
            assert result["total_tools"] == 127
            assert result["available_tools"] == 5

    async def test_run_tool_success(self) -> None:
        with patch.object(self.mod, "_api_post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = {
                "success": True,
                "stdout": "22/tcp open ssh\n80/tcp open http",
                "execution_time": 5.2,
            }
            result = json.loads(
                await self.mod.run_tool("nmap", "example.com", '{"scan_type": "-sV"}')
            )
            assert result["success"] is True
            assert result["tool"] == "nmap"
            assert result["target"] == "example.com"
            mock_post.assert_called_once_with(
                "/api/tools/nmap",
                {"target": "example.com", "scan_type": "-sV"},
            )

    async def test_run_tool_invalid_options_json(self) -> None:
        result = json.loads(
            await self.mod.run_tool("nmap", "example.com", "not-json")
        )
        assert "error" in result

    async def test_run_tool_invalid_name(self) -> None:
        with pytest.raises(ValueError, match="Invalid characters"):
            await self.mod.run_tool("../etc/passwd", "example.com")

    async def test_run_tool_with_error_response(self) -> None:
        with patch.object(self.mod, "_api_post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = {
                "error": "Tool nmap not available",
            }
            result = json.loads(
                await self.mod.run_tool("nmap", "example.com")
            )
            assert result["success"] is False
            assert "Tool nmap not available" in result["errors"]

    async def test_list_agents_tool(self) -> None:
        with patch.object(self.mod, "_api_get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = {
                "agents": [
                    {"name": "bug_bounty", "description": "Bug bounty agent"},
                    {"name": "recon", "description": "Recon agent"},
                ]
            }
            result = json.loads(await self.mod.list_agents())
            assert len(result["agents"]) == 2
            mock_get.assert_called_once_with("/api/agents/list")

    async def test_run_agent_success(self) -> None:
        with patch.object(self.mod, "_api_post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = {
                "success": True,
                "results": {"domains": ["sub.example.com"]},
                "findings": [{"title": "subdomain found"}],
                "execution_time": 30.5,
            }
            result = json.loads(
                await self.mod.run_agent("recon", "example.com")
            )
            assert result["success"] is True
            assert result["agent"] == "recon"
            assert len(result["findings"]) == 1

    async def test_run_agent_invalid_name(self) -> None:
        with pytest.raises(ValueError, match="Invalid characters"):
            await self.mod.run_agent("bad/agent", "example.com")

    async def test_analyze_target_success(self) -> None:
        with patch.object(self.mod, "_api_post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = {
                "success": True,
                "target_profile": {"os": "Linux", "services": ["http", "ssh"]},
                "risk_score": 4.5,
                "recommendations": ["Update SSH", "Enable TLS"],
            }
            result = json.loads(
                await self.mod.analyze_target("example.com", "comprehensive")
            )
            assert result["success"] is True
            assert result["risk_score"] == 4.5
            assert len(result["recommendations"]) == 2
            mock_post.assert_called_once_with(
                "/api/intelligence/analyze-target",
                {"target": "example.com", "analysis_type": "comprehensive"},
            )

    async def test_analyze_target_quick(self) -> None:
        with patch.object(self.mod, "_api_post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = {
                "success": True,
                "results": {"summary": "quick scan done"},
            }
            result = json.loads(
                await self.mod.analyze_target("10.0.0.1", "quick")
            )
            assert result["analysis_type"] == "quick"
