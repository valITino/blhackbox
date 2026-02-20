#!/bin/bash
set -euo pipefail

# ── Colors ──────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
DIM='\033[2m'
NC='\033[0m' # No Color

# ── Symbols ─────────────────────────────────────────────────────────
CHECK="${GREEN}OK${NC}"
CROSS="${RED}FAIL${NC}"
WARN="${YELLOW}WARN${NC}"
WAIT="${DIM}....${NC}"

# ── Configuration ───────────────────────────────────────────────────
MAX_RETRIES=20
RETRY_INTERVAL=3

# Ensure internal Docker hostnames bypass any egress proxy.
export no_proxy="${no_proxy:+${no_proxy},}mcp-gateway,kali-mcp,hexstrike,ollama-mcp,ollama,agent-ingestion,agent-processing,agent-synthesis,localhost,127.0.0.1"
export NO_PROXY="$no_proxy"

# ── Functions ───────────────────────────────────────────────────────

print_banner() {
    echo ""
    echo -e "${CYAN}${BOLD}  ╔══════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}${BOLD}  ║          blhackbox v2.0 — Claude Code       ║${NC}"
    echo -e "${CYAN}${BOLD}  ║        MCP-based Pentesting Framework       ║${NC}"
    echo -e "${CYAN}${BOLD}  ╚══════════════════════════════════════════════╝${NC}"
    echo ""
}

# Check a single service. Returns 0 on success, 1 on failure.
check_service() {
    local name="$1"
    local url="$2"
    local timeout="${3:-5}"
    curl -sf --max-time "$timeout" "$url" > /dev/null 2>&1
}

# Wait for a service with retries. Prints status.
wait_for_service() {
    local name="$1"
    local url="$2"
    local retries="${3:-$MAX_RETRIES}"

    printf "  %-22s " "$name"

    for i in $(seq 1 "$retries"); do
        if check_service "$name" "$url"; then
            echo -e "[ ${CHECK} ]"
            return 0
        fi
        sleep "$RETRY_INTERVAL"
    done

    echo -e "[ ${CROSS} ]  (unreachable at $url)"
    return 1
}

# ── Main ────────────────────────────────────────────────────────────

print_banner

echo -e "${BOLD}Checking MCP server connectivity...${NC}"
echo -e "${DIM}Each server must be healthy before Claude Code can use it.${NC}"
echo ""

FAILED=0
SERVICES_OK=0

# Check each MCP server individually
if wait_for_service "Kali MCP" "http://kali-mcp:9001/sse"; then
    SERVICES_OK=$((SERVICES_OK + 1))
else
    FAILED=$((FAILED + 1))
fi

if wait_for_service "HexStrike MCP" "http://hexstrike:8888/health"; then
    SERVICES_OK=$((SERVICES_OK + 1))
else
    FAILED=$((FAILED + 1))
fi

if wait_for_service "Ollama Pipeline" "http://ollama-mcp:9000/sse"; then
    SERVICES_OK=$((SERVICES_OK + 1))
else
    FAILED=$((FAILED + 1))
fi

# Summary
echo ""
echo -e "${DIM}──────────────────────────────────────────────────${NC}"

if [ "$FAILED" -eq 0 ]; then
    echo -e "${GREEN}${BOLD}  All $SERVICES_OK MCP servers connected.${NC}"
else
    echo -e "${YELLOW}${BOLD}  $SERVICES_OK/$((SERVICES_OK + FAILED)) MCP servers connected. $FAILED unreachable.${NC}"
    echo -e "${DIM}  Claude Code will start — unreachable servers show as 'failed' in /mcp.${NC}"
    echo -e "${DIM}  Use 'docker compose ps' in another terminal to check container health.${NC}"
fi

echo ""
echo -e "${DIM}──────────────────────────────────────────────────${NC}"
echo -e "  ${BOLD}MCP servers configured:${NC}"
echo -e "    kali            ${DIM}Kali Linux security tools (nmap, nikto, ...)${NC}"
echo -e "    hexstrike       ${DIM}HexStrike AI (150+ tools, 12+ agents)${NC}"
echo -e "    ollama-pipeline ${DIM}Ollama preprocessing (3-agent pipeline)${NC}"
echo ""
echo -e "  ${BOLD}Quick start:${NC}"
echo -e "    ${CYAN}/mcp${NC}              ${DIM}Check MCP server status${NC}"
echo -e "    ${CYAN}Run a full recon on example.com --authorized${NC}"
echo -e "${DIM}──────────────────────────────────────────────────${NC}"
echo ""

exec claude "$@"
