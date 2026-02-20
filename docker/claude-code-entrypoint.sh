#!/bin/bash
set -euo pipefail

GATEWAY_URL="http://mcp-gateway:8080/mcp"
MAX_RETRIES=30
RETRY_INTERVAL=2

# Ensure internal Docker hostnames bypass any egress proxy (e.g. Codespaces).
export no_proxy="${no_proxy:+${no_proxy},}mcp-gateway,kali-mcp,hexstrike,ollama-mcp,ollama,agent-ingestion,agent-processing,agent-synthesis,localhost,127.0.0.1"
export NO_PROXY="$no_proxy"

echo "Waiting for MCP Gateway at $GATEWAY_URL ..."

for i in $(seq 1 $MAX_RETRIES); do
  if curl -sf "$GATEWAY_URL" > /dev/null 2>&1; then
    echo "MCP Gateway is ready."
    break
  fi
  if [ "$i" -eq "$MAX_RETRIES" ]; then
    echo "WARNING: MCP Gateway not reachable after $((MAX_RETRIES * RETRY_INTERVAL))s."
    echo "Claude Code will start anyway — run /mcp and select Reconnect if needed."
    break
  fi
  sleep $RETRY_INTERVAL
done

exec claude "$@"
