#!/usr/bin/env bash
# ── blhackbox — Add / Switch Model API Key ───────────────────────────
# Guided helper to configure the API key for a containerized agent model
# (Claude Code, DeepSeek, or Z.ai / GLM 5.2) WITHOUT running the full
# setup wizard. Lists the available models, shows which already have a key
# set, then prompts for the chosen model's key and writes it to .env.
#
# Usage:
#   make add-model          # (recommended)
#   bash scripts/add_model.sh
#
# The key is read from the terminal with input hidden, written verbatim to
# .env (git-ignored), and never echoed back or logged.
set -euo pipefail

# Resolve the repo root from this script's location so .env is found whether
# invoked via `make` (cwd = repo root) or directly from scripts/.
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="$ROOT_DIR/.env"

# ── Color detection (mirror setup.sh: TTY + NO_COLOR convention) ──────
USE_COLOR=true
if [ ! -t 1 ] || [ -n "${NO_COLOR:-}" ]; then
    USE_COLOR=false
fi
if [ "$USE_COLOR" = true ]; then
    RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
    CYAN='\033[0;36m'; BOLD='\033[1m'; DIM='\033[2m'; NC='\033[0m'
else
    RED=''; GREEN=''; YELLOW=''; CYAN=''; BOLD=''; DIM=''; NC=''
fi
CHECK="${GREEN}✔${NC}"; WARN="${YELLOW}!${NC}"; ARROW="${CYAN}→${NC}"

# ── Helpers (same safe patterns as setup.sh) ─────────────────────────

# Read a secret without echoing. Prompt + newline go to stderr; the value is
# the only thing on stdout (safe for command substitution). Never logged.
prompt_secret() {
    local prompt="$1" val
    read -rsp "$prompt" val </dev/tty || true
    printf '\n' >&2
    printf '%s' "$val"
}

# Set KEY=VALUE in .env. The key is a literal we control, so the value is
# NEVER passed through sed (no escaping pitfalls, injection-safe). Removes any
# prior definition (commented placeholder or active line), then appends.
set_env() {
    local key="$1" val="$2"
    sed -i -E "/^[[:space:]]*#?[[:space:]]*${key}=/d" "$ENV_FILE"
    printf '%s=%s\n' "$key" "$val" >> "$ENV_FILE"
}

# Return 0 if KEY is set to a non-empty value in .env.
env_has_value() {
    grep -qE "^$1=.+" "$ENV_FILE" 2>/dev/null
}

# "[key set]" / "[not set]" status label for the menu.
status_label() {
    if env_has_value "$1"; then
        printf '%b' "${GREEN}[key set]${NC}"
    else
        printf '%b' "${DIM}[not set]${NC}"
    fi
}

# Soft, non-blocking key-format check. Returns 0 to save, 1 to skip. Never
# prints the value. Unknown providers (e.g. Z.ai) always pass.
key_format_ok() {
    local var="$1" val="$2" ans
    case "$var" in
        ANTHROPIC_API_KEY)
            [[ "$val" == sk-ant-* ]] && return 0
            echo -e "    ${WARN} That doesn't look like an Anthropic key (expected prefix 'sk-ant-')." ;;
        DEEPSEEK_API_KEY)
            [[ "$val" == sk-* ]] && return 0
            echo -e "    ${WARN} That doesn't look like a typical API key (expected prefix 'sk-')." ;;
        *) return 0 ;;
    esac
    read -rp "    Save it anyway? [Y/n] " ans </dev/tty || true
    [[ "${ans:-y}" =~ ^[Yy] ]]
}

# ── Per-model guidance ───────────────────────────────────────────────

print_anthropic_help() {
    echo -e "    ${BOLD}What it's for:${NC} authenticates Claude Code (Anthropic) running in Docker."
    echo -e "    ${BOLD}Get it:${NC} ${CYAN}https://console.anthropic.com/settings/keys${NC}"
    echo -e "    ${DIM}Sign in → add billing → Settings → API keys → Create Key (shown once).${NC}"
}

