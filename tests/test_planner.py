"""Tests for the planner's response parsing and LLM client helpers."""

from __future__ import annotations

from blhackbox.core.planner import _parse_llm_response
from blhackbox.llm.client import _is_openai_reasoning_model


class TestIsOpenAIReasoningModel:
    def test_o3_is_reasoning(self) -> None:
        assert _is_openai_reasoning_model("o3") is True

    def test_o1_is_reasoning(self) -> None:
        assert _is_openai_reasoning_model("o1") is True

    def test_o3_mini_is_reasoning(self) -> None:
        assert _is_openai_reasoning_model("o3-mini") is True

    def test_o1_preview_is_reasoning(self) -> None:
        assert _is_openai_reasoning_model("o1-preview") is True

    def test_gpt4o_is_not_reasoning(self) -> None:
        assert _is_openai_reasoning_model("gpt-4o") is False

    def test_gpt4_is_not_reasoning(self) -> None:
        assert _is_openai_reasoning_model("gpt-4") is False

    def test_ollama_model_not_reasoning(self) -> None:
        assert _is_openai_reasoning_model("llama3.3") is False

    def test_empty_string(self) -> None:
        assert _is_openai_reasoning_model("") is False

    def test_single_char_o(self) -> None:
        assert _is_openai_reasoning_model("o") is False


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
        raw = (
            '```json\n{"action": "run_tool", "category": "dns",'
            ' "tool": "subfinder", "reasoning": "test"}\n```'
        )
        result = _parse_llm_response(raw)
        assert result["action"] == "run_tool"
        assert result["tool"] == "subfinder"

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
