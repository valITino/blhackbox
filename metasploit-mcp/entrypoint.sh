#!/bin/bash
set -e

# Start the Metasploit RPC daemon in the background
echo "[*] Starting msfrpcd..."
msfrpcd -U "${MSFRPC_USER:-msf}" -P "${MSFRPC_PASS:-msf}" \
    -p "${MSFRPC_PORT:-55553}" -S -a 127.0.0.1 &

# Wait for msfrpcd to become available
echo "[*] Waiting for msfrpcd to start..."
for i in $(seq 1 30); do
    if curl -sk "https://127.0.0.1:${MSFRPC_PORT:-55553}/" > /dev/null 2>&1; then
        echo "[+] msfrpcd is ready"
        break
    fi
    sleep 2
done

# Start the MCP server
echo "[*] Starting Metasploit MCP Server..."
exec /app/venv/bin/python3 /app/server.py
