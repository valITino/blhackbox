"""Centralized configuration via pydantic-settings."""

from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Repo root: blhackbox/config.py -> parent -> parent = repo root
_REPO_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """Application-wide settings, loaded from environment / .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Neo4j (optional — enabled with --profile neo4j) ---
    neo4j_uri: str = Field(default="bolt://neo4j:7687", description="Neo4j Bolt URI")
    neo4j_user: str = Field(default="neo4j", description="Neo4j username")
    neo4j_password: str = Field(
        default="", description="Neo4j password (set via NEO4J_PASSWORD env var)"
    )
    neo4j_database: str = Field(default="neo4j", description="Neo4j database name")

    # --- MCP Gateway ---
    mcp_gateway_port: int = Field(default=8080, description="MCP Gateway port")

    # --- Screenshot MCP ---
    screenshot_mcp_url: str = Field(
        default="http://screenshot-mcp:9004",
        description="Screenshot MCP server base URL",
    )

    # --- General ---
    max_iterations: int = Field(
        default=10, description="Maximum tool iterations per recon session"
    )
    log_level: str = Field(default="INFO", description="Logging level")
    results_dir: Path = Field(
        default=_REPO_ROOT / "results", description="Directory for scan results"
    )
    reports_dir: Path = Field(
        default=_REPO_ROOT / "reports", description="Directory for organized reports"
    )
    wordlists_dir: Path = Field(
        default=_REPO_ROOT / "wordlists", description="Directory for wordlists"
    )


# Singleton instance
settings = Settings()
