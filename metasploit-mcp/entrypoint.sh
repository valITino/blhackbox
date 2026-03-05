#!/bin/bash
# metasploit-mcp entrypoint — starts PostgreSQL, msfrpcd, and MCP server.
#
# Design: PostgreSQL and msfrpcd are initialized in a background subshell
# while the MCP server starts in the foreground. The Docker healthcheck
# verifies the MCP SSE endpoint (port 9002) is reachable — the container
# reports healthy as soon as the MCP server is up. msfrpcd availability is
# managed internally by MSFRPCClient.login() retry logic (15 × 6s = 90s).
#
# No `set -e` — errors are handled explicitly to prevent crash loops.

# ── Background: PostgreSQL + msfrpcd setup ────────────────────────────
(
    echo "[*] Initializing Metasploit database (background)..."

    # msfdb init handles everything: creates cluster, starts PostgreSQL,
    # creates the msf user/database, and writes database.yml.
    if msfdb init 2>&1; then
        echo "[+] msfdb init succeeded."
    else
        echo "[!] msfdb init failed — attempting manual PostgreSQL setup..."
        # Fallback: start PostgreSQL manually and retry
        service postgresql start 2>&1 || true
        for _i in $(seq 1 15); do
            pg_isready -q 2>/dev/null && break
            sleep 1
        done
        msfdb init 2>&1 || echo "[!] msfdb init retry failed — msfrpcd will run without DB."
    fi

    # Verify PostgreSQL is running (informational only)
    if pg_isready -q 2>/dev/null; then
        echo "[+] PostgreSQL is accepting connections."
    else
        echo "[!] PostgreSQL is not running — msfrpcd may have limited functionality."
    fi

    # Start msfrpcd.
    # NOTE: msfrpcd enables SSL by default. The -S flag *disables* SSL.
    # We omit -S so msfrpcd listens on HTTPS, matching MSFRPC_SSL=true
    # in docker-compose.yml and server.py's connection scheme.
    echo "[*] Starting msfrpcd on port ${MSFRPC_PORT:-55553} (SSL enabled)..."
    msfrpcd -U "${MSFRPC_USER:-msf}" -P "${MSFRPC_PASS:-msf}" \
        -p "${MSFRPC_PORT:-55553}" -a 127.0.0.1

    # If msfrpcd exits, log it. The MCP server will return errors on
    # tool calls, but the container stays up so it can be debugged.
    echo "[!] msfrpcd exited (code $?)."
) &
BACKEND_PID=$!

# ── Foreground: Start MCP server immediately ──────────────────────────
# The FastMCP SSE endpoint on port 9002 starts in <2 seconds, allowing
# the Docker healthcheck to pass. Tool calls that require msfrpcd will
# retry automatically via MSFRPCClient.login() (15 × 6s = 90s window).
echo "[*] Starting Metasploit MCP Server on port ${MCP_PORT:-9002}..."
exec /app/venv/bin/python3 /app/server.py
