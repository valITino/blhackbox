#!/bin/bash
# OpSec Fingerprint Audit — read-only inventory of what THIS session leaks.
#
# Surfaces the operator's own footprint so it can be hardened before touching a
# target: egress/exit point, DNS resolver, host identity, per-tool default
# User-Agents, and the Screenshot-MCP browser's fingerprint + favicon-cache
# ("supercookie") exposure.
#
# This script ONLY observes and reports. It never mutates state, never touches a
# target, and never tampers with any logs. Hardening is applied separately by the
# operator following the /opsec-check playbook.
#
# Usage: .claude/opsec-audit.sh
# Findings are tagged [HIGH] / [MED] / [LOW] / [OK] for the MCP host to interpret.

set -uo pipefail

HIGH=0; MED=0; LOW=0

high() { echo "[HIGH] $*"; HIGH=$((HIGH + 1)); }
med()  { echo "[MED]  $*"; MED=$((MED + 1)); }
low()  { echo "[LOW]  $*"; LOW=$((LOW + 1)); }
ok()   { echo "[OK]   $*"; }
hdr()  { echo ""; echo "── $* ──"; }

echo "BLHACKBOX OpSec Fingerprint Audit — $(date -u '+%Y-%m-%dT%H:%M:%SZ')"

# ── 1. Egress / exit point ──────────────────────────────────────
hdr "Egress / exit point"
PROXY_SET=""
for v in ALL_PROXY all_proxy HTTPS_PROXY https_proxy SOCKS_PROXY socks_proxy; do
    [ -n "${!v:-}" ] && PROXY_SET="${!v}"
done
EGRESS_IP="$(curl -s --max-time 6 https://api.ipify.org 2>/dev/null || true)"
# Only trust a response that actually looks like an IP — a restrictive network
# policy may return an error page/body instead of failing the request.
if ! echo "$EGRESS_IP" | grep -qE '^[0-9a-fA-F:.]+$'; then
    EGRESS_IP=""
fi
if [ -z "$EGRESS_IP" ]; then
    ok "Egress IP not resolvable from here (network policy may restrict outbound)"
elif [ -n "$PROXY_SET" ]; then
    ok "Outbound proxy configured ($PROXY_SET); observed exit IP: $EGRESS_IP"
else
    high "No proxy/VPN/Tor egress configured — traffic exits from raw host IP $EGRESS_IP. Route through SOCKS/VPN/Tor before active testing."
fi
if command -v tor >/dev/null 2>&1; then
    ok "tor binary present (usable as an egress)"
else
    low "tor not installed — only relevant if Tor is your intended exit"
fi

# ── 2. DNS resolver ─────────────────────────────────────────────
hdr "DNS resolver"
if [ -r /etc/resolv.conf ]; then
    NS="$(grep -E '^nameserver' /etc/resolv.conf 2>/dev/null | awk '{print $2}' | paste -sd, -)"
    if [ -n "$NS" ]; then
        med "Active DNS resolver(s): $NS — confirm queries route through your controlled/egress resolver, not the host/ISP default (DNS leak risk)."
    else
        ok "No explicit nameserver in /etc/resolv.conf"
    fi
else
    ok "/etc/resolv.conf not readable"
fi

# ── 3. Host identity ────────────────────────────────────────────
hdr "Host identity"
low "Hostname: $(hostname 2>/dev/null || echo unknown) — avoid identifiable hostnames in any banner the target may capture."
TZ_VAL="$(cat /etc/timezone 2>/dev/null || date +%Z 2>/dev/null || echo unknown)"
low "Timezone: ${TZ_VAL}  /  Locale: ${LANG:-unset} — these surface in browser fingerprints and some tool output."
if command -v ip >/dev/null 2>&1; then
    MACS="$(ip link 2>/dev/null | awk '/link\/ether/{print $2}' | paste -sd, -)"
    [ -n "$MACS" ] && low "MAC address(es): $MACS — only leaks on same L2 segment, but note it for internal engagements."
fi

# ── 4. Tool default User-Agents ────────────────────────────────
hdr "Tool default User-Agents / signatures"
declare -A UA_TELL=(
    [curl]="curl/<version>"
    [wget]="Wget/<version>"
    [nikto]="Mozilla/5.00 (Nikto/...)"
    [sqlmap]="sqlmap/<version>"
    [nuclei]="Nuclei - Open-source..."
    [gobuster]="gobuster/<version>"
    [wpscan]="WPScan v<version>"
    [nmap]="Nmap NSE http UA + distinctive timing/flags"
)
FOUND_TOOLS=0
for t in "${!UA_TELL[@]}"; do
    if command -v "$t" >/dev/null 2>&1; then
        FOUND_TOOLS=$((FOUND_TOOLS + 1))
        med "$t present → default identifier '${UA_TELL[$t]}' is trivially attributable. Override the User-Agent / randomize timing before use."
    fi
done
[ "$FOUND_TOOLS" -eq 0 ] && ok "No common signature-leaking CLI tools detected on PATH"

# ── 5. Screenshot browser fingerprint + supercookie surface ─────
hdr "Screenshot-MCP browser fingerprint & cache (supercookie) surface"
BROWSER=""
for b in chromium chromium-browser google-chrome chrome; do
    command -v "$b" >/dev/null 2>&1 && BROWSER="$b" && break
done
if [ -z "$BROWSER" ]; then
    ok "No system Chromium/Chrome on PATH (screenshot MCP may bundle its own — audit that profile too)"
else
    med "$BROWSER present — a target can fingerprint canvas/WebGL/fonts and detect headless tells. Drive it with anti-fingerprint flags and a non-headless-obvious profile."
    # Persistent profile dirs are the supercookie surface: a planted favicon
    # cache entry survives normal cookie clearing and correlates sessions.
    for d in "$HOME/.config/chromium" "$HOME/.config/google-chrome" "$HOME/.cache/chromium" "$HOME/snap/chromium/common/chromium"; do
        if [ -d "$d" ]; then
            high "Persistent browser profile/cache at $d — favicon-cache 'supercookie' entries here survive incognito and cookie clearing, letting a target correlate your browser across engagements. Use an ephemeral profile cleared between targets."
        fi
    done
    [ "$HIGH" -eq 0 ] && low "No persistent Chromium profile found yet — keep it that way: ephemeral, per-engagement profiles only."
fi

# ── Summary ─────────────────────────────────────────────────────
echo ""
echo "━━━ OpSec Audit Summary ━━━"
echo "HIGH: $HIGH   MED: $MED   LOW: $LOW"
if [ "$HIGH" -gt 0 ]; then
    echo "Resolve all HIGH items before active testing. See /opsec-check for the hardening playbook."
else
    echo "No HIGH leaks detected. Review MED/LOW items and proceed under OpSec discipline."
fi
exit 0
