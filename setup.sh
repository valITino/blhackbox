#!/usr/bin/env bash
# ── blhackbox v2.0 — Interactive Setup Wizard ────────────────────────
# Professional, guided setup: checks prerequisites, lets you pick your AI
# client, optional knowledge graph (local Neo4j or Aura cloud), and API
# keys (with step-by-step help for each), then pulls images and starts
# services with LIVE progress and a live service-health dashboard.
#
# Usage:
#   ./setup.sh                      # Interactive wizard (recommended)
#   ./setup.sh --api-key sk-ant-... # Non-interactive: Claude Code container
#   ./setup.sh --deepseek-key sk-.. # Non-interactive: DeepSeek container
#   ./setup.sh --zai-key KEY        # Non-interactive: Z.ai / GLM 5.2 container
#   ./setup.sh --minimal            # Core stack only, no prompts
#   ./setup.sh --with-neo4j         # Enable local Neo4j (Docker)
#   ./setup.sh --with-gateway       # Enable MCP Gateway (Desktop/ChatGPT)
#   ./setup.sh --skip-pull          # Use cached images
#   ./setup.sh --help               # Show usage
set -euo pipefail

# ── Interactivity & color detection ──────────────────────────────────
# Prompt only when stdin is a terminal; emit cursor-redraw codes only when
# stdout is a terminal; colorize only when stdout is a TTY AND the NO_COLOR
# convention (https://no-color.org — any non-empty value disables color) is
# not set. This keeps piped/CI logs clean (no raw escape codes).
INTERACTIVE=true; [ -t 0 ] || INTERACTIVE=false
INTERACTIVE_OUT=true; [ -t 1 ] || INTERACTIVE_OUT=false
USE_COLOR=true
if [ "$INTERACTIVE_OUT" != true ] || [ -n "${NO_COLOR:-}" ]; then
    USE_COLOR=false
fi

# ── Colors & Symbols ─────────────────────────────────────────────────
if [ "$USE_COLOR" = true ]; then
    RED='\033[0;31m'
    GREEN='\033[0;32m'
    YELLOW='\033[1;33m'
    BLUE='\033[0;34m'
    CYAN='\033[0;36m'
    BOLD='\033[1m'
    DIM='\033[2m'
    NC='\033[0m'
else
    RED=''; GREEN=''; YELLOW=''; BLUE=''; CYAN=''; BOLD=''; DIM=''; NC=''
fi
CHECK="${GREEN}✔${NC}"
CROSS="${RED}✘${NC}"
WARN="${YELLOW}!${NC}"
ARROW="${CYAN}→${NC}"

# ── Globals ──────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
API_KEY=""
DEEPSEEK_KEY=""
ZAI_KEY=""
MINIMAL=false
SKIP_PULL=false
NEO4J_PASS=""
PROFILES=""

# Runtime selections (filled in by the wizard).
AI_VARIANT=""        # claude-code | claude-web | claude-desktop | chatgpt | deepseek | zai | ""
AGENT_PROFILE=""     # claude-code | deepseek | zai | ""  (containerized agents only)
NEO4J_MODE="none"    # none | local | aura
WRITE_ENV=true       # whether we may (over)write .env
STATUS_LINES=0       # bookkeeping for the live status redraw

# ── Generic helpers ──────────────────────────────────────────────────

# Render a clickable terminal hyperlink (OSC 8) when color/terminal support
# is on; otherwise print the bare text. Uses the BEL terminator (widely
# supported); terminals without OSC 8 simply show the text, so it's safe.
# $1 = URL, $2 = display text (defaults to the URL).
link() {
    local url="$1" text="${2:-$1}"
    if [ "$USE_COLOR" = true ]; then
        printf '\033]8;;%s\007%s\033]8;;\007' "$url" "$text"
    else
        printf '%s' "$text"
    fi
}

# Append a compose --profile flag once (no duplicates).
add_profile() {
    case " $PROFILES " in
        *" --profile $1 "*) ;;
        *) PROFILES="${PROFILES:+$PROFILES }--profile $1" ;;
    esac
}

# Yes/no prompt. $1 = question, $2 = default (y|n). Returns 0 for yes.
ask_yes_no() {
    local question="$1" def="${2:-n}" ans hint="[y/N]"
    [ "$def" = "y" ] && hint="[Y/n]"
    read -rp "  $question $hint " ans </dev/tty || true
    ans="${ans:-$def}"
    [[ "$ans" =~ ^[Yy] ]]
}

# Numeric menu reader. $1 = max option, $2 = default. Echoes the choice.
read_choice() {
    local max="$1" def="$2" ans
    read -rp "  Enter choice [${def}]: " ans </dev/tty || true
    ans="${ans:-$def}"
    if ! [[ "$ans" =~ ^[0-9]+$ ]] || [ "$ans" -lt 1 ] || [ "$ans" -gt "$max" ]; then
        ans="$def"
    fi
    echo "$ans"
}

# Read a secret without echoing it. Prompt + newline go to stderr; the
# value is the only thing written to stdout (safe for command substitution).
# Never echo secret values back to the screen or logs.
prompt_secret() {
    local prompt="${1:-  Paste value (input hidden), or press Enter to skip: }" val
    read -rsp "$prompt" val </dev/tty || true
    printf '\n' >&2
    printf '%s' "$val"
}

