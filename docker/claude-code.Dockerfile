# Claude Code MCP Client — runs inside the blhackbox Docker network.
# Usage:
#   docker compose --profile claude-code run --rm claude-code
#
# Connects DIRECTLY to each MCP server via SSE on the internal
# blhackbox_net network. No MCP Gateway required. No host-side install.

FROM node:22-slim

RUN npm install -g @anthropic-ai/claude-code

# Install curl for health checks
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

WORKDIR /root

# Pre-configure MCP to connect directly to each server via SSE.
# Each MCP server runs FastMCP with SSE transport on its respective port.
# This bypasses the MCP Gateway entirely — simpler, faster, more reliable.
RUN echo '{ \
  "mcpServers": { \
    "kali": { \
      "type": "sse", \
      "url": "http://kali-mcp:9001/sse" \
    }, \
    "hexstrike": { \
      "type": "sse", \
      "url": "http://hexstrike:8888/sse" \
    }, \
    "ollama-pipeline": { \
      "type": "sse", \
      "url": "http://ollama-mcp:9000/sse" \
    } \
  } \
}' > .mcp.json

# Startup script: checks each MCP server, shows status, launches Claude.
COPY docker/claude-code-entrypoint.sh /usr/local/bin/claude-code-entrypoint.sh
RUN chmod +x /usr/local/bin/claude-code-entrypoint.sh

ENTRYPOINT ["/usr/local/bin/claude-code-entrypoint.sh"]
