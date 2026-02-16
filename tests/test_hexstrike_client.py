"""Tests for the HexStrike API client using respx mocks."""

from __future__ import annotations

import pytest
import respx

from blhackbox.clients.hexstrike_client import HexStrikeClient
from blhackbox.config import Settings
from blhackbox.exceptions import HexStrikeAPIError, HexStrikeConnectionError


@pytest.fixture
def mock_settings() -> Settings:
    return Settings(hexstrike_url="http://testhost:8888")


@pytest.mark.asyncio
class TestHexStrikeClient:
    async def test_health_check_success(self, mock_settings: Settings) -> None:
        with respx.mock:
            respx.get("http://testhost:8888/health").respond(200, json={"status": "ok"})

            async with HexStrikeClient(settings=mock_settings) as client:
                assert await client.health_check() is True

    async def test_health_check_failure(self, mock_settings: Settings) -> None:
        with respx.mock:
            respx.get("http://testhost:8888/health").respond(500)

            async with HexStrikeClient(settings=mock_settings) as client:
                assert await client.health_check() is False

    async def test_run_tool(self, mock_settings: Settings) -> None:
        with respx.mock:
            respx.post("http://testhost:8888/api/tools/nmap").respond(
                200,
                json={
                    "success": True,
                    "output": {"ports": [22, 80, 443]},
                    "raw_output": "22/tcp open ssh\n80/tcp open http",
                    "execution_time": 5.2,
                },
            )

            async with HexStrikeClient(settings=mock_settings) as client:
                result = await client.run_tool(
                    "network", "nmap", {"target": "example.com", "flags": ["-F"]}
                )

            assert result.success is True
            assert result.tool == "nmap"
            assert result.category == "network"
            assert result.output == {"ports": [22, 80, 443]}
            assert not result.has_errors

    async def test_run_tool_api_error(self, mock_settings: Settings) -> None:
        with respx.mock:
            respx.post("http://testhost:8888/api/tools/nmap").respond(
                400, text="Bad request"
            )

            async with HexStrikeClient(settings=mock_settings) as client:
                with pytest.raises(HexStrikeAPIError) as exc_info:
                    await client.run_tool("network", "nmap", {"target": "x"})
                assert exc_info.value.status_code == 400

    async def test_analyze_target(self, mock_settings: Settings) -> None:
        with respx.mock:
            respx.post("http://testhost:8888/api/intelligence/analyze-target").respond(
                200,
                json={
                    "success": True,
                    "results": {"summary": "test"},
                    "recommendations": ["check port 80"],
                    "risk_score": 4.5,
                },
            )

            async with HexStrikeClient(settings=mock_settings) as client:
                result = await client.analyze_target("example.com")

            assert result.target == "example.com"
            assert result.risk_score == 4.5
            assert len(result.recommendations) == 1

    async def test_list_agents(self, mock_settings: Settings) -> None:
        with respx.mock:
            respx.get("http://testhost:8888/api/agents/list").respond(
                200,
                json={
                    "agents": [
                        {"name": "bug_bounty", "description": "Bug bounty agent"},
                        {"name": "recon", "description": "Recon agent"},
                    ]
                },
            )

            async with HexStrikeClient(settings=mock_settings) as client:
                agents = await client.list_agents()

            assert len(agents) == 2
            assert agents[0].name == "bug_bounty"

    async def test_run_agent(self, mock_settings: Settings) -> None:
        with respx.mock:
            respx.post("http://testhost:8888/api/agents/recon/run").respond(
                200,
                json={
                    "success": True,
                    "results": {"domains": ["sub.example.com"]},
                    "findings": [{"title": "subdomain found"}],
                },
            )

            async with HexStrikeClient(settings=mock_settings) as client:
                result = await client.run_agent("recon", "example.com")

            assert result.success is True
            assert result.agent == "recon"
            assert len(result.findings) == 1

    async def test_client_not_initialized(self, mock_settings: Settings) -> None:
        client = HexStrikeClient(settings=mock_settings)
        with pytest.raises(HexStrikeConnectionError):
            _ = client.client
