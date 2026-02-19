# BLHACKBOX v2.0.0

[![CI](https://github.com/valITino/blhackbox/actions/workflows/ci.yml/badge.svg)](https://github.com/valITino/blhackbox/actions/workflows/ci.yml)
[![Docker](https://github.com/valITino/blhackbox/actions/workflows/build-and-push.yml/badge.svg)](https://github.com/valITino/blhackbox/actions/workflows/build-and-push.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Docker Hub](https://img.shields.io/docker/v/crhacky/blhackbox?label=Docker%20Hub&sort=semver)](https://hub.docker.com/r/crhacky/blhackbox)

**MCP-based Autonomous Pentesting Framework**

> **LEGAL DISCLAIMER:** This tool is for **authorized security testing only**.
> You must have explicit written permission from the target owner before running
> any scans. Unauthorized testing is illegal. The `--authorized` flag is mandatory
> on all scan commands as an additional safeguard.

## Architecture

```
USER
  │
  └── MCP Host (Claude Desktop / Claude Code / OpenAI client)
            │
            │  connects once to:
            ▼
      Docker MCP Gateway  ←── single entry point, routes all MCP traffic
            │
     ┌──────┼───────┐
     ▼      ▼       ▼
  Kali   HexStrike  Ollama MCP Server (thin orchestrator)
  MCP    MCP        │
  Server Server     │  calls 3 agent containers via HTTP:
                    │
                    ├──► agent-ingestion   → calls Ollama /api/chat
                    │    returns structured data
                    │
                    ├──► agent-processing  → calls Ollama /api/chat
                    │    returns deduplicated + compressed data
                    │
                    └──► agent-synthesis   → calls Ollama /api/chat
                         returns final AggregatedPayload
                              │
                              ▼
                   AggregatedPayload → back to MCP Host
                              │
                              ▼
                   Claude / OpenAI writes final report
                              │
                              ▼ (optional)
                           Neo4j
                      stores results for
                     cross-session memory
```

In v2, **Claude (or OpenAI) IS the orchestrator** natively via MCP. There is no
internal LangGraph orchestrator or LLM planner. The AI client decides which tools
to call and in what order, collects raw output, sends it to the Ollama MCP server
for preprocessing, and writes the final report.

Each of the 3 preprocessing agents runs as its own Docker container with a
FastAPI HTTP server. This means each agent is individually visible in Portainer,
can be restarted independently, and has its own log stream.

## Components

| Container | Description | Port |
|-----------|-------------|------|
| **MCP Gateway** | Single entry point for all MCP clients | 8080 |
| **Kali MCP** | Kali Linux security tools (nmap, nikto, gobuster, etc.) | stdio |
| **HexStrike MCP** | 150+ security tools, 12+ AI agents | 8888 |
| **Ollama MCP** | Thin MCP orchestrator — calls 3 agents in sequence | stdio |
| **Agent: Ingestion** | Parses raw tool output into structured data | 8001 |
| **Agent: Processing** | Deduplicates, compresses, annotates error_log | 8002 |
| **Agent: Synthesis** | Merges into final AggregatedPayload | 8003 |
| **Ollama** | Standard LLM inference backend | 11434 |
| **Portainer** | Docker management UI | 9443 |
| **Neo4j** | Optional cross-session knowledge graph | 7474/7687 |

## Quick Start

### 1. Clone and configure

```bash
git clone https://github.com/valITino/blhackbox.git
cd blhackbox
git submodule update --init --recursive
cp .env.example .env
# Edit .env with your API keys
```

### 2. Start the stack

```bash
# Core stack (9 containers)
docker compose up -d

# Full stack with Neo4j (10 containers)
docker compose --profile neo4j up -d

# Pull the Ollama model
make ollama-pull
```

### 3. Connect Claude Desktop

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "blhackbox": {
      "transport": "sse",
      "url": "http://localhost:8080/sse"
    }
  }
}
```

### 4. Run scans

Claude will use the pentest playbook to autonomously:
1. Run recon tools (Kali + HexStrike)
2. Scan networks and enumerate services
3. Process results through the Ollama pipeline
4. Write a professional pentest report

## Ollama MCP Server — Preprocessing Pipeline

The Ollama MCP server is a thin orchestrator built with
[FastMCP](https://github.com/modelcontextprotocol/python-sdk) that calls 3
agent containers in sequence via HTTP. Each agent container is a FastAPI server
that calls Ollama via the official
[`ollama` Python package](https://github.com/ollama/ollama-python) with a
task-specific system prompt.

1. **Ingestion Agent** (`agent-ingestion:8001`) — Parses raw tool output into structured typed data
2. **Processing Agent** (`agent-processing:8002`) — Deduplicates, compresses, annotates error_log with security_relevance
3. **Synthesis Agent** (`agent-synthesis:8003`) — Merges into final `AggregatedPayload`

Agent prompts are baked into each container from `blhackbox/prompts/agents/*.md`
at build time. Override via volume mount for tuning without rebuilding.

## CLI Reference

```bash
# Show version and config
blhackbox version

# Run recon (requires --authorized flag)
blhackbox recon --target example.com --authorized
blhackbox recon --target example.com --authorized --attacks nmap,subfinder
blhackbox recon --target example.com --authorized --full

# Run a single tool
blhackbox run-tool -c network -t nmap -p '{"target":"example.com"}' --authorized

# HexStrike AI agents
blhackbox agents list
blhackbox agents run -n BugBounty -t example.com --authorized

# Knowledge graph (requires Neo4j)
blhackbox graph query "MATCH (n) RETURN n LIMIT 10"
blhackbox graph summary -t example.com

# Generate reports
blhackbox report -s SESSION_ID --format pdf

# Start MCP server
blhackbox mcp
```

## Makefile Shortcuts

```bash
make up                    # Start core stack (9 containers)
make up-full               # Start with Neo4j (10 containers)
make down                  # Stop all services
make test                  # Run tests
make lint                  # Run linter
make status                # Health status of all containers
make ollama-pull           # Pull Ollama model
make portainer             # Open Portainer dashboard
make gateway-logs          # Live MCP tool call log
make restart-agents        # Restart all 3 agent containers
make logs-agent-ingestion  # Tail Ingestion Agent logs
make push-all              # Build and push all images to Docker Hub
```

## Docker Hub Images

All custom images are published to `crhacky/blhackbox`:

| Tag | Description |
|-----|-------------|
| `crhacky/blhackbox:kali-mcp` | Kali Linux MCP Server |
| `crhacky/blhackbox:hexstrike` | HexStrike AI MCP Server |
| `crhacky/blhackbox:ollama-mcp` | Ollama MCP Server (thin orchestrator) |
| `crhacky/blhackbox:agent-ingestion` | Agent 1: Ingestion |
| `crhacky/blhackbox:agent-processing` | Agent 2: Processing |
| `crhacky/blhackbox:agent-synthesis` | Agent 3: Synthesis |

Official images pulled directly:
- `ollama/ollama:latest`
- `neo4j:5`
- `portainer/portainer-ce:latest`
- `docker/mcp-gateway:latest`

## Neo4j (Optional)

Neo4j provides cross-session memory. Enable with `--profile neo4j`:

```bash
docker compose --profile neo4j up -d
```

Stores `AggregatedPayload` results as a graph after each session.
Useful for recurring engagements against the same targets.

## GPU Support for Ollama

To enable NVIDIA GPU acceleration, uncomment the GPU block in `docker-compose.yml`
under the `ollama` service:

```yaml
deploy:
  resources:
    reservations:
      devices:
        - driver: nvidia
          count: all
          capabilities: [gpu]
```

## Security Notes

- **Docker socket**: MCP Gateway and Portainer mount `/var/run/docker.sock`.
  This grants effective root on the host. Never expose ports 8080 or 9443 to
  the public internet.
- **Authorization**: The `--authorized` flag is mandatory on all scan commands.
- **Neo4j**: Set a strong password in `.env`. Never use defaults in production.
- **Agent containers**: Do not expose ports to the host — they communicate only
  on the internal `blhackbox_net` Docker network.

## Project Structure

```
blhackbox/
├── docker/
│   ├── kali-mcp.Dockerfile
│   ├── hexstrike.Dockerfile
│   ├── ollama-mcp.Dockerfile
│   ├── agent-ingestion.Dockerfile
│   ├── agent-processing.Dockerfile
│   └── agent-synthesis.Dockerfile
├── kali-mcp/                        # adapted community Kali MCP server
├── mcp_servers/
│   └── ollama_mcp_server.py         # thin MCP orchestrator
├── blhackbox/
│   ├── agents/                      # agent server + library code
│   │   ├── base_agent.py            # base class (library/testing)
│   │   ├── base_agent_server.py     # FastAPI server base
│   │   ├── ingestion_agent.py       # library class
│   │   ├── ingestion_server.py      # container entry point
│   │   ├── processing_agent.py
│   │   ├── processing_server.py
│   │   ├── synthesis_agent.py
│   │   └── synthesis_server.py
│   ├── models/
│   │   ├── aggregated_payload.py    # AggregatedPayload Pydantic model
│   │   ├── base.py
│   │   ├── hexstrike.py
│   │   └── graph.py
│   ├── prompts/
│   │   ├── claude_playbook.md       # pentest playbook for MCP host
│   │   └── agents/
│   │       ├── ingestionagent.md
│   │       ├── processingagent.md
│   │       └── synthesisagent.md
│   ├── core/
│   │   ├── knowledge_graph.py
│   │   ├── graph_exporter.py
│   │   └── runner.py
│   ├── clients/
│   │   └── hexstrike_client.py
│   ├── reporting/
│   │   ├── html_generator.py
│   │   └── pdf_generator.py
│   ├── modules/
│   ├── utils/
│   ├── data/
│   ├── main.py
│   ├── config.py
│   └── exceptions.py
├── blhackbox-mcp-catalog.yaml
├── docker-compose.yml
├── .env.example
├── Makefile
├── hexstrike/                       # git submodule
├── tests/
└── .github/workflows/
    ├── ci.yml
    └── build-and-push.yml
```

## License

MIT
