# Architecture Decision: HexStrike Gamma vs. blhackbox selective adoption

## Decision

Keep blhackbox as the base and selectively adopt HexStrike Gamma architecture patterns.

## Evidence from HexStrike Gamma

HexStrike Gamma centralizes a very broad Flask API server and an MCP wrapper around direct tool execution, target intelligence, process management, cache statistics, error recovery, fallback chains, and visual/report helpers.

## Why blhackbox remains the base

blhackbox already has a modular Docker/MCP split:

- Kali MCP for security tools and Metasploit CLI operations.
- WireMCP for packet capture and analysis.
- Screenshot MCP for browser evidence.
- Core blhackbox MCP for templates, aggregation, reports, graph integration, and discovery.

Replacing blhackbox with a monolithic HexStrike-style API would increase migration and maintenance risk. The better path is to run HexStrike as integrated containers while keeping blhackbox as the orchestrating stack.

## Adopt now

- Low-context catalogue search.
- Workflow recommendations.
- Tool inventory and drift detection.
- MCP validation checks.
- Default HexStrike Gamma API plus full upstream HexStrike MCP service loaded unchanged and exposed over SSE.

## Adopt next

- Parameter presets.
- Fallback-chain metadata.
- Passive recon cache.
- Long-running job/process tracking in Kali MCP.
- DOM/security-header evidence in Screenshot MCP.

## Do not adopt blindly

- Direct proxying of all `/api/tools/*` routes.
- Generic command execution proxying.
- Duplicate process execution plane alongside Kali MCP.
- Unreviewed payload-generation helpers.
