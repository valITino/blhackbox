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

# ── Helper: find the installed PostgreSQL version ─────────────────
# Kali-rolling ships versioned PostgreSQL (e.g. 16, 17). The version
# number is needed for pg_ctlcluster and pg_createcluster calls.
find_pg_version() {
    # Prefer /etc/postgresql/<ver> (cluster already exists)
    local ver
    ver=$(ls /etc/postgresql/ 2>/dev/null | sort -rn | head -1)
    if [ -n "$ver" ]; then
        echo "$ver"
        return
    fi
    # Fallback: check what's installed via pg_config or filesystem
    ver=$(ls /usr/lib/postgresql/ 2>/dev/null | sort -rn | head -1)
    echo "${ver:-16}"
}

# ── Helper: start PostgreSQL using pg_ctlcluster (Debian/Kali way) ─
# Docker containers don't have systemd, so `service postgresql start`
# and `msfdb init` both fail when they try to invoke systemctl.
# We use pg_ctlcluster directly — this is what Kali's postgresql-common
# wrapper actually calls under the hood.
start_postgres_direct() {
    local pgver="$1"
    local cluster="main"
    local pgdata="/var/lib/postgresql/${pgver}/${cluster}"

    # Ensure data directory exists and has correct ownership
    if [ ! -d "$pgdata" ]; then
        echo "[*] Creating PostgreSQL ${pgver} cluster '${cluster}'..."
        # pg_createcluster handles initdb, config, and directory setup
        pg_createcluster "$pgver" "$cluster" 2>&1 || {
            echo "[!] pg_createcluster failed — trying manual initdb..."
            local pgbin="/usr/lib/postgresql/${pgver}/bin"
            mkdir -p "$pgdata"
            chown postgres:postgres "$pgdata"
            su - postgres -c "${pgbin}/initdb -D ${pgdata}" 2>&1 || true
        }
    fi

    # Fix ownership (common issue after volume mounts or fresh containers)
    chown -R postgres:postgres "/var/lib/postgresql/${pgver}" 2>/dev/null || true
    # Also fix /run/postgresql for socket directory
    mkdir -p /run/postgresql
    chown postgres:postgres /run/postgresql
    chmod 2775 /run/postgresql

    # Start the cluster
    echo "[*] Starting PostgreSQL ${pgver}/${cluster}..."
    pg_ctlcluster "$pgver" "$cluster" start 2>&1 || {
        echo "[!] pg_ctlcluster start failed — trying pg_ctl directly..."
        local pgbin="/usr/lib/postgresql/${pgver}/bin"
        su - postgres -c "${pgbin}/pg_ctl -D ${pgdata} -l /var/log/postgresql/startup.log start" 2>&1 || true
    }
}

# ── Helper: ensure msf database and user exist ────────────────────
setup_msf_database() {
    # Create the msf user if it doesn't exist
    su - postgres -c "psql -tAc \"SELECT 1 FROM pg_roles WHERE rolname='msf'\"" 2>/dev/null | grep -q 1 || {
        echo "[*] Creating PostgreSQL user 'msf'..."
        su - postgres -c "createuser -S -R -D msf" 2>&1 || true
        su - postgres -c "psql -c \"ALTER USER msf WITH PASSWORD 'msf'\"" 2>&1 || true
    }

    # Create the msf database if it doesn't exist
    su - postgres -c "psql -tAc \"SELECT 1 FROM pg_database WHERE datname='msf'\"" 2>/dev/null | grep -q 1 || {
        echo "[*] Creating database 'msf'..."
        su - postgres -c "createdb -O msf msf" 2>&1 || true
    }

    # Write database.yml for Metasploit
    local dbconf="/usr/share/metasploit-framework/config/database.yml"
    mkdir -p "$(dirname "$dbconf")"
    cat > "$dbconf" <<YAML
production:
  adapter: postgresql
  database: msf
  username: msf
  password: msf
  host: 127.0.0.1
  port: 5432
  pool: 5
  timeout: 5

development:
  adapter: postgresql
  database: msf
  username: msf
  password: msf
  host: 127.0.0.1
  port: 5432
  pool: 5
  timeout: 5
YAML
    echo "[+] database.yml written."
}

# ── Background: PostgreSQL + msfrpcd setup ────────────────────────
(
    echo "[*] Initializing Metasploit database (background)..."

    PG_VERSION=$(find_pg_version)
    echo "[*] Detected PostgreSQL version: ${PG_VERSION}"

    # Strategy: Try msfdb init first (it handles everything when it works).
    # If it fails (common in Docker due to systemd dependency), fall back
    # to manual PostgreSQL startup via pg_ctlcluster.
    if msfdb init 2>&1; then
        echo "[+] msfdb init succeeded."
    else
        echo "[!] msfdb init failed (expected in Docker — no systemd)."
        echo "[*] Falling back to manual PostgreSQL setup via pg_ctlcluster..."

        start_postgres_direct "$PG_VERSION"

        # Wait for PostgreSQL to accept connections (up to 30s)
        PG_READY=false
        for _i in $(seq 1 30); do
            if pg_isready -q 2>/dev/null; then
                PG_READY=true
                break
            fi
            sleep 1
        done

        if [ "$PG_READY" = "true" ]; then
            echo "[+] PostgreSQL is accepting connections."
            setup_msf_database
        else
            echo "[!] PostgreSQL failed to start — msfrpcd will run without DB."
            echo "[!] Debug info:"
            pg_lsclusters 2>&1 || true
            ls -la /var/lib/postgresql/ 2>&1 || true
        fi
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

    # Verify msfrpcd is actually listening before declaring success.
    # This catches startup crashes, missing libraries, and config errors
    # that would otherwise go unnoticed until the first tool call.
    echo "[*] Waiting for msfrpcd to start listening on port ${MSFRPC_PORT}..."
    MSFRPCD_READY=false
    for _i in $(seq 1 90); do
        # Check if the process is still alive
        if ! kill -0 "$MSFRPCD_PID" 2>/dev/null; then
            echo "[!] msfrpcd process (PID ${MSFRPCD_PID}) exited prematurely."
            wait "$MSFRPCD_PID" 2>/dev/null
            echo "[!] msfrpcd exit code: $?"
            break
        fi
        # Check if the port is open (try ss first, fall back to netstat)
        if ss -tlnp 2>/dev/null | grep -q ":${MSFRPC_PORT}" || \
           netstat -tlnp 2>/dev/null | grep -q ":${MSFRPC_PORT}"; then
            MSFRPCD_READY=true
            echo "[+] msfrpcd is listening on port ${MSFRPC_PORT} (took ~${_i}s)."
            break
        fi
        sleep 1
    done

    if [ "$MSFRPCD_READY" = "false" ]; then
        echo "[!] ERROR: msfrpcd is NOT listening on port ${MSFRPC_PORT} after 90 seconds."
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

# ── Foreground: Start MCP server immediately ──────────────────────
# The FastMCP SSE endpoint on port 9002 starts in <2 seconds, allowing
# the Docker healthcheck to pass. Tool calls that require msfrpcd will
# retry automatically via MSFRPCClient.login() (15 retries × 6s = 90s).
echo "[*] Starting Metasploit MCP Server on port ${MCP_PORT}..."
exec /app/venv/bin/python3 /app/server.py
