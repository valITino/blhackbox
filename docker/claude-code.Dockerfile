# Claude Code MCP Client — runs inside the blhackbox Docker network.
# Usage:
#   docker compose run --rm claude-code
#
# Connects to the MCP Gateway at http://mcp-gateway:8080/sse on the
# internal blhackbox_net network. No host-side install needed.

FROM node:22-slim

RUN npm install -g @anthropic-ai/claude-code

# Pre-configure MCP to connect to the gateway via Docker network hostname
RUN mkdir -p /root && \
    echo '{"mcpServers":{"blhackbox":{"transport":"sse","url":"http://mcp-gateway:8080/sse"}}}' \
    > /root/.mcp.json

ENTRYPOINT ["claude"]
