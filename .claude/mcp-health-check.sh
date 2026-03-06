#!/bin/bash
# MCP Server Health Check — validates all configured MCP server backends
# before or after startup. Designed to surface issues early rather than
# letting them silently fail during tool calls.
#
# Usage: .claude/mcp-health-check.sh [--fix]
#   --fix: Attempt to automatically fix issues (start services, install deps)

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

# ── 1. blhackbox core MCP: check entry point ───────────────────
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

# ── 2. Container diagnostics tools ─────────────────────────────
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
