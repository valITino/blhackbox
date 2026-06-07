# HexStrike MCP

The default Docker stack runs the upstream `hexstrike-ai_gamma` MCP server on SSE port `9006`. The upstream server is cloned into the image unchanged and is loaded by `hexstrike-mcp/server.py`, which only adapts the upstream FastMCP server to the same container entrypoint style used by the other blhackbox MCP containers.

The adapter points the upstream MCP server at `HEXSTRIKE_URL=http://hexstrike-ai:8888`, where the default stack runs the HexStrike Gamma API.

Default SSE port: `9006`.
