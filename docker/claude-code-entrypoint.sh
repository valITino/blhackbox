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
export no_proxy="${no_proxy:+${no_proxy},}mcp-gateway,kali-mcp,wire-mcp,screenshot-mcp,localhost,127.0.0.1"
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
    local timeout="${3:-3}"
    curl -s --max-time "$timeout" -o /dev/null "$url" 2>/dev/null
    local rc=$?
    # Exit code 28 = curl connected but the transfer timed out. This is
    # expected for SSE/streaming endpoints (like /sse) that keep the
    # connection open indefinitely.  Treat it the same as 0 (success):
    # the server is up and responding.
    [ "$rc" -eq 0 ] || [ "$rc" -eq 28 ]
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

# WireMCP shares kali-mcp's network namespace, so use kali-mcp hostname
if wait_for_service "WireMCP" "http://kali-mcp:9003/sse"; then
    MCP_OK=$((MCP_OK + 1))
else
    MCP_FAIL=$((MCP_FAIL + 1))
fi

if wait_for_service "Screenshot MCP" "http://screenshot-mcp:9004/sse"; then
    MCP_OK=$((MCP_OK + 1))
else
    MCP_FAIL=$((MCP_FAIL + 1))
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
echo -e "    kali            ${DIM}Kali Linux security tools + Metasploit (70+ tools)${NC}"
echo -e "    wireshark       ${DIM}WireMCP — tshark packet capture & analysis${NC}"
echo -e "    screenshot      ${DIM}Screenshot MCP — headless Chromium evidence capture${NC}"
echo ""
echo -e "  ${BOLD}Data aggregation:${NC}"
echo -e "    ${DIM}You (Claude) handle parsing, deduplication, and synthesis directly.${NC}"
echo -e "    ${DIM}Use get_payload_schema + aggregate_results to validate & persist.${NC}"
echo ""
echo -e "  ${BOLD}Prompt templates (autonomous pentesting):${NC}"
echo -e "    ${CYAN}full-pentest${NC}       ${DIM}Complete end-to-end penetration test${NC}"
echo -e "    ${CYAN}full-attack-chain${NC}  ${DIM}Recon through exploitation with reporting${NC}"
echo -e "    ${CYAN}quick-scan${NC}         ${DIM}Fast high-level security scan${NC}"
echo -e "    ${CYAN}recon-deep${NC}         ${DIM}Comprehensive reconnaissance${NC}"
echo -e "    ${CYAN}web-app-assessment${NC} ${DIM}Web application security testing${NC}"
echo -e "    ${CYAN}network-infra${NC}      ${DIM}Network infrastructure assessment${NC}"
echo -e "    ${CYAN}vuln-assessment${NC}    ${DIM}Vulnerability identification${NC}"
echo -e "    ${CYAN}api-security${NC}       ${DIM}API security testing (OWASP API Top 10)${NC}"
echo -e "    ${CYAN}bug-bounty${NC}         ${DIM}Bug bounty hunting workflow${NC}"
echo -e "    ${CYAN}osint-gathering${NC}    ${DIM}Passive OSINT intelligence collection${NC}"
echo ""
echo -e "  ${BOLD}Output files${NC} ${DIM}(mounted to host ./output/)${NC}${BOLD}:${NC}"
echo -e "    ${DIM}/root/reports/       → ./output/reports/      pentest reports${NC}"
echo -e "    ${DIM}/tmp/screenshots/    → ./output/screenshots/  PoC evidence${NC}"
echo -e "    ${DIM}/root/results/       → ./output/sessions/     session JSONs${NC}"
echo ""
echo -e "  ${BOLD}Quick start:${NC}"
echo -e "    ${CYAN}/mcp${NC}              ${DIM}Check MCP server status${NC}"
echo -e "    ${CYAN}Use the full-pentest template against example.com${NC}"
echo -e "    ${CYAN}Scan example.com for open ports and web vulnerabilities${NC}"
echo -e "${DIM}──────────────────────────────────────────────────${NC}"
echo ""

exec claude "$@"
