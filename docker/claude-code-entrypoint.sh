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

echo -e "${BOLD}Checking service connectivity...${NC}"
echo -e "${DIM}Waiting for services to become healthy.${NC}"
echo ""

MCP_OK=0
MCP_FAIL=0
REST_OK=0
REST_FAIL=0

# -- MCP Servers (Claude Code connects via SSE) --
echo -e "  ${BOLD}MCP Servers${NC}"
if wait_for_service "Kali MCP" "http://kali-mcp:9001/sse"; then
    MCP_OK=$((MCP_OK + 1))
else
    MCP_FAIL=$((MCP_FAIL + 1))
fi

if wait_for_service "Ollama Pipeline" "http://ollama-mcp:9000/sse"; then
    MCP_OK=$((MCP_OK + 1))
else
    MCP_FAIL=$((MCP_FAIL + 1))
fi

echo ""

# -- REST API Services (accessible via HTTP, not MCP) --
echo -e "  ${BOLD}REST API Services${NC}"
if wait_for_service "HexStrike API" "http://hexstrike:8888/health"; then
    REST_OK=$((REST_OK + 1))
else
    REST_FAIL=$((REST_FAIL + 1))
fi

# Summary
echo ""
echo -e "${DIM}──────────────────────────────────────────────────${NC}"

TOTAL_OK=$((MCP_OK + REST_OK))
TOTAL_FAIL=$((MCP_FAIL + REST_FAIL))

if [ "$TOTAL_FAIL" -eq 0 ]; then
    echo -e "${GREEN}${BOLD}  All $TOTAL_OK services connected.${NC}"
else
    echo -e "${YELLOW}${BOLD}  $TOTAL_OK/$((TOTAL_OK + TOTAL_FAIL)) services connected. $TOTAL_FAIL unreachable.${NC}"
    echo -e "${DIM}  Claude Code will start — unreachable MCP servers show as 'failed' in /mcp.${NC}"
    echo -e "${DIM}  Use 'docker compose ps' in another terminal to check container health.${NC}"
fi

echo ""
echo -e "${DIM}──────────────────────────────────────────────────${NC}"
echo -e "  ${BOLD}MCP servers (connected via SSE):${NC}"
echo -e "    kali            ${DIM}Kali Linux security tools (nmap, nikto, ...)${NC}"
echo -e "    ollama-pipeline ${DIM}Ollama preprocessing (3-agent pipeline)${NC}"
echo ""
echo -e "  ${BOLD}REST API (accessible via HTTP):${NC}"
echo -e "    hexstrike       ${DIM}HexStrike AI (150+ tools, 12+ agents)${NC}"
echo -e "                    ${DIM}http://hexstrike:8888/api/...${NC}"
echo ""
echo -e "  ${BOLD}Quick start:${NC}"
echo -e "    ${CYAN}/mcp${NC}              ${DIM}Check MCP server status${NC}"
echo -e "    ${CYAN}Scan example.com for open ports and web vulnerabilities${NC}"
echo -e "${DIM}──────────────────────────────────────────────────${NC}"
echo ""

exec claude "$@"