# Set KEY=VALUE in .env safely. The key is always a literal we control, so
# the value is NEVER passed through sed (no escaping pitfalls, injection-safe).
# Removes any prior definition (commented placeholder or active line), then
# appends the real value verbatim.
set_env() {
    local key="$1" val="$2" file="$SCRIPT_DIR/.env"
    sed -i -E "/^[[:space:]]*#?[[:space:]]*${key}=/d" "$file"
    printf '%s=%s\n' "$key" "$val" >> "$file"
}

# Return 0 if KEY is set to a non-empty value in .env.
env_has_value() {
    grep -qE "^$1=.+" "$SCRIPT_DIR/.env" 2>/dev/null
}

# Soft, non-blocking format check for a freshly entered API key. Returns 0
# to proceed with saving, 1 to treat as skipped. Never prints the value.
key_format_ok() {
    local var="$1" val="$2"
    case "$var" in
        ANTHROPIC_API_KEY)
            [[ "$val" == sk-ant-* ]] && return 0
            echo -e "    ${WARN} That doesn't look like an Anthropic key (expected prefix 'sk-ant-')." ;;
        DEEPSEEK_API_KEY|OPENAI_API_KEY)
            [[ "$val" == sk-* ]] && return 0
            echo -e "    ${WARN} That doesn't look like a typical API key (expected prefix 'sk-')." ;;
        *) return 0 ;;
    esac
    # Prefix didn't match — let the user decide (non-blocking).
    ask_yes_no "Save it anyway?" "y"
}

# ── Banner & usage ───────────────────────────────────────────────────

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
    echo "Interactive mode (no flags) walks you through: AI client, knowledge"
    echo "graph (local Neo4j or Aura cloud), and API keys — with guidance for"
    echo "each — then pulls images and starts services with live progress."
    echo ""
    echo "Options:"
    echo "  --api-key KEY      Set ANTHROPIC_API_KEY (Claude Code container)"
    echo "  --deepseek-key KEY Set DEEPSEEK_API_KEY (DeepSeek container)"
    echo "  --zai-key KEY      Set ZAI_API_KEY (Z.ai / GLM 5.2 container)"
    echo "  --minimal         Core stack only (no prompts, no Neo4j/Gateway)"
    echo "  --with-neo4j      Enable local Neo4j knowledge graph (Docker)"
    echo "  --with-gateway    Enable MCP Gateway for Claude Desktop/ChatGPT"
    echo "  --skip-pull       Skip docker compose pull (use cached images)"
    echo "  --help            Show this help"
    echo ""
    exit 0
}

# ── Prerequisites ────────────────────────────────────────────────────

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
    echo -e "${BOLD}Step 1/8 · Checking prerequisites${NC}"
    echo -e "${DIM}  Verifying Docker, Compose, Git, and disk space before we begin.${NC}"
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

# ── .env preparation ─────────────────────────────────────────────────

prepare_env() {
    echo -e "${BOLD}Step 2/8 · Preparing configuration (.env)${NC}"
    echo -e "${DIM}  Your keys and settings live in .env (git-ignored — never committed).${NC}"
    echo ""

    if [ -f "$SCRIPT_DIR/.env" ]; then
        if [ "$INTERACTIVE" = true ]; then
            echo -e "  ${WARN} ${BOLD}.env${NC} already exists."
            if ask_yes_no "Overwrite it with a fresh, guided configuration?" "n"; then
                cp "$SCRIPT_DIR/.env.example" "$SCRIPT_DIR/.env"
                echo -e "  ${CHECK} Started a fresh .env from the template"
            else
                WRITE_ENV=false
                echo -e "  ${ARROW} Keeping your existing .env (won't prompt for keys)"
            fi
        else
            WRITE_ENV=false
            echo -e "  ${ARROW} Existing .env kept (non-interactive run)"
        fi
    else
        cp "$SCRIPT_DIR/.env.example" "$SCRIPT_DIR/.env"
        echo -e "  ${CHECK} Created .env from the template"
    fi

    # Secrets live in .env — restrict it to the owner only.
    if chmod 600 "$SCRIPT_DIR/.env" 2>/dev/null; then
        echo -e "  ${CHECK} Locked .env to owner-only ${DIM}(chmod 600)${NC}"
    fi
    echo ""
}

# ── AI client selection ──────────────────────────────────────────────

print_anthropic_help() {
    echo -e "    ${BOLD}What it's for:${NC} authenticates the Claude Code agent running"
    echo -e "    inside Docker. ${DIM}Not needed for Claude Code Web or Claude Desktop.${NC}"
    echo -e "    ${BOLD}Where it's used:${NC} the ${CYAN}claude-code${NC} container (ANTHROPIC_API_KEY)."
    echo -e "    ${BOLD}How to get it:${NC}"
    echo -e "      ${DIM}1.${NC} Sign in at ${CYAN}https://console.anthropic.com${NC}"
    echo -e "      ${DIM}2.${NC} Add a payment method under ${BOLD}Billing${NC} (pay-as-you-go)"
    echo -e "      ${DIM}3.${NC} Open ${BOLD}Settings → API keys${NC} → ${BOLD}Create Key${NC}"
    echo -e "      ${DIM}4.${NC} Copy it now — Anthropic shows the key only once"
}

