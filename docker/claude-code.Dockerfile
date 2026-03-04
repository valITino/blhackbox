# Claude Code MCP Client — runs inside the blhackbox Docker network.
# Usage:
#   docker compose --profile claude-code run --rm claude-code
#
# Connects DIRECTLY to each MCP server via SSE on the internal
# blhackbox_net network. No MCP Gateway required. No host-side install.

FROM node:22-slim

RUN npm install -g @anthropic-ai/claude-code

# Install curl for health checks, python3/jq for data processing,
# and dnsutils for DNS resolution debugging
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    jq \
    python3 \
    dnsutils \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /root

# Pre-configure MCP to connect directly to each FastMCP server via SSE.
# All 6 MCP servers (including hexstrike-mcp adapter) are listed here.
# Wire-MCP shares kali-mcp's network namespace, so it's accessed via
# kali-mcp hostname on port 9003.
RUN echo '{ \
  "mcpServers": { \
    "kali": { \
      "type": "sse", \
      "url": "http://kali-mcp:9001/sse" \
    }, \
    "metasploit": { \
      "type": "sse", \
      "url": "http://metasploit-mcp:9002/sse" \
    }, \
    "wireshark": { \
      "type": "sse", \
      "url": "http://kali-mcp:9003/sse" \
    }, \
    "screenshot": { \
      "type": "sse", \
      "url": "http://screenshot-mcp:9004/sse" \
    }, \
    "hexstrike": { \
      "type": "sse", \
      "url": "http://hexstrike-mcp:9005/sse" \
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
