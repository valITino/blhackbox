"""Centralized configuration via pydantic-settings."""

from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application-wide settings, loaded from environment / .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- HexStrike ---
    hexstrike_url: str = Field(
        default="http://hexstrike:8888", description="HexStrike API base URL"
    )
    hexstrike_timeout: int = Field(default=120, description="HTTP timeout in seconds")
    hexstrike_max_retries: int = Field(default=3, description="Max retries for failed requests")

    # --- Neo4j ---
    neo4j_uri: str = Field(default="bolt://neo4j:7687", description="Neo4j Bolt URI")
    neo4j_user: str = Field(default="neo4j", description="Neo4j username")
    neo4j_password: str = Field(default="", description="Neo4j password (must be set via NEO4J_PASSWORD env var)")

    # --- LLM ---
    openai_api_key: str = Field(default="", description="OpenAI API key")
    openai_model: str = Field(default="gpt-4o", description="OpenAI model name")
    anthropic_api_key: str = Field(default="", description="Anthropic API key")
    anthropic_model: str = Field(
        default="claude-sonnet-4-20250514", description="Anthropic model name"
    )
    ollama_url: str = Field(default="http://ollama:11434", description="Ollama API URL")
    ollama_model: str = Field(default="llama3", description="Ollama model name")
    llm_provider_priority: str = Field(
        default="openai,anthropic,ollama",
        description="Comma-separated LLM fallback order",
    )

    # --- General ---
    log_level: str = Field(default="INFO", description="Logging level")
    results_dir: Path = Field(default=Path("./results"), description="Directory for scan results")
    wordlists_dir: Path = Field(default=Path("./wordlists"), description="Directory for wordlists")

    @property
    def provider_priority_list(self) -> list[str]:
        return [p.strip() for p in self.llm_provider_priority.split(",") if p.strip()]


# Singleton instance
settings = Settings()
