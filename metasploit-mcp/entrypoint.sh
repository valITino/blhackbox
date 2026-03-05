#!/bin/bash
set -e

# ── 1. Start PostgreSQL ──────────────────────────────────────────────
# msfrpcd requires an initialized PostgreSQL database for module lookups
# and session management.  Start PostgreSQL first, verify it's accepting
# connections with pg_isready, THEN initialize the MSF database.
echo "[*] Starting PostgreSQL..."
service postgresql start

# Wait for PostgreSQL to accept connections (pg_isready exits 0 when ready).
echo "[*] Waiting for PostgreSQL to accept connections..."
for i in $(seq 1 30); do
    if pg_isready -q 2>/dev/null; then
        echo "[+] PostgreSQL is ready."
        break
    fi
    if [ "$i" -eq 30 ]; then
        echo "[!] PostgreSQL did not become ready in 30s — continuing anyway."
    fi
    sleep 1
done

# ── 2. Initialize MSF database ───────────────────────────────────────
echo "[*] Initializing Metasploit database..."
msfdb init 2>&1 || echo "[!] msfdb init failed — msfrpcd may have limited functionality."

# ── 3. Start msfrpcd ─────────────────────────────────────────────────
# NOTE: msfrpcd enables SSL by default. The -S flag *disables* SSL.
# We omit -S so msfrpcd listens on HTTPS, matching MSFRPC_SSL=true
# in docker-compose.yml and server.py's connection scheme.
echo "[*] Starting msfrpcd on port ${MSFRPC_PORT:-55553} (SSL enabled)..."
msfrpcd -U "${MSFRPC_USER:-msf}" -P "${MSFRPC_PASS:-msf}" \
    -p "${MSFRPC_PORT:-55553}" -a 127.0.0.1 &
MSFRPCD_PID=$!

# Wait for msfrpcd to accept connections before starting the MCP server.
echo "[*] Waiting for msfrpcd to accept connections..."
for i in $(seq 1 60); do
    if ! kill -0 "$MSFRPCD_PID" 2>/dev/null; then
        echo "[!] msfrpcd process died. Check logs above for errors."
        exit 1
    fi
    if curl -sk "https://127.0.0.1:${MSFRPC_PORT:-55553}/" > /dev/null 2>&1; then
        echo "[+] msfrpcd is ready (took ~${i}s)."
        break
    fi
    if [ "$i" -eq 60 ]; then
        echo "[!] msfrpcd not responding after 60s — starting MCP server anyway."
    fi
    sleep 1
done

# ── 4. Start the MCP server ──────────────────────────────────────────
echo "[*] Starting Metasploit MCP Server on port ${MCP_PORT:-9002}..."
exec /app/venv/bin/python3 /app/server.py
