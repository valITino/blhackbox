"""Tests for the core runner."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import respx

from blhackbox.clients.hexstrike_client import HexStrikeClient
from blhackbox.config import Settings
from blhackbox.core.runner import ReconRunner, save_session
from blhackbox.models.base import ScanSession, Target


@pytest.fixture
def mock_settings() -> Settings:
    return Settings(hexstrike_url="http://testhost:8888")


@pytest.mark.asyncio
class TestReconRunner:
    async def test_run_recon(self, mock_settings: Settings) -> None:
        with respx.mock:
            respx.post("http://testhost:8888/api/intelligence/analyze-target").respond(
                200,
                json={
                    "success": True,
                    "results": {"target_info": "test data"},
                    "recommendations": ["run nmap"],
                    "risk_score": 3.5,
                },
            )

            async with HexStrikeClient(settings=mock_settings) as client:
                runner = ReconRunner(client)
                session = await runner.run_recon("example.com")

            assert session.status == "completed"
            assert len(session.findings) >= 1
            assert "intelligence/analyze-target" in session.tools_executed

    async def test_run_single_tool(self, mock_settings: Settings) -> None:
        with respx.mock:
            respx.post("http://testhost:8888/api/tools/network/nmap").respond(
                200,
                json={
                    "success": True,
                    "output": {"ports": [80]},
                    "raw_output": "80/tcp open http",
                },
            )

            async with HexStrikeClient(settings=mock_settings) as client:
                runner = ReconRunner(client)
                session = await runner.run_single_tool(
                    "network", "nmap", {"target": "example.com", "flags": ["-F"]}
                )

            assert session.status == "completed"
            assert "network/nmap" in session.tools_executed
            assert len(session.findings) == 1


class TestSaveSession:
    def test_save_session(self, sample_session: ScanSession, tmp_path: Path) -> None:
        path = save_session(sample_session, tmp_path)
        assert path.exists()
        assert path.suffix == ".json"

        data = json.loads(path.read_text())
        assert data["status"] == "completed"
        assert data["target"]["value"] == "example.com"
