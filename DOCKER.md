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

Seven custom images are published to `crhacky/blhackbox` on Docker Hub:

| Service | Tag | Dockerfile | Base |
|---|---|---|---|
| **Kali MCP** | `crhacky/blhackbox:kali-mcp` | `docker/kali-mcp.Dockerfile` | `kalilinux/kali-rolling` |
| **HexStrike** | `crhacky/blhackbox:hexstrike` | `docker/hexstrike.Dockerfile` | `python:3.13-slim-bookworm` |
| **Ollama MCP** | `crhacky/blhackbox:ollama-mcp` | `docker/ollama-mcp.Dockerfile` | `python:3.13-slim` |
| **Agent: Ingestion** | `crhacky/blhackbox:agent-ingestion` | `docker/agent-ingestion.Dockerfile` | `python:3.13-slim` |
| **Agent: Processing** | `crhacky/blhackbox:agent-processing` | `docker/agent-processing.Dockerfile` | `python:3.13-slim` |
| **Agent: Synthesis** | `crhacky/blhackbox:agent-synthesis` | `docker/agent-synthesis.Dockerfile` | `python:3.13-slim` |
| **Claude Code** | `crhacky/blhackbox:claude-code` | `docker/claude-code.Dockerfile` | `node:22-slim` |

Official images pulled directly (no custom build):
- `ollama/ollama:latest` — Ollama LLM inference
- `portainer/portainer-ce:latest` — Docker management UI
- `docker/mcp-gateway:latest` — MCP Gateway (optional, `--profile gateway`)
- `neo4j:5` — Knowledge graph (optional, `--profile neo4j`)

### Pulling Images

```bash
# Pull ALL images (custom + official) in one command
docker compose pull
```

---

## Architecture

In v2, **Claude (or OpenAI) IS the orchestrator** natively via MCP.

**Claude Code (Docker)** connects directly to each MCP server via SSE:

```
Claude Code ──┬──> Kali MCP (SSE, port 9001)
(container)   ├──> HexStrike MCP (SSE, port 8888)
              └──> Ollama MCP (SSE, port 9000)
                        │
                        ├──► agent-ingestion:8001
                        ├──► agent-processing:8002
                        └──► agent-synthesis:8003
                                  │
                                  ▼
                               Ollama (LLM backend)

Portainer (Docker UI)    Neo4j (optional)
```

**Claude Desktop / ChatGPT (host)** connect via the MCP Gateway:

```
Claude Desktop ──> MCP Gateway (localhost:8080/mcp) ──┬──> Kali MCP
(host app)                                            ├──> HexStrike MCP
                                                      └──> Ollama MCP
```

> **Ollama is required.** All 3 agent containers call Ollama via the official
> `ollama` Python package. Without it, the aggregation pipeline returns empty results.

---

## Usage

### Core Stack (8 containers)

```bash
git clone https://github.com/valITino/blhackbox.git
cd blhackbox
cp .env.example .env       # configure ANTHROPIC_API_KEY
docker compose pull        # pull ALL images in one command
docker compose up -d       # start core stack
make ollama-pull           # pull the Ollama model (REQUIRED)
```

### With Claude Code (Recommended)

```bash
make claude-code           # builds + launches Claude Code in Docker
```

### With MCP Gateway (for Claude Desktop / ChatGPT)

```bash
make up-gateway            # starts core + gateway on port 8080
```

### With Neo4j

```bash
docker compose --profile neo4j up -d
```

### Verify

```bash
make status                # container status table
make health                # MCP server health check
```

---

## Compose Services

| Service | Image | Port | Profile | Role |
|---|---|---|---|---|
| `kali-mcp` | `crhacky/blhackbox:kali-mcp` | `9001` | default | Kali Linux security tools |
| `hexstrike` | `crhacky/blhackbox:hexstrike` | `8888` | default | HexStrike AI (150+ tools) |
| `ollama-mcp` | `crhacky/blhackbox:ollama-mcp` | `9000` | default | Thin MCP orchestrator |
| `agent-ingestion` | `crhacky/blhackbox:agent-ingestion` | `8001` | default | Agent 1: parse raw output |
| `agent-processing` | `crhacky/blhackbox:agent-processing` | `8002` | default | Agent 2: deduplicate, compress |
| `agent-synthesis` | `crhacky/blhackbox:agent-synthesis` | `8003` | default | Agent 3: assemble payload |
| `ollama` | `ollama/ollama:latest` | `11434` | default | LLM inference backend |
| `portainer` | `portainer/portainer-ce:latest` | `9443` `9000` | default | Docker management UI |
| `mcp-gateway` | `docker/mcp-gateway:latest` | `8080` | `gateway` | Single MCP entry point (host clients) |
| `neo4j` | `neo4j:5` | `7474` `7687` | `neo4j` | Cross-session knowledge graph |
| `claude-code` | `crhacky/blhackbox:claude-code` | - | `claude-code` | Claude Code CLI client (Docker) |

---

## MCP Connection Modes

### Claude Code in Docker (Direct SSE — no gateway)

The Claude Code container's `.mcp.json` connects directly to each server:

