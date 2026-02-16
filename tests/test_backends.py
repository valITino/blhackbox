"""Tests for the tool execution backends."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from blhackbox.backends.base import ToolBackend, ToolResult
from blhackbox.backends.local import LocalBackend, _httpx_args, _nmap_args


class TestToolResult:
    def test_defaults(self) -> None:
        r = ToolResult()
        assert r.success is True
        assert r.has_errors is False

    def test_has_errors_on_failure(self) -> None:
        r = ToolResult(success=False)
        assert r.has_errors is True

    def test_has_errors_with_error_list(self) -> None:
        r = ToolResult(errors=["something went wrong"])
        assert r.has_errors is True


class TestNmapArgs:
    def test_default_scan(self) -> None:
        args = _nmap_args({"target": "example.com"})
        assert "-sV" in args
        assert "-sC" in args
        assert "example.com" in args

    def test_custom_scan_type(self) -> None:
        args = _nmap_args({"target": "10.0.0.1", "scan_type": "sS"})
        assert "-sS" in args
        assert "10.0.0.1" in args

    def test_custom_ports(self) -> None:
        args = _nmap_args({"target": "10.0.0.1", "ports": "80,443"})
        assert "-p" in args
        assert "80,443" in args


class TestHttpxArgs:
    def test_basic_args(self) -> None:
        args = _httpx_args({"target": "example.com"})
        assert "-u" in args
        assert "example.com" in args
        assert "-silent" in args


class TestLocalBackend:
    @pytest.fixture
    def backend(self) -> LocalBackend:
        return LocalBackend()

    async def test_connect_close(self, backend: LocalBackend) -> None:
        await backend.connect()
        await backend.close()

    async def test_unsupported_tool(self, backend: LocalBackend) -> None:
        result = await backend.run_tool("misc", "nonexistent_tool_xyz", {})
        assert result.success is False
        assert "not supported" in result.errors[0]

    async def test_list_tools(self, backend: LocalBackend) -> None:
        tools = await backend.list_tools()
        assert isinstance(tools, list)

    async def test_context_manager(self) -> None:
        async with LocalBackend() as backend:
            assert isinstance(backend, ToolBackend)

    @patch("shutil.which", return_value=None)
    async def test_tool_not_on_path(self, mock_which: AsyncMock) -> None:
        backend = LocalBackend()
        result = await backend.run_tool("network", "nmap", {"target": "127.0.0.1"})
        assert result.success is False
        assert "not found on PATH" in result.errors[0]


class TestHexStrikeBackend:
    async def test_import(self) -> None:
        from blhackbox.backends.hexstrike import HexStrikeBackend

        b = HexStrikeBackend()
        assert b.name == "hexstrike"
