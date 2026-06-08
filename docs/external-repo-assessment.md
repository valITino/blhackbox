# External Repository Assessment: HexStrike AI, BOAZ-MCP, BOAZ_beta

Reviewed references:

- `https://github.com/0x4m4/hexstrike-ai`
- `https://github.com/Yenn503/BOAZ-MCP`
- `https://github.com/thomasxm/BOAZ_beta`

> Network cloning from this environment was blocked by GitHub CONNECT tunnel restrictions, so this assessment used accessible public README/package index summaries and compared their architecture against the local blhackbox codebase.

## HexStrike AI ideas worth adopting

HexStrike AI's strongest public ideas are architectural rather than code-specific:

- A searchable, categorized security-tool catalogue.
- Workflow-oriented agents/profiles for bug bounty, CTF, CVE intelligence, exploit generation, and technology detection.
- Tool selection and parameter optimization before execution.
- Failure recovery, graceful degradation, and performance/caching concepts.
- Visual/evidence-oriented reporting.

### Adopted now

- Added searchable catalogue discovery through `search_tools`.
- Added exact metadata retrieval through `get_tool_details`.
- Added workflow profiles through `recommend_workflow`.
- Enriched tool metadata with backend, tags, and example parameters.

### Recommended later

- Add a local decision engine that scores candidate tools by target type, phase, authorization, and previous results.
- Add cache metadata keyed by target, tool, parameters, and timestamp.
- Add retry/fallback policies for common tool failures.

## BOAZ-MCP and BOAZ_beta ideas worth adopting carefully

BOAZ-MCP wraps BOAZ_beta for AI-assisted payload wrapping/evasion in authorized red-team labs. Its public documentation emphasizes process injection loaders, encoders, obfuscation, anti-emulation, and related techniques.

### Adopted now

- Integrated the upstream BOAZ-MCP Gamma server as the default `boaz-mcp` Docker Compose service, backed by a BOAZ_gamma checkout in the image.
- Exposed BOAZ over SSE on port `9005` and wired it into the same Claude Code Docker direct-SSE `.mcp.json` path as Kali, WireMCP, Screenshot MCP, and HexStrike.
- Kept BOAZ isolated as a separate MCP server with its own workspace mount and upstream path-confinement behavior.
- Kept authorization-gated prompts/docs and avoided automatic execution in default assessment workflows.

### Recommended follow-up hardening

- Add tests that validate path confinement and that payload inputs must already exist in an authorized lab payload directory.
- Keep BOAZ output directories explicit and separate from general report/session output.
- Continue to avoid implicit BOAZ execution in default discovery-only workflows.

## Build-vs-fork recommendation

Keep blhackbox as the base and selectively adopt design patterns. A full HexStrike fork would likely increase maintenance burden and reduce the clean separation currently present in blhackbox:

- Docker-separated MCP services.
- Core graph/reporting/prompt server.
- Explicit tests for MCP schemas and data models.
- Controlled output paths.
- Existing authorization-template workflow.

The best upgrade path is incremental: searchable catalogue, workflow profiles, health checks, caching, and CI-backed Docker smoke tests.
