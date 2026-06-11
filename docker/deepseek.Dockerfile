# DeepSeek (Reasonix) MCP Client — runs inside the blhackbox Docker network.
# Usage:
#   docker compose --profile deepseek run --rm deepseek
#
# Reasonix is a DeepSeek-native terminal coding agent (https://github.com/
# esengine/DeepSeek-Reasonix). It connects DIRECTLY to each MCP server via
# Streamable HTTP on the internal blhackbox_net network by reading the baked
# .mcp.json (Claude Code's exact mcpServers schema). No MCP Gateway required,
# no host-side install.

FROM node:22-slim

# Reasonix ships a single Go binary delivered through npm.
RUN npm install -g reasonix

# curl for health checks, python3/jq for data processing,
# and dnsutils for DNS resolution debugging
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    jq \
    python3 \
    dnsutils \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /root

# DeepSeek provider config. The API key is read from the DEEPSEEK_API_KEY
# environment variable at runtime (api_key_env) and is never written to disk.
# Default model is the cost-efficient DeepSeek-V4-Flash; switch to Pro at
# runtime with /pro (next turn) or /preset max (whole session).
RUN printf '%s\n' \
  'default_model = "deepseek-flash"' \
  '' \
  '[[providers]]' \
  'name        = "deepseek-flash"' \
  'kind        = "openai"' \
  'base_url    = "https://api.deepseek.com"' \
  'model       = "deepseek-v4-flash"' \
  'api_key_env = "DEEPSEEK_API_KEY"' \
  > reasonix.toml

# Reasonix auto-reads a Claude-Code .mcp.json from the project root and maps it
# field-for-field onto its plugins (type/url/headers, ${VAR} expansion). This is
# the same wiring the claude-code container uses. Wire-MCP shares kali-mcp's
# network namespace, so it's accessed via the kali-mcp hostname on port 9003.
RUN echo '{ \
  "mcpServers": { \
    "kali":       { "type": "http", "url": "http://kali-mcp:9001/mcp" }, \
    "wireshark":  { "type": "http", "url": "http://kali-mcp:9003/mcp" }, \
    "screenshot": { "type": "http", "url": "http://screenshot-mcp:9004/mcp" }, \
    "boaz":       { "type": "http", "url": "http://boaz-mcp:9005/mcp" }, \
    "hexstrike":  { "type": "http", "url": "http://hexstrike-bridge-mcp:9006/mcp" } \
  } \
}' > .mcp.json

# Project methodology, available on the filesystem for reference. A volume mount
# in docker-compose.yml overrides this at runtime with the latest version.
COPY CLAUDE.md /root/CLAUDE.md

# Startup script: checks each MCP server, shows status, launches Reasonix.
COPY docker/deepseek-entrypoint.sh /usr/local/bin/deepseek-entrypoint.sh
RUN chmod +x /usr/local/bin/deepseek-entrypoint.sh

ENTRYPOINT ["/usr/local/bin/deepseek-entrypoint.sh"]
