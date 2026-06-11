"""Streamable HTTP entrypoint for the upstream HexStrike AI Gamma MCP server.

This file does not reimplement HexStrike tools. It loads the unmodified upstream
`hexstrike_mcp.py` module from a cloned `hexstrike-ai_gamma` checkout and runs
its FastMCP server over Streamable HTTP so it behaves like the other blhackbox
Docker MCP services.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import uvicorn
from mcp.server.transport_security import TransportSecuritySettings
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

DEFAULT_HEXSTRIKE_PATH = Path(os.environ.get("HEXSTRIKE_PATH", "/opt/hexstrike-ai"))
DEFAULT_HEXSTRIKE_URL = os.environ.get("HEXSTRIKE_URL", "http://hexstrike-ai:8888")
DEFAULT_TIMEOUT = int(os.environ.get("HEXSTRIKE_REQUEST_TIMEOUT", "300"))
DEFAULT_HOST = os.environ.get("HEXSTRIKE_MCP_HOST", "0.0.0.0")
DEFAULT_PORT = int(os.environ.get("HEXSTRIKE_MCP_PORT", "9006"))
DEFAULT_ALLOWED_HOSTS = os.environ.get(
    "HEXSTRIKE_MCP_ALLOWED_HOSTS",
    "hexstrike-bridge-mcp:*,blhackbox-hexstrike-mcp:*,localhost:*,127.0.0.1:*",
)
DEFAULT_ALLOWED_ORIGINS = os.environ.get(
    "HEXSTRIKE_MCP_ALLOWED_ORIGINS",
    "http://hexstrike-bridge-mcp:*,http://blhackbox-hexstrike-mcp:*,http://localhost:*,http://127.0.0.1:*",
)


def _split_csv(value: str) -> list[str]:
    """Return non-empty comma-separated values with surrounding whitespace removed."""
    return [item.strip() for item in value.split(",") if item.strip()]


def _add_upstream_to_path(upstream_path: Path = DEFAULT_HEXSTRIKE_PATH) -> None:
    """Make the cloned upstream hexstrike-ai_gamma checkout importable."""
    resolved = upstream_path.expanduser().resolve()
    if str(resolved) not in sys.path:
        sys.path.insert(0, str(resolved))


def _load_upstream_fastmcp(
    upstream_path: Path = DEFAULT_HEXSTRIKE_PATH,
    server_url: str = DEFAULT_HEXSTRIKE_URL,
    timeout: int = DEFAULT_TIMEOUT,
    allowed_hosts: str = DEFAULT_ALLOWED_HOSTS,
    allowed_origins: str = DEFAULT_ALLOWED_ORIGINS,
):
    """Instantiate the upstream HexStrike FastMCP server without changing it."""
    _add_upstream_to_path(upstream_path)
    from hexstrike_mcp import HexStrikeClient, setup_mcp_server

    client = HexStrikeClient(server_url, timeout)
    fastmcp = setup_mcp_server(client)
    fastmcp.settings.transport_security = TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=_split_csv(allowed_hosts),
        allowed_origins=_split_csv(allowed_origins),
    )
    return fastmcp


def create_app(
    upstream_path: Path = DEFAULT_HEXSTRIKE_PATH,
    server_url: str = DEFAULT_HEXSTRIKE_URL,
    timeout: int = DEFAULT_TIMEOUT,
    allowed_hosts: str = DEFAULT_ALLOWED_HOSTS,
    allowed_origins: str = DEFAULT_ALLOWED_ORIGINS,
) -> Starlette:
    """Create a Starlette app around the upstream HexStrike FastMCP server."""
    fastmcp = _load_upstream_fastmcp(
        upstream_path,
        server_url,
        timeout,
        allowed_hosts,
        allowed_origins,
    )
    app = fastmcp.streamable_http_app()

    async def health(_: Request) -> JSONResponse:
        return JSONResponse(
            {
                "status": "ok",
                "service": "hexstrike-bridge-mcp",
                "upstream": "hexstrike-ai_gamma",
                "hexstrike_url": server_url,
                "transport": "streamable-http",
            }
        )

    app.routes.append(Route("/health", endpoint=health, methods=["GET"]))
    return app


def main() -> None:
    """Run HexStrike AI Gamma MCP over Streamable HTTP."""
    uvicorn.run(create_app(), host=DEFAULT_HOST, port=DEFAULT_PORT)


if __name__ == "__main__":
    main()
