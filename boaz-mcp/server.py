"""Streamable HTTP entrypoint for the upstream BOAZ-MCP Gamma server.

This file does not reimplement BOAZ tools. It loads the unmodified upstream
`boaz_mcp.server.BoazMCPServer` from BOAZ-MCP_gamma and exposes that low-level
MCP server over Streamable HTTP so it behaves like the other blhackbox Docker
MCP services.
"""

from __future__ import annotations

import contextlib
import os
import sys
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import uvicorn
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.types import Receive, Scope, Send

DEFAULT_BOAZ_MCP_PATH = Path(os.environ.get("BOAZ_MCP_PATH", "/opt/BOAZ-MCP_gamma"))
DEFAULT_HOST = os.environ.get("BOAZ_MCP_HOST", "0.0.0.0")
DEFAULT_PORT = int(os.environ.get("BOAZ_MCP_PORT", "9005"))


class _StreamableHTTPASGIApp:
    """ASGI wrapper around the session manager's request handler.

    Mounting the handler with a Starlette ``Route`` whose endpoint is a class
    instance (rather than ``Mount``) serves the Streamable HTTP transport at the
    exact ``/mcp`` path, matching the FastMCP-based servers. ``Mount`` would
    redirect ``/mcp`` to ``/mcp/`` and break clients that POST to ``/mcp``.
    """

    def __init__(self, session_manager: StreamableHTTPSessionManager) -> None:
        self.session_manager = session_manager

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        await self.session_manager.handle_request(scope, receive, send)


def _add_upstream_to_path(upstream_path: Path = DEFAULT_BOAZ_MCP_PATH) -> None:
    """Make the cloned upstream BOAZ-MCP_gamma package importable."""
    resolved = upstream_path.expanduser().resolve()
    if str(resolved) not in sys.path:
        sys.path.insert(0, str(resolved))


def _load_upstream_mcp_server(upstream_path: Path = DEFAULT_BOAZ_MCP_PATH) -> Any:
    """Instantiate the upstream BOAZ-MCP Gamma server without changing it."""
    _add_upstream_to_path(upstream_path)
    from boaz_mcp.server import BoazMCPServer

    return BoazMCPServer().server


def create_app(upstream_path: Path = DEFAULT_BOAZ_MCP_PATH) -> Starlette:
    """Create a Starlette Streamable HTTP app around the upstream BOAZ MCP server."""
    upstream_server = _load_upstream_mcp_server(upstream_path)
    session_manager = StreamableHTTPSessionManager(
        app=upstream_server,
        json_response=False,
        stateless=False,
    )

    async def health(_: Request) -> JSONResponse:
        return JSONResponse(
            {
                "status": "ok",
                "service": "boaz-mcp",
                "upstream": "BOAZ-MCP_gamma",
                "transport": "streamable-http",
            }
        )

    @contextlib.asynccontextmanager
    async def lifespan(_: Starlette) -> AsyncIterator[None]:
        # The session manager's task group must be running for the duration of
        # the app; handle_request fails otherwise.
        async with session_manager.run():
            yield

    return Starlette(
        routes=[
            Route("/health", endpoint=health, methods=["GET"]),
            Route("/mcp", endpoint=_StreamableHTTPASGIApp(session_manager)),
        ],
        lifespan=lifespan,
    )


def main() -> None:
    """Run BOAZ-MCP Gamma over Streamable HTTP."""
    uvicorn.run(create_app(), host=DEFAULT_HOST, port=DEFAULT_PORT)


if __name__ == "__main__":
    main()
