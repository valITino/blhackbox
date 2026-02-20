# Claude Code MCP Client — runs inside the blhackbox Docker network.
# Usage:
#   docker compose run --rm claude-code
#
# Connects to the MCP Gateway at http://mcp-gateway:8080/mcp on the
# internal blhackbox_net network. No host-side install needed.

FROM node:22-slim

RUN npm install -g @anthropic-ai/claude-code

WORKDIR /root

# Pre-configure MCP to connect to the gateway via Docker network hostname.
# The gateway runs with --transport streaming (Streamable HTTP on /mcp).
# Claude Code CLI uses "type" (not "transport") in .mcp.json.
RUN echo '{"mcpServers":{"blhackbox":{"type":"http","url":"http://mcp-gateway:8080/mcp"}}}' \
    > .mcp.json

ENTRYPOINT ["claude"]
