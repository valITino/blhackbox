"""SSE entrypoint for the upstream BOAZ-MCP Gamma server.

This file does not reimplement BOAZ tools. It loads the unmodified upstream
`boaz_mcp.server.BoazMCPServer` from BOAZ-MCP_gamma and exposes that low-level
MCP server over SSE so it behaves like the other blhackbox Docker MCP services.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

import uvicorn
from mcp.server.sse import SseServerTransport
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Mount, Route

DEFAULT_BOAZ_MCP_PATH = Path(os.environ.get("BOAZ_MCP_PATH", "/opt/BOAZ-MCP_gamma"))
DEFAULT_HOST = os.environ.get("BOAZ_MCP_HOST", "0.0.0.0")
DEFAULT_PORT = int(os.environ.get("BOAZ_MCP_PORT", "9005"))


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
    """Create a Starlette SSE app around the upstream BOAZ MCP server."""
    upstream_server = _load_upstream_mcp_server(upstream_path)
    sse = SseServerTransport("/messages/")

    async def handle_sse(scope: Any, receive: Any, send: Any) -> Response:
        async with sse.connect_sse(scope, receive, send) as streams:
            await upstream_server.run(
                streams[0],
                streams[1],
                upstream_server.create_initialization_options(),
            )
        return Response()

    async def sse_endpoint(request: Request) -> Response:
        return await handle_sse(request.scope, request.receive, request._send)  # type: ignore[attr-defined]

    async def health(_: Request) -> JSONResponse:
        return JSONResponse(
            {
                "status": "ok",
                "service": "boaz-mcp",
                "upstream": "BOAZ-MCP_gamma",
                "transport": "sse",
            }
        )

    return Starlette(
        routes=[
            Route("/health", endpoint=health, methods=["GET"]),
            Route("/sse", endpoint=sse_endpoint, methods=["GET"]),
            Mount("/messages/", app=sse.handle_post_message),
        ]
    )


def main() -> None:
    """Run BOAZ-MCP Gamma over SSE."""
    uvicorn.run(create_app(), host=DEFAULT_HOST, port=DEFAULT_PORT)


if __name__ == "__main__":
    main()
