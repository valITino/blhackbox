"""Static checks for default MCP integration container wiring."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).parent.parent
COMPOSE = ROOT / "docker-compose.yml"
CATALOG = ROOT / "blhackbox-mcp-catalog.yaml"
MCP_JSON = ROOT / "blhackbox-mcp.json"


def test_integration_services_are_in_default_compose() -> None:
    text = COMPOSE.read_text(encoding="utf-8")
    for expected in [
        "hexstrike-ai:",
        "hexstrike-bridge-mcp:",
        "boaz-mcp:",
        "docker/hexstrike-ai.Dockerfile",
        "docker/hexstrike-mcp.Dockerfile",
        "docker/boaz-mcp.Dockerfile",
    ]:
        assert expected in text
    assert 'profiles: ["hexstrike"]' not in text
    assert 'profiles: ["boaz-lab"]' not in text


def test_integration_ports_are_documented_in_configs() -> None:
    compose = COMPOSE.read_text(encoding="utf-8")
    catalog = CATALOG.read_text(encoding="utf-8")
    mcp_json = json.loads(MCP_JSON.read_text(encoding="utf-8"))
    for port in ["8888", "9006", "9005"]:
        assert port in compose
    assert "http://localhost:9006/health" in compose
    assert "http://localhost:9005/health" in compose
    assert 'HEXSTRIKE_REF: "${HEXSTRIKE_REF:-master}"' in compose
    assert "hexstrike-bridge-mcp" in catalog
    assert "boaz-mcp" in catalog
    assert mcp_json["mcpServers"]["hexstrike"]["url"] == "http://localhost:9006/mcp"
    assert mcp_json["mcpServers"]["boaz"]["url"] == "http://localhost:9005/mcp"


def test_integration_dockerfiles_exist() -> None:
    for path in [
        ROOT / "docker" / "hexstrike-ai.Dockerfile",
        ROOT / "docker" / "hexstrike-mcp.Dockerfile",
        ROOT / "docker" / "boaz-mcp.Dockerfile",
    ]:
        assert path.exists()
        dockerfile = path.read_text(encoding="utf-8")
        assert "ENTRYPOINT" in dockerfile
    hexstrike_dockerfile = (ROOT / "docker" / "hexstrike-mcp.Dockerfile").read_text(
        encoding="utf-8"
    )
    boaz_dockerfile = (ROOT / "docker" / "boaz-mcp.Dockerfile").read_text(
        encoding="utf-8"
    )
    assert "hexstrike-ai_gamma" in hexstrike_dockerfile
    assert "BOAZ-MCP_gamma" in boaz_dockerfile
    assert "BOAZ_gamma" in boaz_dockerfile


def test_claude_code_container_wires_all_default_mcp_servers() -> None:
    dockerfile = (ROOT / "docker" / "claude-code.Dockerfile").read_text(
        encoding="utf-8"
    )
    entrypoint = (ROOT / "docker" / "claude-code-entrypoint.sh").read_text(
        encoding="utf-8"
    )

    for expected in [
        "http://kali-mcp:9001/mcp",
        "http://kali-mcp:9003/mcp",
        "http://screenshot-mcp:9004/mcp",
        "http://boaz-mcp:9005/mcp",
        "http://hexstrike-bridge-mcp:9006/mcp",
    ]:
        assert expected in dockerfile
        assert expected in entrypoint

    assert "boaz" in dockerfile
    assert "hexstrike" in dockerfile
    assert "boaz-mcp" in entrypoint
    assert "hexstrike-bridge-mcp" in entrypoint


def test_deepseek_reuses_claude_code_image_without_separate_build() -> None:
    # The DeepSeek profile is now just the Claude Code image pointed at the
    # DeepSeek API — no separate Reasonix Dockerfile/entrypoint to maintain.
    assert not (ROOT / "docker" / "deepseek.Dockerfile").exists()
    assert not (ROOT / "docker" / "deepseek-entrypoint.sh").exists()


def test_deepseek_service_is_in_compose_under_profile() -> None:
    compose = COMPOSE.read_text(encoding="utf-8")
    assert "deepseek:" in compose
    # Reuses the Claude Code image rather than building a dedicated one.
    assert "image: crhacky/blhackbox:claude-code" in compose
    assert "crhacky/blhackbox:deepseek" not in compose
    assert "docker/deepseek.Dockerfile" not in compose
    assert 'profiles: ["deepseek"]' in compose
    # Routes Claude Code at DeepSeek's Anthropic-compatible endpoint.
    assert "https://api.deepseek.com/anthropic" in compose
    assert 'ANTHROPIC_AUTH_TOKEN: "${DEEPSEEK_API_KEY:-}"' in compose
