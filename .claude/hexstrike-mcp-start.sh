#!/bin/bash
set -euo pipefail

# HexStrike MCP Server startup script for local/Claude Code Web environments.
# Ensures the git submodule is initialized and dependencies are available
# before starting the MCP server with stdio transport.

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

HEXSTRIKE_URL="${HEXSTRIKE_URL:-http://localhost:8888}"

# ── Pre-flight: check submodule ────────────────────────────────
if [ ! -f "hexstrike/hexstrike_mcp.py" ]; then
    echo "[!] hexstrike/hexstrike_mcp.py not found — initializing git submodule..." >&2
    git submodule init 2>/dev/null || true
    git submodule update --depth 1 2>/dev/null || true

    if [ ! -f "hexstrike/hexstrike_mcp.py" ]; then
        echo "[!] FATAL: hexstrike submodule could not be initialized." >&2
        echo "[!] Clone manually: git submodule update --init hexstrike" >&2
        exit 1
    fi
    echo "[+] hexstrike submodule initialized." >&2
fi

# ── Pre-flight: check backend availability ─────────────────────
if command -v curl >/dev/null 2>&1; then
    if curl -sf --connect-timeout 2 "${HEXSTRIKE_URL}/health" >/dev/null 2>&1; then
        echo "[+] HexStrike backend reachable at ${HEXSTRIKE_URL}" >&2
    else
        echo "[!] HexStrike backend NOT reachable at ${HEXSTRIKE_URL}" >&2
        echo "[!] Tools will fail until the HexStrike server is started." >&2
        echo "[!] Start it with: docker compose up hexstrike" >&2
    fi
fi

# ── Pre-flight: check dependencies ─────────────────────────────
if ! .venv/bin/python3 -c "import requests; from mcp.server.fastmcp import FastMCP" 2>/dev/null; then
    echo "[*] Installing hexstrike dependencies..." >&2
    .venv/bin/pip install -q requests 2>/dev/null || true
fi

exec .venv/bin/python3 hexstrike/hexstrike_mcp.py
