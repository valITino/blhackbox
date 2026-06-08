# MCP Server Review and Upgrade Notes

## Current server topology

| Server | Transport | Port | Primary role | Tools / capability surface |
|---|---:|---:|---|---|
| `kali-mcp` | SSE | `9001` | Kali security-tool execution and Metasploit CLI workflows | 70+ allow-listed command tools including recon, web, exploitation, wireless, forensics, and utility commands |
| `wire-mcp` | SSE | `9003` | Wireshark/tshark packet capture and pcap analysis | Capture, pcap read, conversations, statistics, credential extraction, stream following, interface listing |
| `screenshot-mcp` | SSE | `9004` | Headless Chromium evidence capture | Page screenshots, element screenshots, screenshot listing, annotation |
| `blhackbox` | stdio | n/a | Core orchestration, graph/reporting, templates, catalogue discovery | Tool execution, graph queries, reports, template retrieval, result aggregation, payload schema, catalogue search |
| Docker MCP Gateway | streaming HTTP | `8080` | Optional host-client aggregation proxy | Proxies Kali, WireMCP, Screenshot MCP, HexStrike MCP, and BOAZ MCP through the Docker catalog for host clients |
| `boaz-mcp` | SSE | `9005` | Default BOAZ MCP service | Upstream BOAZ-MCP Gamma server exposed over SSE |
| `hexstrike-bridge-mcp` | SSE | `9006` | Default HexStrike Gamma MCP service | Upstream HexStrike Gamma MCP server loaded unchanged and exposed over SSE, connected to `hexstrike-ai` |

## Changes made in this review

1. Added a compact discovery layer to the core MCP server:
   - `search_tools` searches the curated catalogue by keyword/tag/category/phase.
   - `get_tool_details` returns exact metadata for a tool.
   - `recommend_workflow` returns an ordered tool profile for common assessment workflows.
2. Expanded `tools_catalog.json` from a minimal list to richer metadata:
   - `backend` so agents know whether a tool belongs to Kali MCP, WireMCP, Screenshot MCP, HexStrike MCP, BOAZ MCP, or the core server.
   - `risk` so plans can default to lower-risk discovery before active/high-risk testing.
   - `tags` for low-context semantic discovery.
   - `example_params` for safer tool invocation scaffolding.
3. Added CLI search filters for operators:
   - `blhackbox catalog --search xss --json`
4. Added a default BOAZ MCP service that runs the upstream BOAZ-MCP Gamma server with BOAZ_gamma available in the image.
5. Documented integration guidance for HexStrike AI and BOAZ-MCP Gamma while keeping their upstream tool definitions intact.

## MCP health and correctness checks

### Kali MCP

- The Docker Compose service exposes `http://localhost:9001/sse` and has an HTTP healthcheck against `/sse`.
- The server has an explicit allowlist instead of unrestricted arbitrary execution.
- Tool output is consistently structured with `stdout`, `stderr`, `exit_code`, `tool_name`, `timestamp`, and `target`.
- Recommendation: keep the allowlist, but prefer high-level wrappers for dangerous/high-impact workflows where possible.

### WireMCP

- `wire-mcp` shares `kali-mcp`'s network namespace to observe Kali-generated traffic.
- Gateway catalog points WireMCP to `http://kali-mcp:9003/sse`, matching the shared namespace design.
- Recommendation: preserve this network-mode design; add pcap fixture tests in a future PR if sample pcaps can be committed safely.

### Screenshot MCP

- The server and core MCP schemas expose four evidence-focused tools.
- Recommendation: preserve the evidence path conventions under `output/screenshots/` and keep screenshot tools low-risk.

### Core blhackbox MCP

- The new discovery tools reduce idle context compared with listing every possible tool and mirror a strong pattern seen in larger MCP ecosystems: keep tools discoverable, searchable, and workflow-oriented instead of exposing an undifferentiated wall of schemas.
- Recommendation: use `recommend_workflow` first, then `get_tool_details`, then `run_tool`/server-specific tool calls.

## What not to integrate directly yet

- Do not replace blhackbox with a HexStrike fork wholesale. Keep blhackbox as the orchestrating Docker/MCP stack while containerizing the upstream HexStrike API and MCP surfaces as default services.
- Keep BOAZ isolated as its own direct-SSE Docker MCP service (`boaz-mcp:9005`) with explicit lab-only documentation, path confinement, and dedicated output directories; do not collapse BOAZ functionality into the core blhackbox server.

## Next high-value follow-ups

1. Add a `tool_health` command that checks installed binaries inside `kali-mcp` and returns missing/stale tools.
2. Add signed/provenance-pinned external binary installs for tools fetched in Dockerfiles.
3. Add Docker image build smoke tests for all MCP servers in CI.
4. Add pcap fixtures for WireMCP parser behavior.
5. Add optional workflow state/caching so repeated AI-assisted assessments can skip unchanged passive recon results.
