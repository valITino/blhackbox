#!/bin/bash
# MCP Server Health Check — validates all configured MCP server backends
# before or after startup. Designed to surface issues early rather than
# letting them silently fail during tool calls.
#
# Usage: .claude/mcp-health-check.sh [--fix]
#   --fix: Attempt to automatically fix issues (start services, init submodules)

set -uo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

FIX_MODE="${1:-}"
ISSUES=0
FIXED=0

# ── Helpers ─────────────────────────────────────────────────────
ok()   { echo "[+] $*"; }
warn() { echo "[!] $*"; ISSUES=$((ISSUES + 1)); }
info() { echo "[*] $*"; }
fix()  { echo "[~] FIX: $*"; FIXED=$((FIXED + 1)); }

# ── 1. HexStrike MCP: check submodule and entrypoint ───────────
info "Checking HexStrike MCP server..."

if [ ! -f "hexstrike/hexstrike_mcp.py" ]; then
    warn "hexstrike/hexstrike_mcp.py not found (git submodule not initialized)"
    if [ "$FIX_MODE" = "--fix" ]; then
        info "Initializing hexstrike git submodule..."
        if git submodule init && git submodule update --depth 1 2>/dev/null; then
            fix "hexstrike submodule initialized"
        else
            warn "Failed to initialize hexstrike submodule (network issue?)"
        fi
    fi
else
    ok "hexstrike/hexstrike_mcp.py exists"
fi

# Check Python import
if [ -f ".venv/bin/python3" ]; then
    if .venv/bin/python3 -c "import hexstrike.hexstrike_mcp" 2>/dev/null; then
        ok "hexstrike_mcp is importable"
    else
        warn "hexstrike_mcp cannot be imported (missing dependencies?)"
        if [ "$FIX_MODE" = "--fix" ]; then
            info "Installing hexstrike dependencies..."
            .venv/bin/pip install -q requests 2>/dev/null && fix "Installed requests"
        fi
    fi
fi

# ── 2. Metasploit MCP: check msfrpcd availability ──────────────
info "Checking Metasploit MCP server..."

if command -v msfrpcd >/dev/null 2>&1; then
    ok "msfrpcd binary found"

    MSFRPC_PORT="${MSFRPC_PORT:-55553}"
    PORT_OPEN=false

    if command -v ss >/dev/null 2>&1; then
        ss -tlnp 2>/dev/null | grep -q ":${MSFRPC_PORT}" && PORT_OPEN=true
    elif command -v netstat >/dev/null 2>&1; then
        netstat -tlnp 2>/dev/null | grep -q ":${MSFRPC_PORT}" && PORT_OPEN=true
    fi

    if [ "$PORT_OPEN" = "true" ]; then
        ok "msfrpcd is listening on port ${MSFRPC_PORT}"
    else
        warn "msfrpcd is NOT listening on port ${MSFRPC_PORT}"
        if [ "$FIX_MODE" = "--fix" ]; then
            info "Starting msfrpcd..."
            MSFRPC_USER="${MSFRPC_USER:-msf}"
            MSFRPC_PASS="${MSFRPC_PASS:-msf}"
            msfrpcd -U "$MSFRPC_USER" -P "$MSFRPC_PASS" \
                -p "$MSFRPC_PORT" -a 127.0.0.1 &
            fix "msfrpcd start command issued (PID $!) — may take 30-90s to be ready"
        fi
    fi
else
    warn "metasploit-framework is not installed (msfrpcd not found)"
    info "  Install: apt-get install -y metasploit-framework"
    info "  Or use Docker: docker compose up metasploit-mcp"
fi

# Check Python dependencies for metasploit MCP
if [ -f ".venv/bin/python3" ]; then
    if .venv/bin/python3 -c "import msgpack, httpx, mcp" 2>/dev/null; then
        ok "Metasploit MCP Python dependencies available"
    else
        warn "Metasploit MCP Python dependencies missing (msgpack, httpx)"
        if [ "$FIX_MODE" = "--fix" ]; then
            .venv/bin/pip install -q -r metasploit-mcp/requirements.txt 2>/dev/null && \
                fix "Installed metasploit-mcp Python dependencies"
        fi
    fi
fi

# ── 3. blhackbox core MCP: check entry point ───────────────────
info "Checking blhackbox core MCP server..."

if [ -f ".venv/bin/blhackbox" ]; then
    ok "blhackbox entry point exists"
else
    warn "blhackbox entry point not found (.venv/bin/blhackbox)"
    if [ "$FIX_MODE" = "--fix" ]; then
        info "Installing blhackbox package..."
        .venv/bin/pip install -e . --quiet 2>/dev/null && fix "blhackbox package installed"
    fi
fi

# ── 4. Container diagnostics tools ─────────────────────────────
info "Checking diagnostic tools..."

MISSING_TOOLS=()
for tool in ss ps; do
    if ! command -v "$tool" >/dev/null 2>&1; then
        MISSING_TOOLS+=("$tool")
    fi
done

if [ ${#MISSING_TOOLS[@]} -eq 0 ]; then
    ok "Diagnostic tools (ss, ps) available"
else
    warn "Missing diagnostic tools: ${MISSING_TOOLS[*]}"
    if [ "$FIX_MODE" = "--fix" ]; then
        info "Installing iproute2 and procps..."
        apt-get update -qq 2>/dev/null && \
            apt-get install -y -qq iproute2 procps 2>/dev/null && \
            fix "Installed iproute2 and procps"
    fi
fi

# ── Summary ─────────────────────────────────────────────────────
echo ""
echo "━━━ MCP Health Check Summary ━━━"
if [ $ISSUES -eq 0 ]; then
    echo "All checks passed."
elif [ "$FIX_MODE" = "--fix" ]; then
    echo "Issues found: $ISSUES, Fixed: $FIXED, Remaining: $((ISSUES - FIXED))"
else
    echo "Issues found: $ISSUES (run with --fix to attempt auto-repair)"
fi
exit $ISSUES
