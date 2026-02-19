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
  Kali   HexStrike  Ollama MCP Server
  MCP    MCP        │
  Server Server     │  internally runs 3 agents:
                    ├── Agent 1: Ingestion
                    ├── Agent 2: Processing
                    └── Agent 3: Synthesis
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

## Components

| Service | Description | Port |
|---------|-------------|------|
| **MCP Gateway** | Single entry point for all MCP clients | 8080 |
| **Kali MCP** | Kali Linux security tools (nmap, nikto, gobuster, etc.) | stdio |
| **HexStrike MCP** | 150+ security tools, 12+ AI agents | 8888 |
| **Ollama MCP** | Custom preprocessing (3 agents → AggregatedPayload) | stdio |
| **Ollama** | Standard LLM inference backend | 11434 |
| **Neo4j** | Optional cross-session knowledge graph | 7474/7687 |
| **Portainer** | Docker management UI | 9443 |

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
# Core stack (6 containers)
docker compose up -d

# Full stack with Neo4j (7 containers)
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

The Ollama MCP server is the **only custom-built component** in blhackbox.
Ollama itself runs unchanged as `ollama/ollama:latest`.

Three sequential agents process raw tool output:

1. **Ingestion Agent** — Parses raw tool output into structured typed data
2. **Processing Agent** — Deduplicates, compresses, annotates error_log with security_relevance
3. **Synthesis Agent** — Merges into final `AggregatedPayload`

Agent prompts are loaded from `blhackbox/prompts/agents/*.md` at runtime.
Operators can tune behavior without code changes.

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
make up              # Start core stack
make up-full         # Start with Neo4j
make down            # Stop all services
make test            # Run tests
make lint            # Run linter
make status          # Health status of all containers
make ollama-pull     # Pull Ollama model
make portainer       # Open Portainer dashboard
make gateway-logs    # Live MCP tool call log
make push-all        # Build and push all images to Docker Hub
```

## Docker Hub Images

All custom images are published to `crhacky/blhackbox`:

| Tag | Description |
|-----|-------------|
| `crhacky/blhackbox:kali-mcp` | Kali Linux MCP Server |
| `crhacky/blhackbox:hexstrike` | HexStrike AI MCP Server |
| `crhacky/blhackbox:ollama-mcp` | Ollama MCP Server (custom) |

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

## Project Structure

```
blhackbox/
├── docker/
│   ├── kali-mcp.Dockerfile
│   ├── hexstrike.Dockerfile
│   └── ollama-mcp.Dockerfile
├── kali-mcp/                        # adapted community Kali MCP server
├── mcp_servers/
│   └── ollama_mcp_server.py         # custom blhackbox MCP server
├── blhackbox/
│   ├── agents/                      # Ollama preprocessing agents
│   │   ├── base_agent.py
│   │   ├── ingestion_agent.py
│   │   ├── processing_agent.py
│   │   └── synthesis_agent.py
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
