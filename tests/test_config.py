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

    def test_max_iterations_default(self) -> None:
        s = Settings()
        assert s.max_iterations == 10

    def test_max_iterations_override(self) -> None:
        s = Settings(max_iterations=20)
        assert s.max_iterations == 20

    def test_neo4j_database_default(self) -> None:
        s = Settings()
        assert s.neo4j_database == "neo4j"

    def test_neo4j_database_override(self) -> None:
        s = Settings(neo4j_database="custom_db")
        assert s.neo4j_database == "custom_db"

    def test_aura_fields_default_empty(self) -> None:
        s = Settings()
        assert s.aura_instanceid == ""
        assert s.aura_instancename == ""

    def test_aura_fields_override(self) -> None:
        s = Settings(aura_instanceid="abc123", aura_instancename="Blhackbox")
        assert s.aura_instanceid == "abc123"
        assert s.aura_instancename == "Blhackbox"

    def test_default_model_names(self) -> None:
        s = Settings()
        assert s.openai_model == "o3"
        assert s.anthropic_model == "claude-opus-4-20250514"
        assert s.ollama_model == "llama3.3"
