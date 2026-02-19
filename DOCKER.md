# crhacky/blhackbox

**MCP-based Autonomous Pentesting Framework**

---

## Quick Reference

All custom images are published to a single Docker Hub repository, differentiated by tag.

| | |
|---|---|
| **Repository** | `crhacky/blhackbox` |
| **Registry** | [Docker Hub](https://hub.docker.com/r/crhacky/blhackbox) |
| **Source** | [GitHub](https://github.com/valITino/blhackbox) |
| **License** | MIT |

---

## Images and Tags

Six custom images are published to `crhacky/blhackbox` on Docker Hub:

| Service | Tag | Dockerfile | Base |
|---|---|---|---|
| **Kali MCP** | `crhacky/blhackbox:kali-mcp` | `docker/kali-mcp.Dockerfile` | `kalilinux/kali-rolling` |
| **HexStrike** | `crhacky/blhackbox:hexstrike` | `docker/hexstrike.Dockerfile` | `python:3.13-slim-bookworm` |
| **Ollama MCP** | `crhacky/blhackbox:ollama-mcp` | `docker/ollama-mcp.Dockerfile` | `python:3.13-slim` |
| **Agent: Ingestion** | `crhacky/blhackbox:agent-ingestion` | `docker/agent-ingestion.Dockerfile` | `python:3.13-slim` |
| **Agent: Processing** | `crhacky/blhackbox:agent-processing` | `docker/agent-processing.Dockerfile` | `python:3.13-slim` |
| **Agent: Synthesis** | `crhacky/blhackbox:agent-synthesis` | `docker/agent-synthesis.Dockerfile` | `python:3.13-slim` |

Official images pulled directly (no custom build):
- `docker/mcp-gateway:latest` — MCP Gateway
- `ollama/ollama:latest` — Ollama LLM inference
- `neo4j:5` — Knowledge graph (optional)
- `portainer/portainer-ce:latest` — Docker management UI

### Pulling Images

```bash
# Pull all custom images
docker pull crhacky/blhackbox:kali-mcp
docker pull crhacky/blhackbox:hexstrike
docker pull crhacky/blhackbox:ollama-mcp
docker pull crhacky/blhackbox:agent-ingestion
docker pull crhacky/blhackbox:agent-processing
docker pull crhacky/blhackbox:agent-synthesis
```

---

## Architecture

In v2, **Claude (or OpenAI) IS the orchestrator** natively via MCP. The Ollama
MCP server is a thin orchestrator built with FastMCP that calls 3 separate
agent containers via HTTP. Each agent container runs a FastAPI server and calls
Ollama via the official `ollama` Python package independently.

```
Claude (MCP Host) ──> MCP Gateway ──┬──> Kali MCP (security tools)
                                    ├──> HexStrike MCP (150+ tools, 12+ agents)
                                    └──> Ollama MCP (thin orchestrator)
                                              │
                                              ├──► agent-ingestion:8001
                                              ├──► agent-processing:8002
                                              └──► agent-synthesis:8003
                                                        │
                                                        ▼
                                                     Ollama (LLM backend)

Neo4j (optional)    Portainer (Docker UI)
```

> **Ollama is required.** All 3 agent containers call Ollama via the official
> `ollama` Python package. Without it, the aggregation pipeline returns empty results.

---

## Usage

### Full Stack (Recommended)

```bash
git clone https://github.com/valITino/blhackbox.git
cd blhackbox
git submodule update --init --recursive
cp .env.example .env       # configure API keys and Neo4j password
docker compose up -d       # start core stack (9 containers)
make ollama-pull           # pull the Ollama model (REQUIRED)
```

### With Neo4j (10 containers)

```bash
docker compose --profile neo4j up -d
```

### Connect Claude Desktop

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

---

## Compose Services

| Service | Image | Port | Profile | Role |
|---|---|---|---|---|
| `mcp-gateway` | `docker/mcp-gateway:latest` | `8080` | default | Single MCP entry point |
| `kali-mcp` | `crhacky/blhackbox:kali-mcp` | - | default | Kali Linux security tools |
| `hexstrike` | `crhacky/blhackbox:hexstrike` | `8888` | default | HexStrike AI (150+ tools) |
| `ollama-mcp` | `crhacky/blhackbox:ollama-mcp` | - | default | Thin MCP orchestrator |
| `agent-ingestion` | `crhacky/blhackbox:agent-ingestion` | `8001` | default | Agent 1: parse raw output |
| `agent-processing` | `crhacky/blhackbox:agent-processing` | `8002` | default | Agent 2: deduplicate, compress |
| `agent-synthesis` | `crhacky/blhackbox:agent-synthesis` | `8003` | default | Agent 3: assemble payload |
| `ollama` | `ollama/ollama:latest` | - | default | LLM inference backend |
| `portainer` | `portainer/portainer-ce:latest` | `9443` `9000` | default | Docker management UI |
| `neo4j` | `neo4j:5` | `7474` `7687` | `neo4j` | Cross-session knowledge graph |

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `OLLAMA_MODEL` | `llama3.3` | Ollama model for preprocessing agents |
| `MCP_GATEWAY_PORT` | `8080` | MCP Gateway host port |
| `NEO4J_URI` | `bolt://neo4j:7687` | Neo4j connection URI |
| `NEO4J_USER` | `neo4j` | Neo4j username |
| `NEO4J_PASSWORD` | - | Neo4j password (min 8 chars) |
| `ANTHROPIC_API_KEY` | - | For Claude Desktop MCP host |
| `OPENAI_API_KEY` | - | For OpenAI MCP host |

---

## Image Details

### Kali MCP (`crhacky/blhackbox:kali-mcp`)

- **Base**: `kalilinux/kali-rolling`
- **Tools**: nmap, nikto, gobuster, dirb, whatweb, wafw00f, masscan, hydra, sqlmap, wpscan, subfinder, amass, fierce, dnsenum, whois
- **Entrypoint**: Kali MCP server (`server.py`)
- **Privileged**: Yes (required for raw socket access)

### HexStrike (`crhacky/blhackbox:hexstrike`)

- **Base**: `python:3.13-slim-bookworm`
- **Entrypoint**: HexStrike MCP server
- **Port**: `8888`
- **Source**: [github.com/0x4m4/hexstrike-ai](https://github.com/0x4m4/hexstrike-ai)

### Ollama MCP (`crhacky/blhackbox:ollama-mcp`)

- **Base**: `python:3.13-slim`
- **Entrypoint**: `ollama_mcp_server.py`
- **Role**: Thin MCP orchestrator (built with FastMCP) — calls 3 agent containers via HTTP, does NOT call Ollama directly
- **NOT an official Ollama product**

### Agent Containers (`agent-ingestion`, `agent-processing`, `agent-synthesis`)

- **Base**: `python:3.13-slim`
- **Entrypoint**: FastAPI server (`uvicorn`)
- **Ports**: 8001, 8002, 8003 respectively (internal only)
- **Depends on**: Ollama container (each calls Ollama via the official `ollama` Python package)
- **Health endpoint**: `GET /health` — returns immediately without calling Ollama
- Prompts baked in from `blhackbox/prompts/agents/` at build time
- Can be overridden via volume mount for tuning without rebuilding

---

## Volumes

Named volumes for persistent data:

| Volume | Service | Purpose |
|---|---|---|
| `ollama_models` | ollama | Ollama model storage |
| `neo4j_data` | neo4j | Neo4j graph database |
| `neo4j_logs` | neo4j | Neo4j logs |
| `portainer_data` | portainer | Portainer configuration |
| `results` | - | Scan output and reports |
| `wordlists` | - | Fuzzing wordlists |

---

## CI/CD Pipeline

Six custom images are built and pushed to Docker Hub via GitHub Actions:

```
PR opened  ───>  CI (lint + test + pip-audit)
                      │
PR merged  ───>  CI  ───>  Build & Push (6 images)  ───>  Docker Hub
                           (on CI success)
Tag v*     ──────────────>  Build & Push (6 images)  ───>  Docker Hub

Manual     ──────────────>  Build & Push (6 images)  ───>  Docker Hub
```

Docker Scout vulnerability scanning runs on the ollama-mcp image.

---

## Useful Commands

```bash
# Start core stack (9 containers)
docker compose up -d

# Start with Neo4j (10 containers)
docker compose --profile neo4j up -d

# Pull the Ollama model (REQUIRED)
make ollama-pull

# View MCP Gateway tool call log
make gateway-logs

# View agent logs
make logs-agent-ingestion
make logs-agent-processing
make logs-agent-synthesis

# Restart all 3 agent containers
make restart-agents

# Check health of all containers
make status

# Stop and clean up
docker compose down -v --remove-orphans
```

---

## Security

- **Docker socket**: MCP Gateway and Portainer mount `/var/run/docker.sock`. This grants effective root on the host. Never expose ports 8080 or 9443 to the public internet.
- **Authorization**: The `--authorized` flag is mandatory on all scan commands.
- **Neo4j**: Set a strong password in `.env`. Never use defaults in production.
- **Agent containers**: Do not expose ports to the host — they communicate only on the internal `blhackbox_net` Docker network.

**This tool is for authorized security testing only.** Unauthorized access to computer systems is illegal.

---

## Source

[GitHub Repository](https://github.com/valITino/blhackbox)