print_deepseek_help() {
    echo -e "    ${BOLD}What it's for:${NC} authenticates the DeepSeek agent (Claude Code + DeepSeek API) in Docker."
    echo -e "    ${BOLD}Where it's used:${NC} the ${CYAN}deepseek${NC} container (DEEPSEEK_API_KEY)."
    echo -e "    ${BOLD}How to get it:${NC}"
    echo -e "      ${DIM}1.${NC} Sign in at ${CYAN}https://platform.deepseek.com${NC}"
    echo -e "      ${DIM}2.${NC} Add balance under ${BOLD}Billing${NC} (the API needs a positive balance)"
    echo -e "      ${DIM}3.${NC} Open ${BOLD}API keys${NC} → ${BOLD}Create new API key${NC}"
    echo -e "      ${DIM}4.${NC} Copy it now — DeepSeek shows the key only once"
}

print_zai_help() {
    echo -e "    ${BOLD}What it's for:${NC} authenticates the Z.ai / GLM 5.2 agent (Claude Code + Z.ai API) in Docker."
    echo -e "    ${BOLD}Where it's used:${NC} the ${CYAN}zai${NC} container (ZAI_API_KEY)."
    echo -e "    ${BOLD}How to get it:${NC}"
    echo -e "      ${DIM}1.${NC} Sign in at ${CYAN}https://z.ai${NC} and subscribe to the GLM Coding Plan"
    echo -e "      ${DIM}2.${NC} Open ${BOLD}API Keys${NC} at ${CYAN}https://z.ai/manage-apikey/apikey-list${NC}"
    echo -e "      ${DIM}3.${NC} Click ${BOLD}Add New Key${NC} and copy it"
    echo -e "      ${DIM}4.${NC} Copy it now — Z.ai shows the key only once"
}

print_openai_help() {
    echo -e "    ${BOLD}What it's for:${NC} used by your host-based ChatGPT/OpenAI MCP client"
    echo -e "    ${DIM}(and optional vector-memory embeddings). The Docker stack itself does${NC}"
    echo -e "    ${DIM}not require it — store it here only for convenience.${NC}"
    echo -e "    ${BOLD}How to get it:${NC}"
    echo -e "      ${DIM}1.${NC} Sign in at ${CYAN}https://platform.openai.com${NC}"
    echo -e "      ${DIM}2.${NC} Add billing, then open ${BOLD}API keys${NC} → ${BOLD}Create new secret key${NC}"
    echo -e "      ${DIM}3.${NC} Copy it now — OpenAI shows the key only once"
}

# Prompt for a single agent key and write it (only when WRITE_ENV is true).
configure_agent_key() {
    local var="$1" help_fn="$2"
    echo ""
    echo -e "  ${BOLD}${var}${NC}"
    "$help_fn"
    echo ""
    if [ "$WRITE_ENV" != true ]; then
        echo -e "    ${ARROW} Keeping the value already in your .env"
        return
    fi
    if ask_yes_no "Add ${var} now?" "y"; then
        local val
        val="$(prompt_secret)"
        if [ -n "$val" ] && key_format_ok "$var" "$val"; then
            set_env "$var" "$val"
            echo -e "    ${CHECK} ${var} saved to .env"
        else
            echo -e "    ${WARN} Skipped — add it later in .env, then restart the stack"
        fi
    else
        echo -e "    ${ARROW} Skipped — add it later in .env, then restart the stack"
    fi
}

