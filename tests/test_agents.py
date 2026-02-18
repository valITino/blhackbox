"""Tests for Ollama preprocessing agent classes."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from blhackbox.agents.base_agent import BaseAgent
from blhackbox.agents.error_log_agent import ErrorLogAgent
from blhackbox.agents.network_agent import NetworkAgent
from blhackbox.agents.recon_agent import ReconAgent
from blhackbox.agents.structure_agent import StructureAgent
from blhackbox.agents.vuln_agent import VulnAgent
from blhackbox.agents.web_agent import WebAgent


class TestBaseAgent:
    def test_agent_name(self) -> None:
        agent = BaseAgent(ollama_url="http://localhost:11434", model="llama3.3")
        assert agent.agent_name == "base"
        assert agent.model == "llama3.3"
        assert agent.ollama_url == "http://localhost:11434"

    def test_load_prompt_fallback(self) -> None:
        """If prompt file doesn't exist, returns a fallback prompt."""
        agent = BaseAgent()
        # base_agent.md doesn't exist, so it should use fallback
        assert "base" in agent.system_prompt or "JSON" in agent.system_prompt

    def test_parse_valid_json(self) -> None:
        agent = BaseAgent()
        result = agent._parse({
            "message": {"content": '{"key": "value"}'},
        })
        assert result == {"key": "value"}

    def test_parse_empty_response(self) -> None:
        agent = BaseAgent()
        result = agent._parse({"message": {"content": ""}})
        assert result == {}

    def test_parse_invalid_json(self) -> None:
        agent = BaseAgent()
        result = agent._parse({"message": {"content": "not json at all"}})
        assert result == {}

    def test_parse_json_with_preamble(self) -> None:
        agent = BaseAgent()
        result = agent._parse({
            "message": {"content": 'Here is the result: {"key": "value"} done'},
        })
        assert result == {"key": "value"}

    @pytest.mark.asyncio
    async def test_process_ollama_unreachable(self) -> None:
        """When Ollama is unreachable, process returns empty dict."""
        agent = BaseAgent(ollama_url="http://unreachable:99999")
        result = await agent.process("some raw data")
        assert result == {}

    @pytest.mark.asyncio
    async def test_process_with_mock(self) -> None:
        """Test process with a mocked Ollama response."""
        agent = ReconAgent()
        mock_response = {
            "message": {
                "content": json.dumps({
                    "subdomains": ["api.example.com"],
                    "ips": ["10.0.0.1"],
                    "technologies": [],
                    "asn": {},
                    "certificates": [],
                })
            }
        }

        with patch("blhackbox.agents.base_agent.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=None)

            # httpx Response.json() is synchronous, so use MagicMock
            mock_resp = MagicMock()
            mock_resp.json.return_value = mock_response
            mock_resp.raise_for_status = MagicMock()
            mock_client.post.return_value = mock_resp

            result = await agent.process("subfinder output:\napi.example.com")
            assert result["subdomains"] == ["api.example.com"]


class TestAgentNames:
    def test_recon_agent_name(self) -> None:
        assert ReconAgent().agent_name == "recon_agent"

    def test_network_agent_name(self) -> None:
        assert NetworkAgent().agent_name == "network_agent"

    def test_vuln_agent_name(self) -> None:
        assert VulnAgent().agent_name == "vuln_agent"

    def test_web_agent_name(self) -> None:
        assert WebAgent().agent_name == "web_agent"

    def test_error_log_agent_name(self) -> None:
        assert ErrorLogAgent().agent_name == "error_log_agent"

    def test_structure_agent_name(self) -> None:
        assert StructureAgent().agent_name == "structure_agent"


class TestPromptLoading:
    def test_recon_prompt_loaded(self) -> None:
        agent = ReconAgent()
        prompt_lower = agent.system_prompt.lower()
        assert "reconnaissance" in prompt_lower or "recon" in prompt_lower
        assert "JSON" in agent.system_prompt

    def test_network_prompt_loaded(self) -> None:
        agent = NetworkAgent()
        assert "network" in agent.system_prompt.lower()
        assert "JSON" in agent.system_prompt

    def test_vuln_prompt_loaded(self) -> None:
        agent = VulnAgent()
        assert "vuln" in agent.system_prompt.lower()
        assert "JSON" in agent.system_prompt

    def test_web_prompt_loaded(self) -> None:
        agent = WebAgent()
        assert "web" in agent.system_prompt.lower()
        assert "JSON" in agent.system_prompt

    def test_error_log_prompt_loaded(self) -> None:
        agent = ErrorLogAgent()
        assert "error" in agent.system_prompt.lower() or "noise" in agent.system_prompt.lower()
        assert "security_relevance" in agent.system_prompt

    def test_structure_prompt_loaded(self) -> None:
        agent = StructureAgent()
        assert "merge" in agent.system_prompt.lower()
        assert "JSON" in agent.system_prompt

    def test_all_prompts_are_md_files(self) -> None:
        prompts_dir = Path(__file__).resolve().parent.parent / "blhackbox" / "prompts" / "agents"
        expected = {
            "recon_agent.md",
            "network_agent.md",
            "vuln_agent.md",
            "web_agent.md",
            "error_log_agent.md",
            "structure_agent.md",
        }
        actual = {f.name for f in prompts_dir.glob("*.md")}
        assert expected.issubset(actual), f"Missing prompts: {expected - actual}"
