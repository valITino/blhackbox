# Claude Code MCP Client — runs inside the blhackbox Docker network.
# Usage:
#   docker compose run --rm claude-code
#
# Connects to the MCP Gateway at http://mcp-gateway:8080/mcp on the
# internal blhackbox_net network. No host-side install needed.

FROM node:22-slim

RUN npm install -g @anthropic-ai/claude-code

# Install curl for gateway health checks
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

WORKDIR /root

# Pre-configure MCP to connect to the gateway via Docker network hostname.
# The gateway runs with --transport streaming (Streamable HTTP on /mcp).
# Claude Code CLI uses "type": "http" for Streamable HTTP in .mcp.json.
RUN echo '{"mcpServers":{"blhackbox":{"type":"http","url":"http://mcp-gateway:8080/mcp"}}}' \
    > .mcp.json

# Startup script: wait for the MCP Gateway to be reachable, then launch Claude.
# Without this, Claude Code may start before the gateway is ready and report
# "Status: failed" on /mcp.
COPY docker/claude-code-entrypoint.sh /usr/local/bin/claude-code-entrypoint.sh
RUN chmod +x /usr/local/bin/claude-code-entrypoint.sh

ENTRYPOINT ["/usr/local/bin/claude-code-entrypoint.sh"]