choose_ai_client() {
    echo -e "${BOLD}Step 3/8 · Choose your AI client${NC}"
    echo -e "${DIM}  This decides which agent/profile starts and which key (if any) you need.${NC}"
    echo ""

    # Non-interactive: infer from flags (preserves scripted behavior).
    if [ "$INTERACTIVE" != true ]; then
        if [ -n "$API_KEY" ]; then
            AI_VARIANT="claude-code"; AGENT_PROFILE="claude-code"
            [ "$WRITE_ENV" = true ] && set_env "ANTHROPIC_API_KEY" "$API_KEY"
            echo -e "  ${ARROW} Claude Code (Docker) — key supplied via --api-key"
        elif [ -n "$DEEPSEEK_KEY" ]; then
            AI_VARIANT="deepseek"; AGENT_PROFILE="deepseek"
            [ "$WRITE_ENV" = true ] && set_env "DEEPSEEK_API_KEY" "$DEEPSEEK_KEY"
            echo -e "  ${ARROW} DeepSeek (Docker) — key supplied via --deepseek-key"
        elif [ -n "$ZAI_KEY" ]; then
            AI_VARIANT="zai"; AGENT_PROFILE="zai"
            [ "$WRITE_ENV" = true ] && set_env "ZAI_API_KEY" "$ZAI_KEY"
            echo -e "  ${ARROW} Z.ai / GLM 5.2 (Docker) — key supplied via --zai-key"
        else
            echo -e "  ${ARROW} No agent flag given — starting core stack only"
        fi
        echo ""
        return
    fi

    echo -e "  ${BOLD}Which AI assistant will drive the pentest?${NC}"
    echo -e "    ${CYAN}1)${NC} Claude ${DIM}(Anthropic)${NC}"
    echo -e "    ${CYAN}2)${NC} ChatGPT ${DIM}(OpenAI)${NC}"
    echo -e "    ${CYAN}3)${NC} DeepSeek"
    echo -e "    ${CYAN}4)${NC} Z.ai ${DIM}(GLM 5.2)${NC}"
    local provider; provider="$(read_choice 4 1)"
    echo ""

    case "$provider" in
        1)  # Claude → sub-choice
            echo -e "  ${BOLD}Which Claude experience?${NC}"
            echo -e "    ${CYAN}1)${NC} Claude Code — containerized in Docker  ${DIM}(recommended; needs API key)${NC}"
            echo -e "    ${CYAN}2)${NC} Claude Code — Web at claude.ai/code     ${DIM}(no key in .env)${NC}"
            echo -e "    ${CYAN}3)${NC} Claude Desktop — host app + MCP Gateway ${DIM}(no API key; app login)${NC}"
            local v; v="$(read_choice 3 1)"
            case "$v" in
                1)  AI_VARIANT="claude-code"; AGENT_PROFILE="claude-code"
                    configure_agent_key "ANTHROPIC_API_KEY" print_anthropic_help ;;
                2)  AI_VARIANT="claude-web"
                    echo ""
                    echo -e "  ${ARROW} Claude Code Web uses the stdio MCP server from ${CYAN}.mcp.json${NC} —"
                    echo -e "    ${DIM}no API key in .env. Open this repo at claude.ai/code; the full${NC}"
                    echo -e "    ${DIM}Docker stack below is optional for that path.${NC}" ;;
                3)  AI_VARIANT="claude-desktop"; add_profile gateway
                    echo ""
                    echo -e "  ${ARROW} Claude Desktop is a host app (no API key — it uses your app login)."
                    echo -e "    ${DIM}It connects through the MCP Gateway, which I'll enable for you.${NC}" ;;
            esac
            ;;
        2)  # ChatGPT / OpenAI
            AI_VARIANT="chatgpt"; add_profile gateway
            echo -e "  ${ARROW} ChatGPT/OpenAI is a host client; it connects through the MCP"
            echo -e "    ${DIM}Gateway (enabled for you). The stack itself needs no OpenAI key.${NC}"
            configure_agent_key "OPENAI_API_KEY" print_openai_help
            ;;
        3)  # DeepSeek
            AI_VARIANT="deepseek"; AGENT_PROFILE="deepseek"
            echo -e "  ${ARROW} DeepSeek runs containerized in Docker (Claude Code + DeepSeek API)."
            configure_agent_key "DEEPSEEK_API_KEY" print_deepseek_help
            ;;
        4)  # Z.ai / GLM 5.2
            AI_VARIANT="zai"; AGENT_PROFILE="zai"
            echo -e "  ${ARROW} Z.ai / GLM 5.2 runs containerized in Docker (Claude Code + Z.ai API)."
            configure_agent_key "ZAI_API_KEY" print_zai_help
            ;;
    esac
    echo ""
}

# ── Neo4j selection ──────────────────────────────────────────────────

choose_neo4j() {
    echo -e "${BOLD}Step 4/8 · Knowledge graph (Neo4j)${NC}"
    echo -e "${DIM}  Optional cross-session memory. Skip it for one-off engagements.${NC}"
    echo ""

    # Non-interactive: honor --with-neo4j (local) only.
    if [ "$INTERACTIVE" != true ]; then
        if [[ "$PROFILES" == *"--profile neo4j"* ]]; then
            NEO4J_MODE="local"
            [ "$WRITE_ENV" = true ] && {
                set_env "NEO4J_URI" "bolt://neo4j:7687"
                set_env "NEO4J_USER" "neo4j"
                set_env "NEO4J_PASSWORD" "${NEO4J_PASS:-changeme-min-8-chars}"
            }
            echo -e "  ${ARROW} Local Neo4j enabled via --with-neo4j"
        else
            echo -e "  ${ARROW} Neo4j disabled"
        fi
        echo ""
        return
    fi

    echo -e "  ${BOLD}Use a Neo4j knowledge graph?${NC}"
    echo -e "    ${CYAN}1)${NC} No — single-engagement use            ${DIM}(default)${NC}"
    echo -e "    ${CYAN}2)${NC} Local — Neo4j in Docker               ${DIM}(--profile neo4j)${NC}"
    echo -e "    ${CYAN}3)${NC} Aura — Neo4j cloud, free tier         ${DIM}(no local container)${NC}"
    local c; c="$(read_choice 3 1)"
    echo ""

    case "$c" in
        2)  NEO4J_MODE="local"; add_profile neo4j
            echo -e "  ${ARROW} Local Neo4j (Docker)"
            echo -e "    ${DIM}Bolt URI:  ${NC}bolt://neo4j:7687   ${DIM}(internal Docker network)${NC}"
            echo -e "    ${DIM}Browser:   ${NC}http://localhost:7474   ${DIM}(after startup)${NC}"
            echo ""
            if [ "$WRITE_ENV" = true ]; then
                local p; local def="changeme-min-8-chars"
                echo -e "    ${BOLD}Set a Neo4j password${NC} ${DIM}(min 8 chars; press Enter for '${def}').${NC}"
                p="$(prompt_secret "  Password (hidden): ")"
                [ -n "$p" ] || p="$def"
                # Neo4j 5 rejects passwords shorter than 8 chars and won't start.
                while [ "${#p}" -lt 8 ]; do
                    echo -e "    ${WARN} Too short — Neo4j needs at least 8 characters."
                    p="$(prompt_secret "  Password (hidden, ≥8 chars): ")"
                    [ -n "$p" ] || p="$def"
                done
                set_env "NEO4J_URI" "bolt://neo4j:7687"
                set_env "NEO4J_USER" "neo4j"
                set_env "NEO4J_PASSWORD" "$p"
                echo -e "    ${CHECK} Local Neo4j configured in .env"
            else
                echo -e "    ${ARROW} Using the Neo4j credentials already in your .env"
            fi
            ;;
        3)  NEO4J_MODE="aura"
            echo -e "  ${ARROW} Neo4j Aura (cloud) — follow these steps to get your details:"
            echo -e "    ${DIM}1.${NC} Sign in / create a free account at ${CYAN}https://console.neo4j.io${NC}"
            echo -e "    ${DIM}2.${NC} Click ${BOLD}New Instance${NC} and pick the ${BOLD}Free${NC} tier ${DIM}(\$0, no card)${NC}"
            echo -e "    ${DIM}3.${NC} On creation a credentials ${BOLD}.txt downloads automatically${NC} —"
            echo -e "       ${DIM}it has your Connection URI, Username (neo4j) and Password.${NC}"
            echo -e "       ${DIM}Save it: the password is shown only once.${NC}"
            echo -e "    ${DIM}4.${NC} Copy the Connection URI ${DIM}(looks like neo4j+s://xxxx.databases.neo4j.io)${NC}"
            echo -e "    ${DIM}Note: free instances auto-pause after 72h idle and delete after 30 days paused.${NC}"
            echo ""
            if [ "$WRITE_ENV" = true ]; then
                local uri user pass
                read -rp "  Connection URI (neo4j+s://...): " uri </dev/tty || true
                if [ -z "$uri" ]; then
                    echo -e "    ${WARN} No URI entered — skipping Aura. Add NEO4J_URI to .env later."
                    NEO4J_MODE="none"
                else
                    read -rp "  Username [neo4j]: " user </dev/tty || true
                    user="${user:-neo4j}"
                    pass="$(prompt_secret "  Password (hidden): ")"
                    set_env "NEO4J_URI" "$uri"
                    set_env "NEO4J_USER" "$user"
                    set_env "NEO4J_PASSWORD" "$pass"
                    echo -e "    ${CHECK} Aura connection saved to .env ${DIM}(no local container will start)${NC}"
                fi
            else
                echo -e "    ${ARROW} Ensure NEO4J_URI / NEO4J_USER / NEO4J_PASSWORD are set in your .env"
            fi
            ;;
        *)  echo -e "  ${ARROW} Neo4j disabled" ;;
    esac
    echo ""
}

