"""Tests for configuration (v2 architecture).

The v2 Settings has Neo4j, MCP Gateway, Screenshot MCP,
and general settings.
"""

from __future__ import annotations

from pathlib import Path

from blhackbox.config import Settings


class TestSettings:
    def test_defaults(self) -> None:
        s = Settings()
        assert s.log_level == "INFO"

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

    def test_neo4j_defaults(self) -> None:
        # Use explicit empty password to test the field exists and accepts it,
        # since .env may set NEO4J_PASSWORD which would override the default.
        s = Settings(neo4j_password="")
        assert "bolt://" in s.neo4j_uri
        assert s.neo4j_user == "neo4j"
        assert s.neo4j_password == ""

    def test_mcp_gateway_port_default(self) -> None:
        s = Settings()
        assert s.mcp_gateway_port == 8080

    def test_mcp_gateway_port_override(self) -> None:
        s = Settings(mcp_gateway_port=9090)
        assert s.mcp_gateway_port == 9090

    def test_results_dir_default(self) -> None:
        s = Settings()
        assert isinstance(s.results_dir, Path)

    def test_results_dir_override(self) -> None:
        s = Settings(results_dir="/tmp/custom_results")
        assert s.results_dir == Path("/tmp/custom_results")

    def test_wordlists_dir_default(self) -> None:
        s = Settings()
        assert isinstance(s.wordlists_dir, Path)

    def test_no_llm_provider_settings(self) -> None:
        """v2 Settings should not have LLM provider fields."""
        s = Settings()
        assert not hasattr(s, "openai_api_key")
        assert not hasattr(s, "openai_model")
        assert not hasattr(s, "anthropic_api_key")
        assert not hasattr(s, "anthropic_model")
        assert not hasattr(s, "llm_provider_priority")
        assert not hasattr(s, "provider_priority_list")

    def test_no_aura_fields(self) -> None:
        """v2 Settings should not have Aura fields."""
        s = Settings()
        assert not hasattr(s, "aura_instanceid")
        assert not hasattr(s, "aura_instancename")

    def test_no_hexstrike_fields(self) -> None:
        """v2 Settings should not have HexStrike fields (removed)."""
        s = Settings()
        assert not hasattr(s, "hexstrike_url")
        assert not hasattr(s, "hexstrike_timeout")
        assert not hasattr(s, "hexstrike_max_retries")
