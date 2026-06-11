#!/usr/bin/env bash
# ── blhackbox v2.0 — Interactive Setup Wizard ────────────────────────
# One-command setup: checks prerequisites, generates .env, pulls images,
# starts services, and verifies health.
#
# Usage:
#   ./setup.sh                      # Interactive mode
#   ./setup.sh --api-key sk-ant-... # Non-interactive with API key
#   ./setup.sh --minimal            # Skip optional profiles
#   ./setup.sh --help               # Show usage
set -euo pipefail

# ── Colors & Symbols ─────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
DIM='\033[2m'
NC='\033[0m'
CHECK="${GREEN}✔${NC}"
CROSS="${RED}✘${NC}"
WARN="${YELLOW}!${NC}"
ARROW="${CYAN}→${NC}"

# ── Globals ──────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
API_KEY=""
DEEPSEEK_KEY=""
MINIMAL=false
SKIP_PULL=false
NEO4J_PASS=""
PROFILES=""

# ── Functions ────────────────────────────────────────────────────────

print_banner() {
    echo ""
    echo -e "${CYAN}${BOLD}  ╔══════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}${BOLD}  ║       blhackbox v2.0 — Setup Wizard        ║${NC}"
    echo -e "${CYAN}${BOLD}  ║      MCP-based Pentesting Framework        ║${NC}"
    echo -e "${CYAN}${BOLD}  ╚══════════════════════════════════════════════╝${NC}"
    echo ""
}

usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --api-key KEY      Set ANTHROPIC_API_KEY for the Claude Code container"
    echo "  --deepseek-key KEY Set DEEPSEEK_API_KEY for the DeepSeek (Reasonix) container"
    echo "  --minimal         Core stack only (no Neo4j)"
    echo "  --with-neo4j      Enable Neo4j knowledge graph"
    echo "  --with-gateway    Enable MCP Gateway for Claude Desktop/ChatGPT"
    echo "  --skip-pull       Skip docker compose pull (use cached images)"
    echo "  --help            Show this help"
    echo ""
    exit 0
}

# Check if a command exists
require_cmd() {
    if ! command -v "$1" &>/dev/null; then
        echo -e "  ${CROSS} ${BOLD}$1${NC} is not installed."
        echo -e "    ${ARROW} $2"
        return 1
    fi
    return 0
}

# Compare semver: returns 0 if $1 >= $2
version_gte() {
    printf '%s\n%s' "$2" "$1" | sort -V -C
}

check_prerequisites() {
    echo -e "${BOLD}Checking prerequisites...${NC}"
    echo ""
    local ok=true

    # Docker
    if require_cmd docker "Install: https://docs.docker.com/get-docker/"; then
        local docker_ver
        docker_ver=$(docker version --format '{{.Server.Version}}' 2>/dev/null || echo "0.0.0")
        if version_gte "$docker_ver" "24.0.0"; then
            echo -e "  ${CHECK} Docker ${DIM}v${docker_ver}${NC}"
        else
            echo -e "  ${WARN} Docker v${docker_ver} — recommend v24.0+ for BuildKit support"
        fi
    else
        ok=false
    fi

    # Docker Compose (v2 plugin)
    if docker compose version &>/dev/null; then
        local compose_ver
        compose_ver=$(docker compose version --short 2>/dev/null | sed 's/^v//')
        if version_gte "$compose_ver" "2.20.0"; then
            echo -e "  ${CHECK} Docker Compose ${DIM}v${compose_ver}${NC}"
        else
            echo -e "  ${WARN} Docker Compose v${compose_ver} — recommend v2.20+"
        fi
    else
        echo -e "  ${CROSS} ${BOLD}docker compose${NC} not available."
        echo -e "    ${ARROW} Install Docker Compose v2: https://docs.docker.com/compose/install/"
        ok=false
    fi

    # Git
    if require_cmd git "Install: https://git-scm.com/downloads"; then
        local git_ver
        git_ver=$(git --version | awk '{print $3}')
        echo -e "  ${CHECK} Git ${DIM}v${git_ver}${NC}"
    fi

    # Disk space check (need ~5GB for images)
    local avail_gb
    avail_gb=$(df -BG "$SCRIPT_DIR" | awk 'NR==2 {print $4}' | tr -d 'G')
    if [ "$avail_gb" -lt 5 ]; then
        echo -e "  ${WARN} Only ${avail_gb}GB disk space available (recommend 5GB+)"
    else
        echo -e "  ${CHECK} Disk space ${DIM}${avail_gb}GB available${NC}"
    fi

    echo ""
    if [ "$ok" = false ]; then
        echo -e "${RED}${BOLD}Prerequisites missing. Install the required tools and re-run.${NC}"
        exit 1
    fi
}

