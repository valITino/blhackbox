# blhackbox Repository Audit

## Scope

This audit covers the current repository structure, MCP servers, Docker/config files, tests, scripts, and Markdown documentation.

## High-priority findings

| Area | Finding | Impact | Recommendation |
|---|---|---|---|
| MCP live validation | Static tests cannot prove Docker services are running. | Broken containers or SSE endpoints may pass unit tests. | Use `make check-mcp LIVE=1` after `docker compose up -d`; HexStrike and BOAZ are checked as default services. |
| Tool/catalog drift | Catalogue, Kali allowlist, Dockerfile packages, and MCP configs can drift. | Agents may recommend tools that are unavailable or misrouted. | Use `scripts/tool_inventory.py`; later promote to CI. |
| External binary installs | Dockerfile downloads release artifacts for tools not in apt. | Supply-chain/version drift. | Pin checksums/signatures where available. |
| Integrated services | HexStrike/BOAZ now run in the default compose stack. | Default services can drift from host, gateway, or Claude Code Docker MCP configs if not checked. | Keep `make mcp-status`, `scripts/tool_inventory.py`, and `docs/container-integration-review.md` updated with every service change. |

## Medium-priority findings

| Area | Finding | Impact | Recommendation |
|---|---|---|---|
| Workflow profiles | Profiles are currently static lists. | Less adaptive than HexStrike-style decision engine. | Add parameter presets and fallback suggestions per tool. |
| Screenshot MCP | Good screenshot coverage but limited DOM/header analysis. | Misses browser-agent evidence ideas. | Add DOM summary/security-header capture as future safe tools. |
| WireMCP tests | Static tests exist, but pcap fixture coverage can be improved. | Parser regressions may be missed. | Add small sanitized pcap fixtures. |
| Docs | README is comprehensive but long. | New users may miss operator flows. | Split quickstart vs reference sections over time. |

## Low-priority findings

| Area | Finding | Impact | Recommendation |
|---|---|---|---|
| CLI catalog | Search is useful but plain. | Operators may want exact workflow display. | Add `blhackbox catalog workflow <name>` later. |
| Security scan | Offline scanner is intentionally basic. | Does not replace Bandit/pip-audit. | Add optional Makefile target that runs external scanners when installed. |

## Implemented in this iteration

- Removed unwanted risk labels/gates from tool discovery.
- Added static/live MCP validation script.
- Added tool inventory consistency script.
- Replaced the local BOAZ helper implementation with a default containerized integration of the upstream BOAZ-MCP Gamma server.
- Added HexStrike Gamma API + upstream MCP service as default containerized integrations.
- Added HexStrike architecture decision docs and workflow profile expansion.
- Added container integration review documentation.
