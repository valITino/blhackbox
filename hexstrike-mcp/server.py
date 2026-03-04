#!/usr/bin/env python3
"""blhackbox entrypoint for the HexStrike MCP server.

Imports and runs the upstream hexstrike_mcp.py with SSE transport
so it integrates with the blhackbox Docker Compose stack.

The upstream hexstrike_mcp.py uses stdio transport by default.
This wrapper overrides setup_mcp_server to set host/port for SSE,
then calls the standard main() entry point flow.
"""

import logging
import os
import sys

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("hexstrike-mcp-entrypoint")

# Import from the hexstrike_mcp module
import hexstrike_mcp

MCP_PORT = int(os.environ.get("MCP_PORT", "9005"))
MCP_HOST = os.environ.get("MCP_HOST", "0.0.0.0")
HEXSTRIKE_URL = os.environ.get("HEXSTRIKE_URL", "http://hexstrike:8888")
HEXSTRIKE_TIMEOUT = int(os.environ.get("HEXSTRIKE_TIMEOUT", "300"))


def main():
    """Start HexStrike MCP server with SSE transport for Docker."""
    logger.info(
        "Starting HexStrike MCP Server (SSE on %s:%d, backend: %s)",
        MCP_HOST, MCP_PORT, HEXSTRIKE_URL,
    )

    # Initialize the HexStrike client (connects to Flask API)
    client = hexstrike_mcp.HexStrikeClient(HEXSTRIKE_URL, HEXSTRIKE_TIMEOUT)

    # Check server health
    health = client.check_health()
    if "error" in health:
        logger.warning(
            "HexStrike API unreachable at %s: %s — tools will retry on demand",
            HEXSTRIKE_URL, health["error"],
        )
    else:
        avail = health.get("total_tools_available", 0)
        total = health.get("total_tools_count", 0)
        logger.info(
            "HexStrike API healthy (v%s, %d/%d tools available)",
            health.get("version", "?"), avail, total,
        )

    # Set up the MCP server using the upstream setup function
    mcp = hexstrike_mcp.setup_mcp_server(client)

    # Override transport settings for SSE (Docker network)
    transport = os.environ.get("MCP_TRANSPORT", "sse")
    mcp.settings.host = MCP_HOST
    mcp.settings.port = MCP_PORT
    logger.info("HexStrike MCP ready — %s transport on port %d", transport, MCP_PORT)
    mcp.run(transport=transport)


if __name__ == "__main__":
    main()