# ── Optional recon API keys ──────────────────────────────────────────

# $1 var, $2 one-line "what it adds", $3 URL, $4 short how-to
configure_optional_key() {
    local var="$1" desc="$2" url="$3" how="$4"
    echo -e "  ${BOLD}${var}${NC} ${DIM}— ${desc}${NC}"
    echo -e "    ${DIM}Get it:${NC} ${CYAN}${url}${NC}  ${DIM}${how}${NC}"
    if ask_yes_no "Add ${var} now?" "n"; then
        local val
        val="$(prompt_secret)"
        if [ -n "$val" ]; then
            set_env "$var" "$val"
            echo -e "    ${CHECK} ${var} saved"
        else
            echo -e "    ${ARROW} Skipped"
        fi
    else
        echo -e "    ${ARROW} Skipped"
    fi
    echo ""
}

choose_optional_keys() {
    echo -e "${BOLD}Step 5/8 · Optional recon API keys${NC}"
    echo -e "${DIM}  Every tool runs WITHOUT these — they only widen passive recon coverage.${NC}"
    echo ""

    if [ "$INTERACTIVE" != true ] || [ "$WRITE_ENV" != true ]; then
        echo -e "  ${ARROW} Skipping optional-key prompts ${DIM}(add any to .env later, then restart).${NC}"
        echo ""
        return
    fi

    if ! ask_yes_no "Configure optional recon keys now? (all are skippable)" "n"; then
        echo -e "  ${ARROW} Skipped — you can add these to .env anytime."
        echo ""
        return
    fi
    echo ""

    configure_optional_key "WPSCAN_API_TOKEN" \
        "WordPress vulnerability database (wpscan auto-loads it)" \
        "https://wpscan.com/api" "free: 25 req/day — register, then copy your API token"
    configure_optional_key "SHODAN_API_KEY" \
        "subfinder passive source + Shodan host data" \
        "https://account.shodan.io" "sign in, copy the API key shown on your account page"
    configure_optional_key "VIRUSTOTAL_API_KEY" \
        "subfinder passive source" \
        "https://www.virustotal.com/gui/my-apikey" "sign in, copy the API key from your profile"
    configure_optional_key "SECURITYTRAILS_API_KEY" \
        "subfinder passive source (subdomains/history)" \
        "https://securitytrails.com" "sign up, then create an API key in account credentials"

    echo -e "  ${DIM}theHarvester and amass read keys from their OWN config files, not env${NC}"
    echo -e "  ${DIM}vars: ~/.theHarvester/api-keys.yaml and ~/.config/amass/datasources.yaml${NC}"
    echo ""
}

# ── Output directories ───────────────────────────────────────────────

