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
export no_proxy="${no_proxy:+${no_proxy},}mcp-gateway,kali-mcp,wire-mcp,screenshot-mcp,hexstrike-ai,hexstrike-bridge-mcp,boaz-mcp,localhost,127.0.0.1"
export NO_PROXY="$no_proxy"

# ── Functions ───────────────────────────────────────────────────────

print_banner() {
    echo ""
    echo -e "${CYAN}${BOLD}  ╔══════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}${BOLD}  ║       blhackbox v2.0 — DeepSeek (Reasonix)  ║${NC}"
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
    # A bare GET to the Streamable HTTP endpoint (/mcp) returns an HTTP 4xx
    # (no MCP session/headers) — curl still exits 0 because it received a
    # response, which confirms the server is up. Exit code 28 (transfer
    # timed out) is also treated as success for any endpoint that streams.
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

# ── Output directory symlinks ──────────────────────────────────────
# Report/session paths resolve to /root/output/* (WORKDIR is /root).
# Bind mounts are at /root/reports, /root/results, /tmp/screenshots.
# Create symlinks so both path conventions reach the bind mounts.
mkdir -p /root/output
ln -sfn /root/reports       /root/output/reports
ln -sfn /root/results       /root/output/sessions
ln -sfn /tmp/screenshots    /root/output/screenshots

# ── Main ────────────────────────────────────────────────────────────

print_banner

# DeepSeek API key is required for Reasonix to authenticate against the
# DeepSeek API. It is read from the environment (reasonix.toml api_key_env).
if [ -z "${DEEPSEEK_API_KEY:-}" ]; then
    echo -e "  ${WARN} DEEPSEEK_API_KEY is not set — Reasonix cannot authenticate."
    echo -e "  ${DIM}Add it to .env and re-run, or pass -e DEEPSEEK_API_KEY=sk-...${NC}"
    echo -e "  ${DIM}Get a key at https://platform.deepseek.com/api_keys${NC}"
    echo ""
fi

echo -e "${BOLD}Checking service connectivity...${NC}"
echo -e "${DIM}Waiting for services to become healthy.${NC}"
echo ""

MCP_OK=0
MCP_FAIL=0

# -- MCP Servers (Reasonix connects via Streamable HTTP) --
echo -e "  ${BOLD}MCP Servers${NC}"
if wait_for_service "Kali MCP" "http://kali-mcp:9001/mcp"; then
    MCP_OK=$((MCP_OK + 1))
else
    MCP_FAIL=$((MCP_FAIL + 1))
fi

# WireMCP shares kali-mcp's network namespace, so use kali-mcp hostname
if wait_for_service "WireMCP" "http://kali-mcp:9003/mcp"; then
    MCP_OK=$((MCP_OK + 1))
else
    MCP_FAIL=$((MCP_FAIL + 1))
fi

if wait_for_service "Screenshot MCP" "http://screenshot-mcp:9004/mcp"; then
    MCP_OK=$((MCP_OK + 1))
else
    MCP_FAIL=$((MCP_FAIL + 1))
fi

if wait_for_service "BOAZ MCP" "http://boaz-mcp:9005/mcp"; then
    MCP_OK=$((MCP_OK + 1))
else
    MCP_FAIL=$((MCP_FAIL + 1))
fi

if wait_for_service "HexStrike MCP" "http://hexstrike-bridge-mcp:9006/mcp"; then
    MCP_OK=$((MCP_OK + 1))
else
    MCP_FAIL=$((MCP_FAIL + 1))
fi

# Summary
echo ""
echo -e "${DIM}──────────────────────────────────────────────────${NC}"

if [ "$MCP_FAIL" -eq 0 ]; then
    echo -e "${GREEN}${BOLD}  All $MCP_OK MCP servers connected.${NC}"
else
    echo -e "${YELLOW}${BOLD}  $MCP_OK/$((MCP_OK + MCP_FAIL)) MCP servers connected. $MCP_FAIL unreachable.${NC}"
    echo -e "${DIM}  Reasonix will start — unreachable servers simply won't expose tools.${NC}"
    echo -e "${DIM}  Use 'docker compose ps' in another terminal to check container health.${NC}"
fi

echo ""
echo -e "${DIM}──────────────────────────────────────────────────${NC}"
echo -e "  ${BOLD}MCP servers (connected via Streamable HTTP):${NC}"
echo -e "    kali            ${DIM}Kali Linux security tools + Metasploit (70+ tools)${NC}"
echo -e "    wireshark       ${DIM}WireMCP — tshark packet capture & analysis${NC}"
echo -e "    screenshot      ${DIM}Screenshot MCP — headless Chromium evidence capture${NC}"
echo -e "    boaz           ${DIM}BOAZ-MCP Gamma — agentic offensive security tools${NC}"
echo -e "    hexstrike      ${DIM}HexStrike Gamma — AI security automation tools${NC}"
echo ""
echo -e "  ${BOLD}Model:${NC} ${DIM}DeepSeek-V4-Flash (default). Type ${NC}${CYAN}/pro${NC}${DIM} for one Pro turn,${NC}"
echo -e "         ${DIM}or ${NC}${CYAN}/preset max${NC}${DIM} to use Pro for the whole session.${NC}"
echo ""
echo -e "  ${BOLD}Methodology:${NC} ${DIM}Pentest workflow and rules are in ${NC}${CYAN}/root/CLAUDE.md${NC}${DIM}.${NC}"
echo -e "  ${DIM}Describe your authorized target and goal; Reasonix will call the MCP tools.${NC}"
echo ""
echo -e "  ${BOLD}Output files${NC} ${DIM}(mounted to host ./output/)${NC}${BOLD}:${NC}"
echo -e "    ${DIM}output/reports/      → ./output/reports/      pentest reports${NC}"
echo -e "    ${DIM}output/screenshots/  → ./output/screenshots/  PoC evidence (read-only)${NC}"
echo -e "    ${DIM}output/sessions/     → ./output/sessions/     session data${NC}"
echo -e "    ${DIM}/root/kali-data/     ← shared Kali MCP recon artifacts (read-only)${NC}"
echo -e "${DIM}──────────────────────────────────────────────────${NC}"
echo ""

# Launch the Reasonix coding agent. `reasonix code` opens the interactive TUI;
# any args passed to the container are forwarded.
exec reasonix code "$@"