```json
{
  "mcpServers": {
    "kali":            { "type": "sse", "url": "http://kali-mcp:9001/sse" },
    "hexstrike":       { "type": "sse", "url": "http://hexstrike:8888/sse" },
    "ollama-pipeline": { "type": "sse", "url": "http://ollama-mcp:9000/sse" }
  }
}
```

### Claude Desktop (via MCP Gateway)

Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "blhackbox": {
      "transport": "streamable-http",
      "url": "http://localhost:8080/mcp"
    }
  }
}
```

Requires `--profile gateway` (`make up-gateway`).

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | - | Required for Claude Code in Docker |
| `OLLAMA_MODEL` | `llama3.3` | Ollama model for preprocessing agents |
| `MCP_GATEWAY_PORT` | `8080` | MCP Gateway host port (optional) |
| `NEO4J_URI` | `bolt://neo4j:7687` | Neo4j connection URI (optional) |
| `NEO4J_USER` | `neo4j` | Neo4j username (optional) |
| `NEO4J_PASSWORD` | - | Neo4j password, min 8 chars (optional) |
| `OPENAI_API_KEY` | - | For OpenAI MCP clients (optional) |

---

## Image Details

### Kali MCP (`crhacky/blhackbox:kali-mcp`)

- **Base**: `kalilinux/kali-rolling`
- **Tools**: nmap, nikto, gobuster, dirb, whatweb, wafw00f, masscan, hydra, sqlmap, wpscan, subfinder, amass, fierce, dnsenum, whois
- **Entrypoint**: Kali MCP server (`server.py`)
- **Transport**: SSE on port 9001
- **Privileged**: Yes (required for raw socket access)

### HexStrike (`crhacky/blhackbox:hexstrike`)

- **Base**: `python:3.13-slim-bookworm`
- **Entrypoint**: HexStrike MCP server
- **Transport**: SSE on port 8888
- **Source**: [github.com/0x4m4/hexstrike-ai](https://github.com/0x4m4/hexstrike-ai)

### Ollama MCP (`crhacky/blhackbox:ollama-mcp`)

- **Base**: `python:3.13-slim`
- **Entrypoint**: `ollama_mcp_server.py`
- **Transport**: SSE on port 9000
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

### Claude Code (`crhacky/blhackbox:claude-code`)

- **Base**: `node:22-slim`
- **Entrypoint**: `claude-code-entrypoint.sh` (health checks + launch)
- **MCP config**: Direct SSE to each server (no gateway dependency)
- **Note**: Requires `ANTHROPIC_API_KEY` in `.env`

---

## Portainer

Portainer CE provides a web dashboard for all blhackbox containers.

- **URL**: `https://localhost:9443`
- **First run**: Create an admin account within 5 minutes of startup
- **Missed the window?** `docker compose restart portainer`

> Your browser will warn about the self-signed HTTPS certificate. This is
> expected. Click "Advanced" and proceed.

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

Seven custom images are built and pushed to Docker Hub via GitHub Actions:

```
PR opened  ───>  CI (lint + test + pip-audit)
                      │
PR merged  ───>  CI  ───>  Build & Push (7 images)  ───>  Docker Hub
                           (on CI success)
Tag v*     ──────────────>  Build & Push (7 images)  ───>  Docker Hub

Manual     ──────────────>  Build & Push (7 images)  ───>  Docker Hub
```

Docker Scout vulnerability scanning runs on the ollama-mcp image.

---

## Useful Commands

```bash
# Pull all pre-built images from Docker Hub
docker compose pull

# Start core stack (8 containers)
docker compose up -d

# Start with MCP Gateway for Claude Desktop (9 containers)
make up-gateway

# Start with Neo4j (9 containers)
docker compose --profile neo4j up -d

# Launch Claude Code in Docker
make claude-code

# Pull the Ollama model (REQUIRED)
make ollama-pull

# Check health of all MCP servers
make health

# Container status
make status

# View service logs
make logs-kali
make logs-hexstrike
make logs-agent-ingestion
make logs-agent-processing
make logs-agent-synthesis
make gateway-logs

# Restart all 3 agent containers
make restart-agents

# Stop and clean up
make down
make clean                 # also removes volumes
```

---

## GPU Support

NVIDIA GPU acceleration is **enabled by default** for the Ollama service. This
requires the [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html)
on the host.

If you do **not** have an NVIDIA GPU, comment out the `deploy` block under the
`ollama` service in `docker-compose.yml`. Ollama will fall back to CPU-only
inference automatically.

---

## Security

- **Docker socket**: MCP Gateway (optional) and Portainer mount `/var/run/docker.sock`. This grants effective root on the host. Never expose ports 8080 or 9443 to the public internet.
- **Authorization**: Ensure you have written permission before scanning any target.
- **Neo4j**: Set a strong password in `.env`. Never use defaults in production.
- **Agent containers**: Communicate only on the internal `blhackbox_net` Docker network. No ports exposed to host.
- **Portainer**: Uses HTTPS with a self-signed certificate. Create a strong admin password on first run.

**This tool is for authorized security testing only.** Unauthorized access to computer systems is illegal.

---

## Source

[GitHub Repository](https://github.com/valITino/blhackbox)
