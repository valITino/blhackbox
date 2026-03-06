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
- `mcp_servers/ollama_mcp_server.py` — Ollama MCP orchestrator
- Every file directly relevant to the task: the relevant `Dockerfile`, `*_server.py`, `*_agent.py`, agent prompts in `blhackbox/prompts/agents/` — whatever applies
- Do not rely on memory from previous sessions. Read the actual current files.

**Phase 3: Understand Before Acting**
Before writing code, answer these internally:
1. What is the root cause — not the symptom, the actual root cause?
2. Does the fix conflict with anything else in the codebase?
3. Does it break the Ollama pipeline contract? (`AggregatedPayload` schema must stay stable across Ingestion → Processing → Synthesis)
4. Does it violate the `shell=False` rule?
5. Am I touching agent prompts in `blhackbox/prompts/agents/`? If so — do I need a rebuild, or can I use a volume mount override?
6. Is there a simpler fix that achieves the same result?

Only after answering all six — write the fix.

---

## Project Purpose
BLHACKBOX is an MCP-based autonomous pentesting framework. The AI client (Claude Code,
Claude Desktop, or ChatGPT) IS the orchestrator — it decides which tools to call,
collects raw outputs, and sends them to the Ollama pipeline for preprocessing before
writing the final pentest report.

## Code Standards
- All Python code must be type-annotated
- All MCP tool inputs must be validated with Pydantic
- All subprocess calls must use `subprocess.run(args_list, shell=False)`
- Never use `shell=True` in subprocess calls
- Never log API keys or secrets
- `AggregatedPayload` schema (`blhackbox/models/aggregated_payload.py`) is the contract between the pipeline and the AI — do not break it without updating all three agents

## Adding a New MCP Server
1. Create `new-mcp/` directory with your server code
2. Write Dockerfile (non-root user, health check required)
3. Build with FastMCP, expose SSE on an unused port
4. Add service to `docker-compose.yml` (default profile)
5. Add `make logs-<name>` target to `Makefile`
6. Update `.mcp.json` if the server should also be available in the Claude Code Web path
7. Document tools in README.md components table
8. Add unit tests

## Adding or Tuning an Agent Prompt
Agent prompts are in `blhackbox/prompts/agents/`:
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

---

*Only use this framework against targets you have explicit written authorization to test. Unauthorized scanning is illegal.*
