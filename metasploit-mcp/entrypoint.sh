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

MSFRPC_USER="${MSFRPC_USER:-msf}"
MSFRPC_PASS="${MSFRPC_PASS:-msf}"
MSFRPC_PORT="${MSFRPC_PORT:-55553}"
MCP_PORT="${MCP_PORT:-9002}"

# ── Background: PostgreSQL + msfrpcd setup ────────────────────────────
(
    echo "[*] Initializing Metasploit database (background)..."

    # Step 1: Ensure PostgreSQL data directory has correct ownership.
    # On fresh containers or after volume mounts, the data directory may
    # be owned by root, causing pg_ctlcluster to fail.
    PG_VERSION=$(ls /etc/postgresql/ 2>/dev/null | head -1)
    if [ -n "$PG_VERSION" ] && [ -d "/var/lib/postgresql/${PG_VERSION}/main" ]; then
        chown -R postgres:postgres "/var/lib/postgresql/${PG_VERSION}" 2>/dev/null || true
    fi

    # Step 2: Start PostgreSQL — try msfdb init first (handles cluster
    # creation, user/DB setup, and database.yml), fall back to manual.
    if msfdb init 2>&1; then
        echo "[+] msfdb init succeeded."
    else
        echo "[!] msfdb init failed — attempting manual PostgreSQL setup..."
        # Fallback: start PostgreSQL manually and retry
        service postgresql start 2>&1 || true
        for _i in $(seq 1 30); do
            pg_isready -q 2>/dev/null && break
            sleep 1
        done
        if pg_isready -q 2>/dev/null; then
            echo "[+] PostgreSQL started manually."
            msfdb init 2>&1 || echo "[!] msfdb init retry failed — msfrpcd will run without DB."
        else
            echo "[!] PostgreSQL failed to start — msfrpcd will run without DB."
        fi
    fi

    # Verify PostgreSQL is running (informational only)
    if pg_isready -q 2>/dev/null; then
        echo "[+] PostgreSQL is accepting connections."
    else
        echo "[!] PostgreSQL is not running — msfrpcd may have limited functionality."
    fi

    # Step 3: Start msfrpcd.
    # NOTE: msfrpcd enables SSL by default. The -S flag *disables* SSL.
    # We omit -S so msfrpcd listens on HTTPS, matching MSFRPC_SSL=true
    # in docker-compose.yml and server.py's connection scheme.
    #
    # Use -f to run msfrpcd in the foreground within this background
    # subshell. Without -f, msfrpcd daemonizes (forks), and the parent
    # process exits immediately — which means the subshell exits and
    # we lose the ability to detect crashes. With -f, msfrpcd stays
    # attached to this subshell, and the "msfrpcd exited" message below
    # fires only when it actually terminates.
    echo "[*] Starting msfrpcd on 127.0.0.1:${MSFRPC_PORT} (user=${MSFRPC_USER}, SSL enabled)..."
    msfrpcd -U "$MSFRPC_USER" -P "$MSFRPC_PASS" \
        -p "$MSFRPC_PORT" -a 127.0.0.1 -f &
    MSFRPCD_PID=$!

    # Step 4: Verify msfrpcd is actually listening before declaring success.
    # This catches startup crashes, missing libraries, and config errors
    # that would otherwise go unnoticed until the first tool call.
    echo "[*] Waiting for msfrpcd to start listening on port ${MSFRPC_PORT}..."
    MSFRPCD_READY=false
    for _i in $(seq 1 60); do
        # Check if the process is still alive
        if ! kill -0 "$MSFRPCD_PID" 2>/dev/null; then
            echo "[!] msfrpcd process (PID ${MSFRPCD_PID}) exited prematurely."
            wait "$MSFRPCD_PID" 2>/dev/null
            echo "[!] msfrpcd exit code: $?"
            break
        fi
        # Check if the port is open
        if ss -tlnp 2>/dev/null | grep -q ":${MSFRPC_PORT}"; then
            MSFRPCD_READY=true
            echo "[+] msfrpcd is listening on port ${MSFRPC_PORT} (took ~${_i}s)."
            break
        fi
        sleep 1
    done

    if [ "$MSFRPCD_READY" = "false" ]; then
        echo "[!] ERROR: msfrpcd is NOT listening on port ${MSFRPC_PORT} after 60 seconds."
        echo "[!] The MCP server will start but all Metasploit tools will fail."
        echo "[!] Debug: Check msfrpcd logs above for startup errors."
        echo "[!] Common fixes:"
        echo "[!]   1. Verify metasploit-framework is installed: dpkg -l | grep metasploit"
        echo "[!]   2. Verify msfrpcd binary exists: which msfrpcd"
        echo "[!]   3. Check PostgreSQL: pg_isready"
        echo "[!]   4. Check database.yml: cat /usr/share/metasploit-framework/config/database.yml"
    fi

    # Wait for msfrpcd process to keep the subshell alive
    wait "$MSFRPCD_PID" 2>/dev/null
    echo "[!] msfrpcd exited (code $?)."
) &
BACKEND_PID=$!

# ── Foreground: Start MCP server immediately ──────────────────────────
# The FastMCP SSE endpoint on port 9002 starts in <2 seconds, allowing
# the Docker healthcheck to pass. Tool calls that require msfrpcd will
# retry automatically via MSFRPCClient.login() (15 retries × 6s = 90s).
echo "[*] Starting Metasploit MCP Server on port ${MCP_PORT}..."
exec /app/venv/bin/python3 /app/server.py
