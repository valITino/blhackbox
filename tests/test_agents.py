"""Tests for Ollama preprocessing agent classes (v2 architecture).

The v2 pipeline has three agents:
  1. IngestionAgent  — parse raw tool output into structured data
  2. ProcessingAgent — deduplicate, compress, annotate error_log
  3. SynthesisAgent  — merge into final AggregatedPayload
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from blhackbox.agents.base_agent import BaseAgent
from blhackbox.agents.ingestion_agent import IngestionAgent
from blhackbox.agents.processing_agent import ProcessingAgent
from blhackbox.agents.synthesis_agent import SynthesisAgent

# ---------------------------------------------------------------------------
# BaseAgent
# ---------------------------------------------------------------------------


class TestBaseAgent:
    def test_default_params(self) -> None:
        agent = BaseAgent()
        assert agent.ollama_url == "http://localhost:11434"
        assert agent.model == "llama3.3"

    def test_custom_params(self) -> None:
        agent = BaseAgent(ollama_url="http://custom:9999", model="mistral")
        assert agent.ollama_url == "http://custom:9999"
        assert agent.model == "mistral"

    def test_trailing_slash_stripped(self) -> None:
        agent = BaseAgent(ollama_url="http://localhost:11434/")
        assert agent.ollama_url == "http://localhost:11434"

    def test_load_prompt_fallback(self) -> None:
        """BaseAgent has no prompt file, so it should use the fallback prompt."""
        agent = BaseAgent()
        # Fallback prompt contains the class name and "JSON"
        assert "BaseAgent" in agent.system_prompt
        assert "JSON" in agent.system_prompt

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

    def test_parse_missing_message_key(self) -> None:
        agent = BaseAgent()
        result = agent._parse({})
        assert result == {}

    @pytest.mark.asyncio
    async def test_process_ollama_unreachable(self) -> None:
        """When Ollama is unreachable, process returns empty dict."""
        agent = BaseAgent(ollama_url="http://unreachable:99999")
        result = await agent.process("some raw data")
        assert result == {}

    @pytest.mark.asyncio
    async def test_process_with_mock(self) -> None:
        """Test process with a mocked Ollama response."""
        agent = IngestionAgent()
        mock_response = {
            "message": {
                "content": json.dumps({
                    "hosts": [{"ip": "10.0.0.1", "hostname": "", "ports": []}],
                    "subdomains": ["api.example.com"],
                    "services": [],
                    "vulnerabilities": [],
                    "endpoints": [],
                    "technologies": [],
                    "ports": [],
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

            result = await agent.process("nmap output:\n80/tcp open http")
            assert result["subdomains"] == ["api.example.com"]
            assert result["hosts"][0]["ip"] == "10.0.0.1"


# ---------------------------------------------------------------------------
# Agent names (used for prompt file loading)
# ---------------------------------------------------------------------------


class TestAgentNames:
    def test_ingestion_agent_name(self) -> None:
        agent = IngestionAgent()
        assert agent.__class__.__name__ == "IngestionAgent"

    def test_processing_agent_name(self) -> None:
        agent = ProcessingAgent()
        assert agent.__class__.__name__ == "ProcessingAgent"

    def test_synthesis_agent_name(self) -> None:
        agent = SynthesisAgent()
        assert agent.__class__.__name__ == "SynthesisAgent"

    def test_all_are_base_agent_subclasses(self) -> None:
        assert issubclass(IngestionAgent, BaseAgent)
        assert issubclass(ProcessingAgent, BaseAgent)
        assert issubclass(SynthesisAgent, BaseAgent)


# ---------------------------------------------------------------------------
# Prompt loading from .md files
# ---------------------------------------------------------------------------


class TestPromptLoading:
    def test_ingestion_prompt_loaded(self) -> None:
        agent = IngestionAgent()
        prompt_lower = agent.system_prompt.lower()
        assert "ingestion" in prompt_lower
        assert "json" in prompt_lower

    def test_processing_prompt_loaded(self) -> None:
        agent = ProcessingAgent()
        prompt_lower = agent.system_prompt.lower()
        assert "processing" in prompt_lower or "deduplic" in prompt_lower
        assert "json" in prompt_lower

    def test_synthesis_prompt_loaded(self) -> None:
        agent = SynthesisAgent()
        prompt_lower = agent.system_prompt.lower()
        assert "synthesis" in prompt_lower or "merge" in prompt_lower
        assert "json" in prompt_lower

    def test_all_prompts_are_md_files(self) -> None:
        prompts_dir = Path(__file__).resolve().parent.parent / "blhackbox" / "prompts" / "agents"
        expected = {
            "ingestionagent.md",
            "processingagent.md",
            "synthesisagent.md",
        }
        actual = {f.name for f in prompts_dir.glob("*.md")}
        assert expected.issubset(actual), f"Missing prompts: {expected - actual}"

    def test_prompt_file_name_matches_class_name(self) -> None:
        """Prompt file is <classname>.lower().md — verify the naming convention."""
        for cls in (IngestionAgent, ProcessingAgent, SynthesisAgent):
            cls()  # ensure instantiation works
            expected_file = cls.__name__.lower() + ".md"
            prompts_dir = Path(__file__).resolve().parent.parent / "blhackbox" / "prompts" / "agents"  # noqa: E501
            assert (prompts_dir / expected_file).exists(), (
                f"Expected prompt file {expected_file} for {cls.__name__}"
            )


# ---------------------------------------------------------------------------
# Agent instantiation with custom params
# ---------------------------------------------------------------------------


class TestAgentInstantiation:
    def test_ingestion_agent_custom_params(self) -> None:
        agent = IngestionAgent(ollama_url="http://custom:1234", model="codellama")
        assert agent.ollama_url == "http://custom:1234"
        assert agent.model == "codellama"

    def test_processing_agent_custom_params(self) -> None:
        agent = ProcessingAgent(ollama_url="http://custom:5678", model="phi3")
        assert agent.ollama_url == "http://custom:5678"
        assert agent.model == "phi3"

    def test_synthesis_agent_custom_params(self) -> None:
        agent = SynthesisAgent(ollama_url="http://custom:9012", model="gemma2")
        assert agent.ollama_url == "http://custom:9012"
        assert agent.model == "gemma2"

    def test_default_params_inherited(self) -> None:
        for cls in (IngestionAgent, ProcessingAgent, SynthesisAgent):
            agent = cls()
            assert agent.ollama_url == "http://localhost:11434"
            assert agent.model == "llama3.3"
