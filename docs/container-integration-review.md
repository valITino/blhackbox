# Container Integration Review

## Current container topology

| Startup | Service | Purpose | Port(s) | Network |
|---|---|---|---:|---|
| default | `kali-mcp` | Kali tool execution and Metasploit CLI workflows | `9001` | `blhackbox_net` |
| default | `wire-mcp` | tshark/Wireshark traffic tools sharing Kali network namespace | `9003` | `service:kali-mcp` |
| default | `screenshot-mcp` | Playwright/Chromium evidence capture | `9004` | `blhackbox_net` |
| default | `hexstrike-ai` | Capsulated HexStrike Gamma API | `8888` | `blhackbox_net` |
| default | `hexstrike-bridge-mcp` | Full upstream HexStrike Gamma MCP server loaded unchanged and exposed over SSE | `9006` | `blhackbox_net` |
| default | `boaz-mcp` | Upstream BOAZ-MCP Gamma server with image-bundled `BOAZ_gamma` | `9005` | `blhackbox_net` |
| default | `portainer` | Local container management UI | `9443` | `blhackbox_net` |
| `gateway` | `mcp-gateway` | Gateway for host clients that explicitly need it | `8080` | `blhackbox_net` |
| `neo4j` | `neo4j` | Graph database | `7474`, `7687` | `blhackbox_net` |
| `claude-code` | `claude-code` | In-network MCP client | n/a | `blhackbox_net` |

## Interconnection review

- `hexstrike-bridge-mcp` depends on `hexstrike-ai` and uses `HEXSTRIKE_URL=http://hexstrike-ai:8888`.
- `boaz-mcp` loads upstream BOAZ-MCP Gamma from `BOAZ_MCP_PATH=/opt/BOAZ-MCP_gamma`, uses `BOAZ_PATH=/opt/BOAZ_gamma`, and mounts `./output/boaz-lab` for operator workspace files.
- `claude-code` has `NO_PROXY` entries for all internal service hostnames.
- `wire-mcp` intentionally shares the Kali network namespace for packet visibility.
- `mcp-gateway` remains available only for clients that require a single host-side Streamable HTTP endpoint; normal Docker-based Claude Code operation connects directly to Kali, WireMCP, Screenshot MCP, BOAZ MCP, and HexStrike MCP.

## Operator commands

- `make up` starts the default stack, including HexStrike and BOAZ.
- `make mcp-status` runs static MCP validation, tool inventory, and the fallback security scan.
- `make check-mcp LIVE=1` checks live endpoints for default MCP services.
- `make logs-hexstrike` tails HexStrike API and MCP logs.
- `make logs-boaz` tails BOAZ MCP logs.

## Review outcome

The stack is aligned around one Docker network, default-start MCP services, predictable ports, and health checks. HexStrike and BOAZ are no longer profile-gated sidecars; they are integrated into the normal compose lifecycle and the Claude Code direct-SSE path like the other MCP services.