create_output_dirs() {
    echo -e "${BOLD}Step 6/8 · Creating output directories${NC}"
    mkdir -p "$SCRIPT_DIR/output/reports" \
             "$SCRIPT_DIR/output/screenshots" \
             "$SCRIPT_DIR/output/sessions"
    echo -e "  ${CHECK} output/reports/      ${DIM}← pentest reports (.md, .pdf)${NC}"
    echo -e "  ${CHECK} output/screenshots/  ${DIM}← PoC evidence captures${NC}"
    echo -e "  ${CHECK} output/sessions/     ${DIM}← aggregated session JSONs${NC}"
    echo ""
}

# ── Image pull (LIVE progress) ───────────────────────────────────────

pull_images() {
    echo -e "${BOLD}Step 7/8 · Pulling Docker images${NC}"
    if [ "$SKIP_PULL" = true ]; then
        echo -e "  ${ARROW} Skipping image pull (--skip-pull)"
        echo ""
        return
    fi
    echo -e "  ${DIM}First run downloads several GB — Docker shows live per-layer progress below.${NC}"
    echo -e "  ${DIM}(Output is NOT captured, so the download bars render in real time.)${NC}"
    echo ""

    # IMPORTANT: do NOT pipe this. Docker only renders its live progress UI
    # when stdout is a TTY; piping forces silent/plain mode and hides it.
    # shellcheck disable=SC2086
    if docker compose $PROFILES pull; then
        echo ""
        echo -e "  ${CHECK} Core images ready"
    else
        echo ""
        echo -e "  ${WARN} Some images failed to pull — will retry during startup."
    fi

    # Pre-fetch the chosen containerized agent so first launch is instant.
    if [ -n "$AGENT_PROFILE" ]; then
        echo ""
        echo -e "  ${ARROW} Preparing the ${CYAN}${AGENT_PROFILE}${NC} agent image..."
        docker compose --profile "$AGENT_PROFILE" pull "$AGENT_PROFILE" \
            || docker compose --profile "$AGENT_PROFILE" build "$AGENT_PROFILE" \
            || echo -e "  ${WARN} Couldn't prepare it now; it will build on first launch."
        echo -e "  ${CHECK} ${AGENT_PROFILE} agent image ready"
    fi
    echo ""
}

# ── Start services (LIVE progress) ───────────────────────────────────

start_services() {
    echo -e "${BOLD}Step 8/8 · Starting services${NC}"
    echo -e "  ${DIM}Bringing up the core stack${NC}"
    [ -n "$PROFILES" ] && echo -e "  ${DIM}Extra profiles:${NC} ${PROFILES//--profile /}"
    echo ""

    # Streamed (not piped) so the per-container create/start status is visible.
    # Guarded so a partial failure still reaches the health dashboard below.
    # shellcheck disable=SC2086
    if docker compose $PROFILES up -d; then
        echo ""
        echo -e "  ${CHECK} Containers created"
    else
        echo ""
        echo -e "  ${WARN} Some containers failed to start — review their status below."
    fi
    echo ""
}

# ── Live health dashboard ────────────────────────────────────────────

