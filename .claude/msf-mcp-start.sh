#!/bin/bash
set -euo pipefail

# Metasploit MCP Server startup script for local/Claude Code Web environments.
# Handles msfrpcd lifecycle and starts the MCP server with stdio transport.
#
# In Docker environments, the entrypoint.sh in metasploit-mcp/ handles this.
# This script is the equivalent for non-Docker (local) environments.

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

MSFRPC_USER="${MSFRPC_USER:-msf}"
MSFRPC_PASS="${MSFRPC_PASS:-msf}"
MSFRPC_PORT="${MSFRPC_PORT:-55553}"
MSFRPC_HOST="${MSFRPC_HOST:-127.0.0.1}"

# ── Pre-flight: check if metasploit-framework is installed ──────
if ! command -v msfrpcd >/dev/null 2>&1; then
    echo "[!] metasploit-framework is not installed." >&2
    echo "[!] Install it with: apt-get install -y metasploit-framework" >&2
    echo "[!] Or use Docker: docker compose up metasploit-mcp" >&2
    echo "[!] Starting MCP server anyway — tools will report msfrpcd unavailable." >&2
fi

# ── Start msfrpcd if not already running ────────────────────────
start_msfrpcd() {
    # Check if msfrpcd is already listening
    if command -v ss >/dev/null 2>&1; then
        if ss -tlnp 2>/dev/null | grep -q ":${MSFRPC_PORT}"; then
            echo "[+] msfrpcd already listening on port ${MSFRPC_PORT}." >&2
            return 0
        fi
    elif command -v netstat >/dev/null 2>&1; then
        if netstat -tlnp 2>/dev/null | grep -q ":${MSFRPC_PORT}"; then
            echo "[+] msfrpcd already listening on port ${MSFRPC_PORT}." >&2
            return 0
        fi
    fi

    if ! command -v msfrpcd >/dev/null 2>&1; then
        echo "[!] msfrpcd not found — skipping startup." >&2
        return 1
    fi

    # Start PostgreSQL if available (msfrpcd needs it for the database)
    if command -v pg_isready >/dev/null 2>&1; then
        if ! pg_isready -q 2>/dev/null; then
            echo "[*] Starting PostgreSQL..." >&2
            if command -v pg_ctlcluster >/dev/null 2>&1; then
                PG_VER=$(ls /etc/postgresql/ 2>/dev/null | sort -rn | head -1)
                PG_VER="${PG_VER:-$(ls /usr/lib/postgresql/ 2>/dev/null | sort -rn | head -1)}"
                if [ -n "$PG_VER" ]; then
                    pg_ctlcluster "$PG_VER" main start 2>&1 >&2 || true
                fi
            fi
        fi
    fi

    echo "[*] Starting msfrpcd on ${MSFRPC_HOST}:${MSFRPC_PORT} (user=${MSFRPC_USER}, SSL enabled)..." >&2
    msfrpcd -U "$MSFRPC_USER" -P "$MSFRPC_PASS" \
        -p "$MSFRPC_PORT" -a "$MSFRPC_HOST" &
    MSFRPCD_PID=$!

    # Wait for msfrpcd to start listening (up to 60s)
    echo "[*] Waiting for msfrpcd to start..." >&2
    for _i in $(seq 1 60); do
        if ! kill -0 "$MSFRPCD_PID" 2>/dev/null; then
            echo "[!] msfrpcd process exited prematurely." >&2
            return 1
        fi
        # Check port
        if command -v ss >/dev/null 2>&1 && ss -tlnp 2>/dev/null | grep -q ":${MSFRPC_PORT}"; then
            echo "[+] msfrpcd is listening on port ${MSFRPC_PORT} (took ~${_i}s)." >&2
            return 0
        elif command -v netstat >/dev/null 2>&1 && netstat -tlnp 2>/dev/null | grep -q ":${MSFRPC_PORT}"; then
            echo "[+] msfrpcd is listening on port ${MSFRPC_PORT} (took ~${_i}s)." >&2
            return 0
        fi
        sleep 1
    done

    echo "[!] msfrpcd did not start within 60 seconds." >&2
    return 1
}

# ── Ensure Python dependencies are available ────────────────────
if ! .venv/bin/python3 -c "import msgpack, httpx, mcp" 2>/dev/null; then
    echo "[*] Installing metasploit-mcp Python dependencies..." >&2
    .venv/bin/pip install -q -r metasploit-mcp/requirements.txt >&2
fi

# ── Start msfrpcd in the background ────────────────────────────
start_msfrpcd || true

# ── Start MCP server with stdio transport ───────────────────────
export MCP_TRANSPORT=stdio
export MSFRPC_HOST
export MSFRPC_PORT
export MSFRPC_USER
export MSFRPC_PASS
export MSFRPC_SSL="${MSFRPC_SSL:-true}"

exec .venv/bin/python3 metasploit-mcp/server.py
