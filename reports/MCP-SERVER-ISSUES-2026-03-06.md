# MCP Server Issues Report — Claude Code Web

**Date:** 2026-03-06
**Environment:** Claude Code Web (Kali Linux container, claude-opus-4-6)

---

## 1. Metasploit MCP Server (`metasploit`)

**Status:** Server loaded, but non-functional — all tool calls fail.

### Root Cause

`msfrpcd` (Metasploit RPC daemon) is not running on the expected endpoint `https://127.0.0.1:55553/api/`. A curl test returns exit code 7 ("connection refused"), confirming nothing is listening on port 55553.

### Errors Observed

| Tool Tested | Result |
|---|---|
| `msf_status` (force_reconnect=true) | `"authenticated": false, "token_present": false, "reconnect_result": "failed"` |
| `list_exploits` | "Not authenticated to msfrpcd. Ensure msfrpcd is running and credentials are correct (user=msf, ssl=True, host=127.0.0.1:55553). Login cooldown active." |
| `list_sessions` | Same authentication error + cooldown |
| `list_listeners` | Same authentication error + cooldown |

### Additional Notes

- After a failed `force_reconnect`, a login cooldown is activated (~15 seconds), during which all subsequent calls are blocked with a cooldown timer message.
- The MCP server itself starts fine and exposes tools — the issue is the backend dependency (`msfrpcd`) is not started in the container.
- Basic diagnostic tools (`ps`, `ss`) are missing from the container, making troubleshooting harder.

---

## 2. HexStrike MCP Server (`hexstrike`)

**Status:** Completely failed to load. No tools available.

### Root Cause

The `.mcp.json` config references `hexstrike/hexstrike_mcp.py` as the server entrypoint, but this file does not exist. The `hexstrike/` directory is empty. The `hexstrike-mcp/server.py` file exists in a separate directory but is not referenced by the config.

Additionally, `hexstrike` is listed in `enabledMcpjsonServers` in `/root/.claude/settings.local.json`, but since the entrypoint is missing, the server cannot start.

### Errors Observed

- No `mcp__hexstrike__*` tools appear in the deferred tools list
- No error message is surfaced to the user — silent failure
- The `/mcp` dialog showed it as failed, but no detailed error was provided

### Additional Notes

- The `hexstrike-mcp/` directory contains a `server.py` that may be the intended entrypoint — config path mismatch suspected
- No separate `mcp.json` config file exists beyond the root `.mcp.json`

---

## Summary of All Issues

| # | Server | Severity | Issue |
|---|---|---|---|
| 1 | metasploit | **High** | `msfrpcd` not running — all Metasploit tools fail with auth errors |
| 2 | metasploit | Medium | Login cooldown blocks rapid retries with no way to bypass |
| 3 | metasploit | Low | Missing `ps`/`ss` in container makes debugging difficult |
| 4 | hexstrike | **Critical** | Server fails to load entirely — zero tools available |
| 5 | hexstrike | **Critical** | Entrypoint `hexstrike/hexstrike_mcp.py` does not exist (empty directory) |
| 6 | hexstrike | High | Silent failure — no error message shown to user, only visible via `/mcp` dialog |
| 7 | hexstrike | Medium | Possible config mismatch: `hexstrike-mcp/server.py` exists but `.mcp.json` points to `hexstrike/hexstrike_mcp.py` |
| 8 | General | Medium | No external `mcp.json` config file found — all config is in `.mcp.json` at repo root |

---

## Recommended Actions

1. **Metasploit:** Ensure `msfrpcd` is started before/alongside the Metasploit MCP server (e.g., as a container entrypoint or health-checked sidecar)
2. **HexStrike:** Fix the entrypoint path in `.mcp.json` — either populate `hexstrike/hexstrike_mcp.py` or point to `hexstrike-mcp/server.py`
3. **General:** Add startup health checks that verify backend dependencies are reachable before marking MCP servers as "ready"
4. **General:** Surface MCP server startup errors prominently (not just in `/mcp` dialog)
5. **Container:** Install basic diagnostic tools (`procps`, `iproute2`) for `ps` and `ss` availability
