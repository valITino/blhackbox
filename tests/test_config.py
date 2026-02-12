"""Tests for configuration."""

from __future__ import annotations

from blhackbox.config import Settings


class TestSettings:
    def test_defaults(self) -> None:
        s = Settings()
        assert "hexstrike" in s.hexstrike_url or "localhost" in s.hexstrike_url
        assert s.hexstrike_timeout == 120
        assert s.hexstrike_max_retries == 3
        assert s.log_level == "INFO"

    def test_provider_priority(self) -> None:
        s = Settings(llm_provider_priority="anthropic,ollama")
        assert s.provider_priority_list == ["anthropic", "ollama"]

    def test_provider_priority_with_spaces(self) -> None:
        s = Settings(llm_provider_priority=" openai , anthropic ")
        assert s.provider_priority_list == ["openai", "anthropic"]
