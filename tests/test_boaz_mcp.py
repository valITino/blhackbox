"""Tests for the BOAZ-MCP Gamma SSE adapter."""

from __future__ import annotations

import importlib.util
from pathlib import Path

BOAZ_SERVER = Path(__file__).parent.parent / "boaz-mcp" / "server.py"


def _load_boaz_module():  # type: ignore[no-untyped-def]
    spec = importlib.util.spec_from_file_location("boaz_mcp_server", BOAZ_SERVER)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_boaz_server_compiles() -> None:
    source = BOAZ_SERVER.read_text(encoding="utf-8")
    compile(source, str(BOAZ_SERVER), "exec")


def test_boaz_adapter_uses_upstream_package(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    upstream = tmp_path / "BOAZ-MCP_gamma"
    package = upstream / "boaz_mcp"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text("", encoding="utf-8")
    (package / "server.py").write_text(
        "from mcp.server import Server\n"
        "class BoazMCPServer:\n"
        "    def __init__(self):\n"
        "        self.server = Server('boaz')\n",
        encoding="utf-8",
    )
    monkeypatch.syspath_prepend(str(upstream))

    module = _load_boaz_module()
    app = module.create_app(upstream)
    route_paths = {getattr(route, "path", "") for route in app.routes}
    assert "/health" in route_paths
    assert "/sse" in route_paths
    assert "/messages" in route_paths or "/messages/" in route_paths


def test_boaz_dockerfile_clones_upstream_repos() -> None:
    dockerfile = (Path(__file__).parent.parent / "docker" / "boaz-mcp.Dockerfile").read_text(
        encoding="utf-8"
    )
    assert "BOAZ-MCP_gamma" in dockerfile
    assert "BOAZ_gamma" in dockerfile
    assert "COPY boaz-mcp/server.py /app/server.py" in dockerfile