# Render the current service table, colorized by health/state, redrawing
# in place on a TTY. Uses awk (which interprets \033) for color so we don't
# depend on echo -e semantics inside the loop.
render_status() {
    local elapsed="$1" max="$2" header table block
    if [ "$USE_COLOR" = true ]; then
        header=$(printf '  \033[2mService health  ·  %ss / %ss elapsed  (auto-refresh)\033[0m' "$elapsed" "$max")
    else
        header=$(printf '  Service health  ·  %ss / %ss elapsed  (auto-refresh)' "$elapsed" "$max")
    fi
    # shellcheck disable=SC2086
    table=$(docker compose $PROFILES ps --format "table {{.Name}}\t{{.State}}\t{{.Status}}" 2>/dev/null \
        | awk -v color="$USE_COLOR" '
            NR==1 { if (color=="true") printf "  \033[2m%s\033[0m\n", $0; else printf "  %s\n", $0; next }
            {
                if (color!="true")                     { printf "  %s\n", $0; next }
                if ($0 ~ /\(healthy\)/)                 code="32";  # green
                else if ($0 ~ /starting/)               code="33";  # yellow
                else if ($0 ~ /unhealthy|Exit|Restart/) code="31";  # red
                else                                    code="36";  # cyan
                printf "  \033[%sm%s\033[0m\n", code, $0
            }')
    block="${header}"$'\n'"${table}"

    if [ "$STATUS_LINES" -gt 0 ] && [ "$INTERACTIVE_OUT" = true ]; then
        printf '\033[%dA\033[J' "$STATUS_LINES"
    fi
    printf '%s\n' "$block"
    STATUS_LINES=$(printf '%s\n' "$block" | wc -l | tr -d ' ')
}

wait_for_health() {
    echo -e "${BOLD}Waiting for services to become healthy${NC}"
    echo -e "  ${DIM}Kali MCP takes 30–60s on first start (Metasploit DB init). Live status:${NC}"
    echo ""

    local max_wait=120 interval=4 elapsed=0
    STATUS_LINES=0

    while :; do
        if [ "$INTERACTIVE_OUT" = true ]; then
            render_status "$elapsed" "$max_wait"
        fi

        local ps_txt healthy starting
        # shellcheck disable=SC2086
        ps_txt=$(docker compose $PROFILES ps 2>/dev/null || true)
        healthy=$(printf '%s\n' "$ps_txt" | grep -c '(healthy)' || true)
        starting=$(printf '%s\n' "$ps_txt" | grep -c 'starting' || true)

        if [ "${starting:-0}" -eq 0 ] && [ "${healthy:-0}" -ge 1 ]; then
            break
        fi
        if [ "$elapsed" -ge "$max_wait" ]; then
            break
        fi
        sleep "$interval"
        elapsed=$((elapsed + interval))
    done

    # Final snapshot (also covers the non-TTY case where we skipped redraws).
    render_status "$elapsed" "$max_wait"
    echo ""

    local healthy
    # shellcheck disable=SC2086
    healthy=$(docker compose $PROFILES ps 2>/dev/null | grep -c '(healthy)' || true)
    if [ "${healthy:-0}" -ge 1 ]; then
        echo -e "  ${CHECK} ${GREEN}${BOLD}${healthy} service(s) healthy.${NC} ${DIM}Run 'make health' anytime for a recheck.${NC}"
    else
        echo -e "  ${WARN} Services may still be starting. Check with: ${CYAN}make health${NC} / ${CYAN}docker compose ps${NC}"
    fi
    echo ""
}

# ── Summary ──────────────────────────────────────────────────────────

print_launch_hint() {
    case "$AI_VARIANT" in
        claude-code)
            echo -e "  ${BOLD}Launch your agent:${NC}"
            echo -e "    ${CYAN}make claude-code${NC}    ${DIM}Start Claude Code in Docker${NC}"
            if ! env_has_value ANTHROPIC_API_KEY; then
                echo -e "    ${WARN} ${YELLOW}ANTHROPIC_API_KEY is not set${NC} — the claude-code container won't"
                echo -e "       start until you add it to ${CYAN}.env${NC} (then re-run ${CYAN}make claude-code${NC})."
            fi ;;
        deepseek)
            echo -e "  ${BOLD}Launch your agent:${NC}"
            echo -e "    ${CYAN}make deepseek${NC}       ${DIM}Start the DeepSeek agent${NC}"
            if ! env_has_value DEEPSEEK_API_KEY; then
                echo -e "    ${WARN} ${YELLOW}DEEPSEEK_API_KEY is not set${NC} — the deepseek container won't"
                echo -e "       start until you add it to ${CYAN}.env${NC} (then re-run ${CYAN}make deepseek${NC})."
            fi ;;
        zai)
            echo -e "  ${BOLD}Launch your agent:${NC}"
            echo -e "    ${CYAN}make zai${NC}            ${DIM}Start the Z.ai / GLM 5.2 agent${NC}"
            if ! env_has_value ZAI_API_KEY; then
                echo -e "    ${WARN} ${YELLOW}ZAI_API_KEY is not set${NC} — the zai container won't"
                echo -e "       start until you add it to ${CYAN}.env${NC} (then re-run ${CYAN}make zai${NC})."
            fi ;;
        claude-web)
            echo -e "  ${BOLD}Using Claude Code Web:${NC}"
            echo -e "    ${DIM}Open this repository at ${NC}$(link https://claude.ai/code "${CYAN}https://claude.ai/code${NC}")${DIM}.${NC}"
            echo -e "    ${DIM}The .mcp.json starts the blhackbox MCP server automatically; type /mcp to verify.${NC}" ;;
        claude-desktop)
            echo -e "  ${BOLD}Connect Claude Desktop${NC} ${DIM}(via the MCP Gateway, now enabled):${NC}"
            echo -e "    ${DIM}Add to your Claude Desktop config, then restart the app:${NC}"
            echo -e "      ${CYAN}{\"mcpServers\":{\"blhackbox\":{\"transport\":\"streamable-http\",\"url\":\"http://localhost:8080/mcp\"}}}${NC}"
            echo -e "    ${DIM}Config path — macOS: ~/Library/Application Support/Claude/claude_desktop_config.json${NC}"
            echo -e "    ${DIM}             Windows: %APPDATA%\\Claude\\claude_desktop_config.json${NC}"
            echo -e "    ${DIM}             Linux: ~/.config/Claude/claude_desktop_config.json${NC}" ;;
        chatgpt)
            echo -e "  ${BOLD}Connect ChatGPT/OpenAI${NC} ${DIM}(via the MCP Gateway, now enabled):${NC}"
            echo -e "    ${DIM}Point your MCP-capable client at${NC} ${CYAN}http://localhost:8080/mcp${NC} ${DIM}(Streamable HTTP).${NC}" ;;
        *)
            echo -e "  ${BOLD}Launch an agent:${NC}"
            echo -e "    ${CYAN}make claude-code${NC} ${DIM}or${NC} ${CYAN}make deepseek${NC}" ;;
    esac
}