configure_env() {
    echo -e "${BOLD}Configuring environment...${NC}"
    echo ""

    # If .env already exists, ask before overwriting
    if [ -f "$SCRIPT_DIR/.env" ]; then
        echo -e "  ${WARN} ${BOLD}.env${NC} already exists."
        read -rp "  Overwrite with fresh config? [y/N] " overwrite
        if [[ ! "$overwrite" =~ ^[Yy] ]]; then
            echo -e "  ${ARROW} Keeping existing .env"
            echo ""
            return
        fi
    fi

    # Start from template
    cp "$SCRIPT_DIR/.env.example" "$SCRIPT_DIR/.env"

    # --- ANTHROPIC_API_KEY ---
    if [ -z "$API_KEY" ]; then
        echo -e "  ${BOLD}ANTHROPIC_API_KEY${NC} ${DIM}(required for Claude Code in Docker)${NC}"
        echo -e "  ${DIM}Get yours at: https://console.anthropic.com/settings/keys${NC}"
        echo -e "  ${DIM}Press Enter to skip if you'll only use Claude Code on host.${NC}"
        read -rsp "  API Key: " API_KEY
        echo ""
    fi

    if [ -n "$API_KEY" ]; then
        # Replace the commented-out line with the actual key
        sed -i "s|^# ANTHROPIC_API_KEY=sk-ant-.*|ANTHROPIC_API_KEY=${API_KEY}|" "$SCRIPT_DIR/.env"
        echo -e "  ${CHECK} ANTHROPIC_API_KEY configured"
    else
        echo -e "  ${WARN} ANTHROPIC_API_KEY skipped — Claude Code Docker won't start without it"
    fi

    # --- DEEPSEEK_API_KEY (for the DeepSeek / Reasonix container) ---
    if [ -z "$DEEPSEEK_KEY" ]; then
        echo ""
        echo -e "  ${BOLD}DEEPSEEK_API_KEY${NC} ${DIM}(for the DeepSeek/Reasonix agent in Docker)${NC}"
        echo -e "  ${DIM}Get yours at: https://platform.deepseek.com/api_keys${NC}"
        echo -e "  ${DIM}Press Enter to skip if you won't use the DeepSeek agent.${NC}"
        read -rsp "  API Key: " DEEPSEEK_KEY
        echo ""
    fi

    if [ -n "$DEEPSEEK_KEY" ]; then
        sed -i "s|^# DEEPSEEK_API_KEY=sk-.*|DEEPSEEK_API_KEY=${DEEPSEEK_KEY}|" "$SCRIPT_DIR/.env"
        echo -e "  ${CHECK} DEEPSEEK_API_KEY configured"
    else
        echo -e "  ${WARN} DEEPSEEK_API_KEY skipped — the DeepSeek agent won't start without it"
    fi

    # --- NEO4J_PASSWORD ---
    if [[ "$PROFILES" == *"neo4j"* ]]; then
        if [ -z "$NEO4J_PASS" ]; then
            echo ""
            echo -e "  ${BOLD}NEO4J_PASSWORD${NC} ${DIM}(min 8 chars for Neo4j)${NC}"
            read -rp "  Password [changeme-min-8-chars]: " NEO4J_PASS
            NEO4J_PASS="${NEO4J_PASS:-changeme-min-8-chars}"
        fi
        sed -i "s|^NEO4J_PASSWORD=.*|NEO4J_PASSWORD=${NEO4J_PASS}|" "$SCRIPT_DIR/.env"
        echo -e "  ${CHECK} NEO4J_PASSWORD configured"
    fi

    # --- Keys & tokens reference ---
    # Print the full list of keys/tokens the framework can use so the user
    # knows exactly what to provide. Only ANTHROPIC_API_KEY (Docker client) is
    # ever required; every pentest tool runs without the rest — they only widen
    # passive recon coverage and extra data sources.
    echo ""
    echo -e "  ${BOLD}Keys & tokens${NC} ${DIM}(edit .env to add them, then restart the stack):${NC}"
    echo ""
    echo -e "    ${BOLD}Agent keys (set the one for the in-Docker agent you run)${NC}"
    echo -e "      ${CYAN}ANTHROPIC_API_KEY${NC}      ${DIM}Claude Code container (--profile claude-code).${NC}"
    echo -e "                             ${DIM}Not needed for Claude Code Web/host.${NC}"
    echo -e "                             ${DIM}→ https://console.anthropic.com/settings/keys${NC}"
    echo -e "      ${CYAN}DEEPSEEK_API_KEY${NC}       ${DIM}DeepSeek (Reasonix) container (--profile deepseek).${NC}"
    echo -e "                             ${DIM}→ https://platform.deepseek.com/api_keys${NC}"
    echo ""
    echo -e "    ${BOLD}Optional — widen recon (all tools work without them)${NC}"
    echo -e "      ${CYAN}WPSCAN_API_TOKEN${NC}       ${DIM}WordPress vuln database; wpscan auto-reads it.${NC}"
    echo -e "                             ${DIM}→ https://wpscan.com/api  (free: 25 req/day)${NC}"
    echo -e "      ${CYAN}SHODAN_API_KEY${NC}         ${DIM}subfinder passive source + Shodan host data.${NC}"
    echo -e "                             ${DIM}→ https://account.shodan.io${NC}"
    echo -e "      ${CYAN}VIRUSTOTAL_API_KEY${NC}     ${DIM}subfinder passive source.${NC}"
    echo -e "                             ${DIM}→ https://www.virustotal.com/gui/my-apikey${NC}"
    echo -e "      ${CYAN}SECURITYTRAILS_API_KEY${NC} ${DIM}subfinder passive source (subdomains/history).${NC}"
    echo -e "                             ${DIM}→ https://securitytrails.com/app/account/credentials${NC}"
    echo -e "      ${CYAN}OPENAI_API_KEY${NC}         ${DIM}Only for ChatGPT/OpenAI MCP clients (host-based).${NC}"
    echo -e "                             ${DIM}→ https://platform.openai.com/api-keys${NC}"
    echo ""
    echo -e "    ${DIM}theHarvester and amass read keys from their OWN config files, not${NC}"
    echo -e "    ${DIM}env vars: ~/.theHarvester/api-keys.yaml and ~/.config/amass/datasources.yaml${NC}"

    echo ""
}