print_deepseek_help() {
    echo -e "    ${BOLD}What it's for:${NC} authenticates the DeepSeek agent (Claude Code + DeepSeek API) in Docker."
    echo -e "    ${BOLD}Get it:${NC} ${CYAN}https://platform.deepseek.com/api_keys${NC}"
    echo -e "    ${DIM}Sign in → add balance → API keys → Create new API key (shown once).${NC}"
}

print_zai_help() {
    echo -e "    ${BOLD}What it's for:${NC} authenticates the Z.ai / GLM 5.2 agent (Claude Code + Z.ai API) in Docker."
    echo -e "    ${BOLD}Get it:${NC} ${CYAN}https://z.ai/manage-apikey/apikey-list${NC}"
    echo -e "    ${DIM}Subscribe to the GLM Coding Plan → API Keys → Add New Key (shown once).${NC}"
}

# ── Ensure .env exists ───────────────────────────────────────────────

ensure_env_file() {
    if [ ! -f "$ENV_FILE" ]; then
        cp "$ROOT_DIR/.env.example" "$ENV_FILE"
        chmod 600 "$ENV_FILE" 2>/dev/null || true
        echo -e "  ${CHECK} Created .env from the template"
        echo ""
    fi
}

# ── Main ─────────────────────────────────────────────────────────────

main() {
    echo ""
    echo -e "${CYAN}${BOLD}  ╔══════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}${BOLD}  ║      blhackbox — Add / Switch Model Key      ║${NC}"
    echo -e "${CYAN}${BOLD}  ╚══════════════════════════════════════════════╝${NC}"
    echo ""

    if [ ! -t 0 ]; then
        echo -e "  ${WARN} This is an interactive helper — run it from a terminal:"
        echo -e "      ${CYAN}make add-model${NC}"
        exit 1
    fi

    ensure_env_file

    echo -e "  Configure the API key for a containerized agent model. The key is"
    echo -e "  saved to ${CYAN}.env${NC} ${DIM}(git-ignored)${NC} and read at runtime — never written to an image."
    echo ""
    echo -e "  ${BOLD}Which model do you want to configure?${NC}"
    printf "    ${CYAN}1)${NC} %-24s %b   ${DIM}→ make claude-code${NC}\n" "Claude Code (Anthropic)" "$(status_label ANTHROPIC_API_KEY)"
    printf "    ${CYAN}2)${NC} %-24s %b   ${DIM}→ make deepseek${NC}\n"    "DeepSeek"                "$(status_label DEEPSEEK_API_KEY)"
    printf "    ${CYAN}3)${NC} %-24s %b   ${DIM}→ make zai${NC}\n"         "Z.ai / GLM 5.2"          "$(status_label ZAI_API_KEY)"
    echo ""

    local choice
    read -rp "  Enter choice [1]: " choice </dev/tty || true
    choice="${choice:-1}"

    local var launch
    case "$choice" in
        1) var="ANTHROPIC_API_KEY"; launch="make claude-code" ;;
        2) var="DEEPSEEK_API_KEY";  launch="make deepseek" ;;
        3) var="ZAI_API_KEY";       launch="make zai" ;;
        *) echo -e "  ${WARN} Invalid choice — run ${CYAN}make add-model${NC} again."; exit 1 ;;
    esac

    echo ""
    echo -e "  ${BOLD}${var}${NC}"
    case "$var" in
        ANTHROPIC_API_KEY) print_anthropic_help ;;
        DEEPSEEK_API_KEY)  print_deepseek_help ;;
        ZAI_API_KEY)       print_zai_help ;;
    esac
    echo ""

    local val
    val="$(prompt_secret "  Paste ${var} (input hidden), or press Enter to cancel: ")"
    if [ -z "$val" ]; then
        echo -e "  ${ARROW} Cancelled — nothing changed."
        exit 0
    fi
    if ! key_format_ok "$var" "$val"; then
        echo -e "  ${ARROW} Skipped — re-run ${CYAN}make add-model${NC} to try again."
        exit 0
    fi

    set_env "$var" "$val"
    chmod 600 "$ENV_FILE" 2>/dev/null || true
    echo -e "  ${CHECK} ${var} saved to .env"
    echo ""
    echo -e "  ${BOLD}Next — launch the agent:${NC}"
    echo -e "      ${CYAN}${launch}${NC}"
    echo ""
}

main "$@"
