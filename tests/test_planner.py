"""Tests for the planner's response parsing."""

from __future__ import annotations

from blhackbox.core.planner import _parse_llm_response


class TestParseLLMResponse:
    def test_valid_json(self) -> None:
        raw = '{"action": "run_tool", "category": "network", "tool": "nmap", "reasoning": "start"}'
        result = _parse_llm_response(raw)
        assert result["action"] == "run_tool"
        assert result["tool"] == "nmap"

    def test_stop_action(self) -> None:
        raw = '{"action": "stop", "reasoning": "done"}'
        result = _parse_llm_response(raw)
        assert result["action"] == "stop"

    def test_markdown_fenced_json(self) -> None:
        raw = '```json\n{"action": "run_agent", "agent": "recon", "reasoning": "test"}\n```'
        result = _parse_llm_response(raw)
        assert result["action"] == "run_agent"
        assert result["agent"] == "recon"

    def test_json_with_surrounding_text(self) -> None:
        raw = 'Based on analysis: {"action": "stop", "reasoning": "complete"} is my answer.'
        result = _parse_llm_response(raw)
        assert result["action"] == "stop"

    def test_invalid_json_returns_stop(self) -> None:
        raw = "I think we should run nmap next"
        result = _parse_llm_response(raw)
        assert result["action"] == "stop"

    def test_unknown_action_returns_stop(self) -> None:
        raw = '{"action": "exploit", "tool": "bad"}'
        result = _parse_llm_response(raw)
        assert result["action"] == "stop"
