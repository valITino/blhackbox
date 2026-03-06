#!/bin/bash
# kali-mcp entrypoint — starts PostgreSQL for Metasploit (if available),
# then launches the MCP server.
#
# PostgreSQL is started in the background so msfconsole has database
# support for `db_nmap`, module caching, etc.  If PostgreSQL fails to
# start, Metasploit still works (without DB features).

MSFRPC_USER="${MSFRPC_USER:-msf}"
MSFRPC_PASS="${MSFRPC_PASS:-msf}"
MCP_PORT="${MCP_PORT:-9001}"

# ── Helper: find the installed PostgreSQL version ─────────────────
find_pg_version() {
    local ver
    ver=$(ls /etc/postgresql/ 2>/dev/null | sort -rn | head -1)
    if [ -n "$ver" ]; then
        echo "$ver"
        return
    fi
    ver=$(ls /usr/lib/postgresql/ 2>/dev/null | sort -rn | head -1)
    echo "${ver:-16}"
}

# ── Helper: start PostgreSQL for Metasploit ──────────────────────
start_postgres() {
    if ! command -v pg_isready >/dev/null 2>&1; then
        echo "[*] PostgreSQL not installed — Metasploit will run without DB."
        return 1
    fi

    # Already running?
    if pg_isready -q 2>/dev/null; then
        echo "[+] PostgreSQL is already running."
        return 0
    fi

    local pgver
    pgver=$(find_pg_version)
    local cluster="main"
    local pgdata="/var/lib/postgresql/${pgver}/${cluster}"

    # Create cluster if needed
    if [ ! -d "$pgdata" ]; then
        echo "[*] Creating PostgreSQL ${pgver} cluster..."
        pg_createcluster "$pgver" "$cluster" 2>&1 || {
            echo "[!] pg_createcluster failed."
            return 1
        }
    fi

    # Fix ownership
    chown -R postgres:postgres "/var/lib/postgresql/${pgver}" 2>/dev/null || true
    mkdir -p /run/postgresql
    chown postgres:postgres /run/postgresql
    chmod 2775 /run/postgresql

    # Start
    echo "[*] Starting PostgreSQL ${pgver}..."
    pg_ctlcluster "$pgver" "$cluster" start 2>&1 || {
        echo "[!] PostgreSQL failed to start."
        return 1
    }

    # Wait for readiness
    for _i in $(seq 1 30); do
        if pg_isready -q 2>/dev/null; then
            echo "[+] PostgreSQL is accepting connections."
            return 0
        fi
        sleep 1
    done

    echo "[!] PostgreSQL did not become ready in 30s."
    return 1
}

# ── Helper: ensure msf database and user exist ────────────────────
setup_msf_database() {
    su - postgres -c "psql -tAc \"SELECT 1 FROM pg_roles WHERE rolname='msf'\"" 2>/dev/null | grep -q 1 || {
        echo "[*] Creating PostgreSQL user 'msf'..."
        su - postgres -c "createuser -S -R -D msf" 2>&1 || true
        su - postgres -c "psql -c \"ALTER USER msf WITH PASSWORD 'msf'\"" 2>&1 || true
    }

    su - postgres -c "psql -tAc \"SELECT 1 FROM pg_database WHERE datname='msf'\"" 2>/dev/null | grep -q 1 || {
        echo "[*] Creating database 'msf'..."
        su - postgres -c "createdb -O msf msf" 2>&1 || true
    }

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
YAML
    echo "[+] Metasploit database.yml written."
}

# ── Background: Initialize PostgreSQL + Metasploit DB ─────────────
if command -v msfconsole >/dev/null 2>&1; then
    (
        echo "[*] Initializing Metasploit database (background)..."

        # Try msfdb init first (handles everything when it works)
        if msfdb init 2>&1; then
            echo "[+] msfdb init succeeded."
        else
            echo "[!] msfdb init failed (expected in Docker — no systemd)."
            echo "[*] Falling back to manual PostgreSQL setup..."

            if start_postgres; then
                setup_msf_database
            fi
        fi

        if pg_isready -q 2>/dev/null; then
            echo "[+] PostgreSQL ready — Metasploit has full DB support."
        else
            echo "[!] PostgreSQL not running — Metasploit will work without DB."
        fi
    ) &
else
    echo "[*] Metasploit Framework not installed — skipping DB setup."
fi

# ── Foreground: Start MCP server ──────────────────────────────────
echo "[*] Starting Kali MCP Server on port ${MCP_PORT}..."
exec /app/venv/bin/python3 /app/server.py