print_summary() {
    echo -e "${DIM}══════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}${BOLD}  Setup complete!${NC}"
    echo -e "${DIM}══════════════════════════════════════════════════${NC}"
    echo ""
    print_launch_hint
    echo ""
    echo -e "  ${BOLD}Operate the stack:${NC}"
    echo -e "    ${CYAN}make status${NC}         ${DIM}Container status${NC}"
    echo -e "    ${CYAN}make health${NC}         ${DIM}MCP server health check${NC}"
    echo -e "    ${CYAN}make logs${NC}           ${DIM}View service logs${NC}"
    echo ""
    echo -e "  ${BOLD}Output files${NC} (on your host):"
    echo -e "    ${DIM}./output/reports/      Pentest reports (.md, .pdf)${NC}"
    echo -e "    ${DIM}./output/screenshots/  PoC evidence screenshots${NC}"
    echo -e "    ${DIM}./output/sessions/     Aggregated session data${NC}"
    echo ""
    echo -e "  ${BOLD}Portainer UI:${NC}  $(link https://localhost:9443 "${CYAN}https://localhost:9443${NC}")"
    echo -e "    ${WARN} Create the admin account within 5 minutes of first start!"
    if [ "$NEO4J_MODE" = "local" ]; then
        echo ""
        echo -e "  ${BOLD}Neo4j Browser:${NC}  $(link http://localhost:7474 "${CYAN}http://localhost:7474${NC}") ${DIM}(user: neo4j)${NC}"
    elif [ "$NEO4J_MODE" = "aura" ]; then
        echo ""
        echo -e "  ${BOLD}Neo4j Aura:${NC}  manage your cloud instance at $(link https://console.neo4j.io "${CYAN}https://console.neo4j.io${NC}")"
        echo -e "    ${DIM}Connection details are in your .env (no local container started).${NC}"
    fi
    echo ""
    echo -e "  ${BOLD}For pentesting:${NC} use a skill — ${DIM}/full-pentest, /quick-scan, /bug-bounty, …${NC}"
    echo ""
    echo -e "  ${DIM}Add or change keys anytime in ${NC}${CYAN}.env${NC}${DIM}, then: ${NC}${CYAN}docker compose up -d${NC}"
    echo ""
}

# ── Pre-flight confirmation ──────────────────────────────────────────

# Human-readable label for the selected AI client.
ai_label() {
    case "$AI_VARIANT" in
        claude-code)    echo "Claude Code (Docker container)" ;;
        claude-web)     echo "Claude Code (Web — claude.ai/code)" ;;
        claude-desktop) echo "Claude Desktop (host app via MCP Gateway)" ;;
        chatgpt)        echo "ChatGPT / OpenAI (host app via MCP Gateway)" ;;
        deepseek)       echo "DeepSeek (Docker — Claude Code + DeepSeek API)" ;;
        zai)            echo "Z.ai / GLM 5.2 (Docker — Claude Code + Z.ai API)" ;;
        *)              echo "None selected (core stack only)" ;;
    esac
}

# Show a review of all selections and ask before any images are pulled or
# containers started. Skipped entirely in non-interactive runs.
confirm_plan() {
    [ "$INTERACTIVE" = true ] || return 0

    echo -e "${BOLD}Review your setup${NC}"
    echo -e "${DIM}  Nothing has been pulled or started yet. Here's what will happen:${NC}"
    echo ""
    echo -e "  ${BOLD}AI client:${NC}        $(ai_label)"
    case "$NEO4J_MODE" in
        local) echo -e "  ${BOLD}Knowledge graph:${NC}  Local Neo4j (Docker container)" ;;
        aura)  echo -e "  ${BOLD}Knowledge graph:${NC}  Neo4j Aura (cloud — no local container)" ;;
        *)     echo -e "  ${BOLD}Knowledge graph:${NC}  None" ;;
    esac
    if [[ "$PROFILES" == *"--profile gateway"* ]]; then
        echo -e "  ${BOLD}MCP Gateway:${NC}      Enabled (port 8080)"
    else
        echo -e "  ${BOLD}MCP Gateway:${NC}      Disabled"
    fi
    echo ""
    echo -e "  ${BOLD}Actions:${NC}"
    if [ "$SKIP_PULL" = true ]; then
        echo -e "    ${ARROW} Skip image pull (use cached images)"
    else
        echo -e "    ${ARROW} Pull core Docker images ${DIM}(live progress)${NC}"
    fi
    [ -n "$AGENT_PROFILE" ] && echo -e "    ${ARROW} Prepare the ${CYAN}${AGENT_PROFILE}${NC} agent image"
    if [ -n "$PROFILES" ]; then
        echo -e "    ${ARROW} Start the core stack + profiles:${PROFILES//--profile /}"
    else
        echo -e "    ${ARROW} Start the core stack"
    fi
    echo -e "    ${ARROW} Wait for services to become healthy"
    echo ""
    if ! ask_yes_no "Proceed?" "y"; then
        echo ""
        echo -e "  ${ARROW} Stopped before any images were pulled or containers started."
        echo -e "    ${DIM}Your .env is saved. Re-run ${NC}${CYAN}./setup.sh${NC}${DIM} anytime.${NC}"
        exit 0
    fi
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
        --zai-key)
            ZAI_KEY="$2"
            shift 2
            ;;
        --minimal)
            MINIMAL=true
            INTERACTIVE=false
            shift
            ;;
        --with-neo4j)
            add_profile neo4j
            shift
            ;;
        --with-gateway)
            add_profile gateway
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

# --minimal means: core stack only, no optional profiles, no prompts.
if [ "$MINIMAL" = true ]; then
    PROFILES=""
    INTERACTIVE=false
fi

# ── Main ─────────────────────────────────────────────────────────────

cd "$SCRIPT_DIR"

print_banner
check_prerequisites
prepare_env
choose_ai_client
choose_neo4j
choose_optional_keys
create_output_dirs
confirm_plan
pull_images
start_services
wait_for_health
print_summary