select_profiles() {
    if [ "$MINIMAL" = true ]; then
        PROFILES=""
        echo -e "  ${ARROW} Minimal mode: core stack only (4 containers)"
        echo ""
        return
    fi

    echo -e "${BOLD}Select optional components:${NC}"
    echo ""

    # Neo4j
    if [[ "$PROFILES" != *"neo4j"* ]]; then
        read -rp "  Enable Neo4j knowledge graph? [y/N] " yn
        if [[ "$yn" =~ ^[Yy] ]]; then
            PROFILES="${PROFILES:+$PROFILES }--profile neo4j"
        fi
    fi

    # Gateway
    if [[ "$PROFILES" != *"gateway"* ]]; then
        read -rp "  Enable MCP Gateway (for Claude Desktop/ChatGPT)? [y/N] " yn
        if [[ "$yn" =~ ^[Yy] ]]; then
            PROFILES="${PROFILES:+$PROFILES }--profile gateway"
        fi
    fi

    echo ""
}

create_output_dirs() {
    echo -e "${BOLD}Creating output directories...${NC}"
    mkdir -p "$SCRIPT_DIR/output/reports" \
             "$SCRIPT_DIR/output/screenshots" \
             "$SCRIPT_DIR/output/sessions"
    echo -e "  ${CHECK} output/reports/      ${DIM}← pentest reports (.md, .pdf)${NC}"
    echo -e "  ${CHECK} output/screenshots/  ${DIM}← PoC evidence captures${NC}"
    echo -e "  ${CHECK} output/sessions/     ${DIM}← aggregated session JSONs${NC}"
    echo ""
}

pull_images() {
    if [ "$SKIP_PULL" = true ]; then
        echo -e "  ${ARROW} Skipping image pull (--skip-pull)"
        echo ""
        return
    fi

    echo -e "${BOLD}Pulling Docker images...${NC}"
    echo -e "  ${DIM}This may take a few minutes on first run.${NC}"
    echo ""
    # shellcheck disable=SC2086
    docker compose $PROFILES pull 2>&1 | tail -5
    echo ""
    echo -e "  ${CHECK} Images pulled"
    echo ""
}

start_services() {
    echo -e "${BOLD}Starting services...${NC}"
    echo ""
    # shellcheck disable=SC2086
    docker compose $PROFILES up -d 2>&1 | tail -10
    echo ""
    echo -e "  ${CHECK} Services started"
    echo ""
}

