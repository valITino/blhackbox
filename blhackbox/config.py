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

    # --- Neo4j (optional — enabled with --profile neo4j) ---
    neo4j_uri: str = Field(default="bolt://neo4j:7687", description="Neo4j Bolt URI")
    neo4j_user: str = Field(default="neo4j", description="Neo4j username")
    neo4j_password: str = Field(
        default="", description="Neo4j password (set via NEO4J_PASSWORD env var)"
    )
    neo4j_database: str = Field(default="neo4j", description="Neo4j database name")

    # --- Ollama ---
    ollama_url: str = Field(default="http://ollama:11434", description="Ollama API URL")
    ollama_model: str = Field(default="llama3.3", description="Ollama model name")

    # --- MCP Gateway ---
    mcp_gateway_port: int = Field(default=8080, description="MCP Gateway port")

    # --- General ---
    max_iterations: int = Field(
        default=10, description="Maximum tool iterations per recon session"
    )
    log_level: str = Field(default="INFO", description="Logging level")
    results_dir: Path = Field(default=Path("./results"), description="Directory for scan results")
    wordlists_dir: Path = Field(default=Path("./wordlists"), description="Directory for wordlists")


# Singleton instance
settings = Settings()
