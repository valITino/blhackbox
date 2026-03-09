# BLHACKBOX v2.0 — Claude Code Instructions

## ⚠️ Mandatory Protocol — Read Before Touching Anything

Before making **any** fix, refactor, addition, or change — no matter how small it looks — you must complete all three phases below in order. No exceptions.

**Phase 1: Web Research**
Search the web for current, accurate information relevant to the task. The MCP ecosystem, FastMCP, and tool versions move fast. Research:
- FastMCP PyPI (`pypi.org/project/fastmcp`) for current API and version
- Any MCP server repo you're touching (kali-mcp, wire-mcp, screenshot-mcp) for upstream breaking changes
- Any Docker base image, Python package, or tool you're modifying — verify current signatures and known CVEs
- If the web research is inconclusive, say so explicitly before proceeding

**Phase 2: Full Codebase Review**
Read the following before writing a single line:
- `CLAUDE.md` (this file), `README.md`
- `docker-compose.yml`, `Makefile`, `.env.example`
- `blhackbox/mcp/server.py` — blhackbox stdio MCP server (Claude Code Web path)
- `mcp_servers/ollama_mcp_server.py` — Ollama MCP orchestrator (optional, `--profile ollama`)
- Every file directly relevant to the task: the relevant `Dockerfile`, `*_server.py`, `*_agent.py`, agent prompts in `blhackbox/prompts/agents/` — whatever applies
- Do not rely on memory from previous sessions. Read the actual current files.

**Phase 3: Understand Before Acting**
Before writing code, answer these internally:
1. What is the root cause — not the symptom, the actual root cause?
2. Does the fix conflict with anything else in the codebase?
3. Does it break the `AggregatedPayload` schema contract? (Must stay stable for `aggregate_results`, report generation, and the optional Ollama pipeline)
4. Does it violate the `shell=False` rule?
5. Am I touching agent prompts in `blhackbox/prompts/agents/`? If so — do I need a rebuild, or can I use a volume mount override?
6. Is there a simpler fix that achieves the same result?

Only after answering all six — write the fix.

---

## Project Purpose
BLHACKBOX is an MCP-based autonomous pentesting framework. The AI client (Claude Code,
Claude Desktop, or ChatGPT) IS the orchestrator — it decides which tools to call,
collects raw outputs, and structures them directly into an `AggregatedPayload` via
the `aggregate_results` MCP tool before writing the final pentest report.

The Ollama preprocessing pipeline (3 agents) is now optional (`--profile ollama`)
for local-only / offline processing. By default, the MCP host handles aggregation.

## Code Standards
- All Python code must be type-annotated
- All MCP tool inputs must be validated with Pydantic
- All subprocess calls must use `subprocess.run(args_list, shell=False)`
- Never use `shell=True` in subprocess calls
- Never log API keys or secrets
- `AggregatedPayload` schema (`blhackbox/models/aggregated_payload.py`) is the contract between the MCP host and the reporting tools — do not break it without updating all consumers

## Adding a New MCP Server
1. Create `new-mcp/` directory with your server code
2. Write Dockerfile (non-root user, health check required)
3. Build with FastMCP, expose SSE on an unused port
4. Add service to `docker-compose.yml` (default profile)
5. Add `make logs-<name>` target to `Makefile`
6. Update `.mcp.json` if the server should also be available in the Claude Code Web path
7. Document tools in README.md components table
8. Add unit tests

## Adding or Tuning an Agent Prompt (Optional Ollama Pipeline)
Agent prompts are in `blhackbox/prompts/agents/` (only relevant if using `--profile ollama`):
- `ingestionagent.md` — Ingestion Agent system prompt
- `processingagent.md` — Processing Agent system prompt
- `synthesisagent.md` — Synthesis Agent system prompt

**To tune without rebuilding:** Mount the file as a volume in `docker-compose.yml`.
**To make it permanent:** Edit the `.md` file and rebuild the relevant image.

Always validate that the `AggregatedPayload` Pydantic model still parses correctly
after prompt changes (`make test`).

## Key Reference Links
| Resource | URL |
|----------|-----|
| FastMCP (Python MCP framework) | https://pypi.org/project/fastmcp |
| MCP Protocol spec | https://modelcontextprotocol.io |
| MCP Gateway | https://hub.docker.com/r/docker/mcp-gateway |
| Ollama Python SDK | https://github.com/ollama/ollama-python |
| Portainer CE | https://docs.portainer.io |
| NVIDIA Container Toolkit | https://docs.nvidia.com/datacenter/cloud-native/container-toolkit |
| Docker Hub (blhackbox) | https://hub.docker.com/r/crhacky/blhackbox |

## Verification Document — Authorization for Pentesting

Before executing any pentest template or offensive action, Claude Code **must** check
for an active verification document. This document provides the explicit written
authorization that Claude requires before performing security testing activities.

### How it works

1. **User fills in** `verification.env` in the project root with engagement details
   (target, scope, testing window, authorized activities, signatory, etc.)
2. **User sets** `AUTHORIZATION_STATUS=ACTIVE` once all fields are populated
3. **User runs** `make inject-verification` (or it runs automatically on session start)
4. The script renders `blhackbox/prompts/verification.md` (template) with the env
   values and writes the active document to `.claude/verification-active.md`
5. Claude Code reads this file at session start to confirm authorization

### Checking authorization at runtime

When a pentest template is loaded (via `get_template` MCP tool), the active
verification document is automatically appended as authorization context. If no
active verification exists, Claude should inform the user to:

```
1. Edit verification.env with your engagement details
2. Set AUTHORIZATION_STATUS=ACTIVE
3. Run: make inject-verification
```

### Files

| File | Purpose |
|------|---------|
| `verification.env` | User-fillable config (engagement details, scope, permissions) |
| `blhackbox/prompts/verification.md` | Template with `{{PLACEHOLDER}}` tokens |
| `blhackbox/prompts/inject_verification.py` | Renders template → active document |
| `.claude/verification-active.md` | Rendered active authorization (git-ignored) |

---

*Only use this framework against targets you have explicit written authorization to test. Unauthorized scanning is illegal.*