wait_for_health() {
    echo -e "${BOLD}Waiting for services to become healthy...${NC}"
    echo -e "  ${DIM}Kali MCP takes 30-60s on first startup (Metasploit DB init).${NC}"
    echo ""

    local max_wait=90
    local interval=5
    local elapsed=0
    local all_healthy=false

    while [ $elapsed -lt $max_wait ]; do
        local healthy
        healthy=$(docker compose ps --format json 2>/dev/null | grep -c '"healthy"' || true)
        local total
        total=$(docker compose ps --format json 2>/dev/null | grep -c '"running\|healthy\|unhealthy"' || true)

        printf "\r  ${DIM}[%02d/%02ds]${NC} %d/%d services healthy..." "$elapsed" "$max_wait" "$healthy" "$total"

        # Check core services
        if docker compose ps kali-mcp 2>/dev/null | grep -q "healthy" && \
           docker compose ps screenshot-mcp 2>/dev/null | grep -q "healthy"; then
            all_healthy=true
            break
        fi

        sleep "$interval"
        elapsed=$((elapsed + interval))
    done

    echo ""
    echo ""

    if [ "$all_healthy" = true ]; then
        echo -e "  ${CHECK} ${GREEN}${BOLD}Core services are healthy!${NC}"
    else
        echo -e "  ${WARN} Some services may still be starting."
        echo -e "  ${DIM}Run 'make health' or 'docker compose ps' to check status.${NC}"
    fi
    echo ""
}

print_summary() {
    echo -e "${DIM}══════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}${BOLD}  Setup complete!${NC}"
    echo -e "${DIM}══════════════════════════════════════════════════${NC}"
    echo ""
    echo -e "  ${BOLD}Quick start:${NC}"
    echo -e "    ${CYAN}make claude-code${NC}    ${DIM}Launch Claude Code in Docker${NC}"
    echo -e "    ${CYAN}make deepseek${NC}       ${DIM}Launch the DeepSeek (Reasonix) agent in Docker${NC}"
    echo -e "    ${CYAN}make status${NC}         ${DIM}Check service status${NC}"
    echo -e "    ${CYAN}make health${NC}         ${DIM}Run health checks${NC}"
    echo -e "    ${CYAN}make logs${NC}           ${DIM}View service logs${NC}"
    echo ""
    echo -e "  ${BOLD}Output files${NC} (accessible on your host):"
    echo -e "    ${DIM}./output/reports/      Pentest reports (.md, .pdf)${NC}"
    echo -e "    ${DIM}./output/screenshots/  PoC evidence screenshots${NC}"
    echo -e "    ${DIM}./output/sessions/     Aggregated session data${NC}"
    echo ""
    echo -e "  ${BOLD}Portainer UI:${NC}"
    echo -e "    ${CYAN}https://localhost:9443${NC}"
    echo -e "    ${WARN} Create admin account within 5 minutes of first start!"
    echo ""
    if [[ "$PROFILES" == *"neo4j"* ]]; then
        echo -e "  ${BOLD}Neo4j Browser:${NC}  ${CYAN}http://localhost:7474${NC}"
    fi
    if [[ "$PROFILES" == *"gateway"* ]]; then
        echo -e "  ${BOLD}MCP Gateway:${NC}    ${CYAN}http://localhost:8080${NC}"
    fi
    echo -e "  ${BOLD}For pentesting:${NC}"
    echo -e "    Use a pentest template or skill: ${DIM}full-pentest, quick-scan, etc.${NC}"
    echo ""
    echo -e "  ${BOLD}Optional API keys${NC} ${DIM}(none required — all tools run without them):${NC}"
    echo -e "    Add keys to ${CYAN}.env${NC} to widen recon coverage, then restart the stack."
    echo -e "    ${DIM}WPSCAN_API_TOKEN (WordPress vulns), VIRUSTOTAL_API_KEY / SHODAN_API_KEY /${NC}"
    echo -e "    ${DIM}SECURITYTRAILS_API_KEY (subfinder sources). See README → Optional API keys.${NC}"
    echo ""
}

# ── Parse Arguments ──────────────────────────────────────────────────

while [[ $# -gt 0 ]]; do
    case "$1" in
        --api-key)
            API_KEY="$2"
            shift 2
            ;;
        --deepseek-key)
            DEEPSEEK_KEY="$2"
            shift 2
            ;;
        --minimal)
            MINIMAL=true
            shift
            ;;
        --with-neo4j)
            PROFILES="${PROFILES:+$PROFILES }--profile neo4j"
            shift
            ;;
        --with-gateway)
            PROFILES="${PROFILES:+$PROFILES }--profile gateway"
            shift
            ;;
        --skip-pull)
            SKIP_PULL=true
            shift
            ;;
        --help|-h)
            usage
            ;;
        *)
            echo "Unknown option: $1"
            usage
            ;;
    esac
done

# ── Main ─────────────────────────────────────────────────────────────

cd "$SCRIPT_DIR"

print_banner
check_prerequisites
select_profiles
configure_env
create_output_dirs
pull_images
start_services
wait_for_health
print_summary
