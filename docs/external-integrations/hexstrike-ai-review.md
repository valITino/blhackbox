# HexStrike AI Gamma Review for blhackbox Integration

## Source inspected

- `https://github.com/valITino/hexstrike-ai_gamma`
- Local clone used during this task: `hexstrike-ai_gamma`
- Key files reviewed: `hexstrike_server.py`, `hexstrike_mcp.py`, `hexstrike-ai-mcp.json`, `requirements.txt`, `README.md`

## Relevant architecture observed

HexStrike AI Gamma is built around a large Flask API server plus an MCP client/server wrapper. The API surface includes:

- `/health` for comprehensive tool availability and category statistics.
- `/api/intelligence/*` for target analysis, tool selection, parameter optimization, attack-chain construction, and smart scans.
- `/api/error-handling/*` for fallback chains, alternative tools, parameter adjustments, and recovery execution.
- `/api/process/*` for async execution, process/cache stats, resource usage, and graceful process management.
- Many `/api/tools/*` routes for direct tool execution.

## What blhackbox adopted now

- Kept blhackbox as the base architecture rather than replacing it with HexStrike.
- Added/kept low-context tool discovery: `search_tools`, `get_tool_details`, `recommend_workflow`.
- Expanded workflow profiles inspired by HexStrike-style autonomous workflows.
- Added tool inventory checks to detect catalogue/server/config drift.
- Added static/live MCP validation checks.
- Added a default containerized HexStrike MCP service that loads the upstream Gamma MCP implementation unchanged and exposes it over SSE/port 9006.

## Containerized MCP integration

The production container now runs the upstream MCP tool surface through a small SSE entrypoint; blhackbox does not rewrite the upstream tool definitions. The adapter imports upstream `HexStrikeClient` and `setup_mcp_server`, points them at the `hexstrike-ai` API container, and serves the resulting FastMCP app on port `9006`.

This keeps HexStrike available as a default blhackbox MCP service on the same direct-SSE Claude Code Docker path as Kali MCP, WireMCP, Screenshot MCP, BOAZ MCP, reporting, graph storage, and templates.

## Best next implementation ideas

| HexStrike Gamma concept | blhackbox implementation path |
|---|---|
| Health/category stats | Extend `scripts/tool_inventory.py` into a core MCP `tool_health` endpoint. |
| Tool selection | Add target-aware scoring on top of `recommend_workflow`. |
| Parameter optimization | Add catalogue `presets` for quick/default/deep modes. |
| Fallback chains | Add fallback metadata such as `subfinder -> amass` and `httpx -> curl/whatweb`. |
| Process management | Add Kali MCP job IDs for long-running scans instead of only direct subprocess calls. |
| Cache stats | Add passive recon cache under `output/sessions/cache/`. |
| Browser agent ideas | Expand Screenshot MCP with DOM summary and security-header capture. |

## Fork decision

Do not replace blhackbox wholesale. Keep blhackbox as the base and run HexStrike as integrated default containers so its upstream API/MCP capabilities are available without collapsing the Docker-separated MCP design.
