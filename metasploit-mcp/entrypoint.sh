#!/bin/bash
set -e

# Start the Metasploit RPC daemon in the background.
# NOTE: msfrpcd enables SSL by default. The -S flag *disables* SSL.
# We omit -S so msfrpcd listens on HTTPS, matching MSFRPC_SSL=true
# in docker-compose.yml and server.py's connection scheme.
echo "[*] Starting msfrpcd on port ${MSFRPC_PORT:-55553} (SSL enabled)..."
msfrpcd -U "${MSFRPC_USER:-msf}" -P "${MSFRPC_PASS:-msf}" \
    -p "${MSFRPC_PORT:-55553}" -a 127.0.0.1 &

# Monitor msfrpcd readiness in the background (non-blocking).
# server.py lazy-connects to msfrpcd on first tool call, so we don't
# need to wait here — just log when it's ready for operator awareness.
(
    for i in $(seq 1 90); do
        if curl -sk "https://127.0.0.1:${MSFRPC_PORT:-55553}/" > /dev/null 2>&1; then
            echo "[+] msfrpcd is ready (took ~$((i * 2))s)"
            exit 0
        fi
        sleep 2
    done
    echo "[!] msfrpcd did not respond within 180s — tools will retry on demand"
) &

# Start the MCP server immediately.
# The FastMCP SSE endpoint on port 9002 comes up in seconds,
# allowing the Docker healthcheck to pass quickly.
# msfrpcd connections are established lazily when tools are called.
echo "[*] Starting Metasploit MCP Server on port ${MCP_PORT:-9002}..."
exec /app/venv/bin/python3 /app/server.py
