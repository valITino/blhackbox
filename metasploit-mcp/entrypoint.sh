#!/bin/bash
set -e

# Initialize the Metasploit database (PostgreSQL).
# msfrpcd requires an initialized database for module lookups and session
# management.  This is idempotent — safe to run on every container start.
echo "[*] Initializing Metasploit database..."
msfdb init 2>/dev/null || {
    echo "[!] msfdb init failed — attempting manual PostgreSQL start..."
    service postgresql start 2>/dev/null || true
    # Give PostgreSQL a moment to start
    sleep 2
    msfdb init 2>/dev/null || echo "[!] msfdb init failed again — msfrpcd may still work without DB"
}

# Start the Metasploit RPC daemon in the background.
# NOTE: msfrpcd enables SSL by default. The -S flag *disables* SSL.
# We omit -S so msfrpcd listens on HTTPS, matching MSFRPC_SSL=true
# in docker-compose.yml and server.py's connection scheme.
echo "[*] Starting msfrpcd on port ${MSFRPC_PORT:-55553} (SSL enabled)..."
msfrpcd -U "${MSFRPC_USER:-msf}" -P "${MSFRPC_PASS:-msf}" \
    -p "${MSFRPC_PORT:-55553}" -a 127.0.0.1 &
MSFRPCD_PID=$!

# Block-wait for msfrpcd to become responsive.
# The MCP server retries on its own, but waiting here ensures msfrpcd is
# actually running before we declare the container healthy.
MAX_WAIT=120
WAITED=0
echo "[*] Waiting for msfrpcd to become responsive (max ${MAX_WAIT}s)..."
while [ "$WAITED" -lt "$MAX_WAIT" ]; do
    # Check if msfrpcd process is still alive
    if ! kill -0 "$MSFRPCD_PID" 2>/dev/null; then
        echo "[!] msfrpcd process died — restarting..."
        msfrpcd -U "${MSFRPC_USER:-msf}" -P "${MSFRPC_PASS:-msf}" \
            -p "${MSFRPC_PORT:-55553}" -a 127.0.0.1 &
        MSFRPCD_PID=$!
        sleep 5
        WAITED=$((WAITED + 5))
        continue
    fi

    if curl -sk "https://127.0.0.1:${MSFRPC_PORT:-55553}/" > /dev/null 2>&1; then
        echo "[+] msfrpcd is ready (took ~${WAITED}s)"
        break
    fi
    sleep 2
    WAITED=$((WAITED + 2))
done

if [ "$WAITED" -ge "$MAX_WAIT" ]; then
    echo "[!] msfrpcd did not respond within ${MAX_WAIT}s — MCP server will retry on demand"
fi

# Start the MCP server.
# The FastMCP SSE endpoint on port 9002 comes up in seconds,
# allowing the Docker healthcheck to pass quickly.
echo "[*] Starting Metasploit MCP Server on port ${MCP_PORT:-9002}..."
exec /app/venv/bin/python3 /app/server.py
