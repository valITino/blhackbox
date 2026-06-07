"""Tests for the HexStrike AI Gamma SSE adapter."""

from __future__ import annotations

import importlib.util
from pathlib import Path

HEXSTRIKE_SERVER = Path(__file__).parent.parent / "hexstrike-mcp" / "server.py"


def _load_hexstrike_module():  # type: ignore[no-untyped-def]
    spec = importlib.util.spec_from_file_location("hexstrike_mcp_server", HEXSTRIKE_SERVER)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_hexstrike_server_compiles() -> None:
    source = HEXSTRIKE_SERVER.read_text(encoding="utf-8")
    compile(source, str(HEXSTRIKE_SERVER), "exec")


def test_hexstrike_adapter_uses_upstream_package(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    upstream = tmp_path / "hexstrike-ai_gamma"
    upstream.mkdir()
    (upstream / "hexstrike_mcp.py").write_text(
        "from mcp.server.fastmcp import FastMCP\n"
        "class HexStrikeClient:\n"
        "    def __init__(self, server_url, timeout):\n"
        "        self.server_url = server_url\n"
        "def setup_mcp_server(client):\n"
        "    mcp = FastMCP('hexstrike-ai-mcp')\n"
        "    @mcp.tool()\n"
        "    def server_health():\n"
        "        return {'status': 'ok'}\n"
        "    return mcp\n",
        encoding="utf-8",
    )
    monkeypatch.syspath_prepend(str(upstream))

    module = _load_hexstrike_module()
    app = module.create_app(upstream, "http://hexstrike-ai:8888", 1)
    route_paths = {getattr(route, "path", "") for route in app.routes}
    assert "/health" in route_paths
    assert "/sse" in route_paths
    assert "/messages" in route_paths or "/messages/" in route_paths


def test_hexstrike_dockerfile_clones_upstream_repo() -> None:
    dockerfile = (Path(__file__).parent.parent / "docker" / "hexstrike-mcp.Dockerfile").read_text(
        encoding="utf-8"
    )
    assert "hexstrike-ai_gamma" in dockerfile
    assert "ARG HEXSTRIKE_REF=master" in dockerfile
    assert "COPY hexstrike-mcp/server.py /app/server.py" in dockerfile


def test_hexstrike_ai_dockerfile_uses_kali_python_packages() -> None:
    dockerfile = (Path(__file__).parent.parent / "docker" / "hexstrike-ai.Dockerfile").read_text(
        encoding="utf-8"
    )
    assert "python3 -m venv --system-site-packages /opt/hexstrike-venv" in dockerfile
    assert "pip install --no-cache-dir -r requirements.txt" not in dockerfile
    # Heavy deps that exist in Kali's apt repos are installed via apt.
    for package in ["python3-pwntools", "mitmproxy"]:
        assert package in dockerfile
    # angr has no Kali/Debian apt package (python3-angr does not exist), so it
    # is installed via pip into the venv instead of apt.
    assert "python3-angr" not in dockerfile
    assert "angr>=" in dockerfile
