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

Three custom images are published to `crhacky/blhackbox` on Docker Hub:

| Service | Tag | Dockerfile | Base |
|---|---|---|---|
| **Kali MCP** | `crhacky/blhackbox:kali-mcp` | `docker/kali-mcp.Dockerfile` | `kalilinux/kali-rolling` |
| **HexStrike** | `crhacky/blhackbox:hexstrike` | `docker/hexstrike.Dockerfile` | `python:3.13-slim-bookworm` |
| **Ollama MCP** | `crhacky/blhackbox:ollama-mcp` | `docker/ollama-mcp.Dockerfile` | `python:3.13-slim-bookworm` |

Official images pulled directly (no custom build):
- `docker/mcp-gateway:latest` — MCP Gateway
- `ollama/ollama:latest` — Ollama LLM inference
- `neo4j:5` — Knowledge graph (optional)
- `portainer/portainer-ce:latest` — Docker management UI

### Pulling Images

```bash
# Pull custom images
docker pull crhacky/blhackbox:kali-mcp
docker pull crhacky/blhackbox:hexstrike
docker pull crhacky/blhackbox:ollama-mcp
```

---

## Architecture

In v2, **Claude (or OpenAI) IS the orchestrator** natively via MCP. There is no
internal LangGraph orchestrator or LLM planner. The AI client connects to the
MCP Gateway and decides which tools to call.

```
Claude (MCP Host) ──> MCP Gateway ──┬──> Kali MCP (security tools)
                                    ├──> HexStrike MCP (150+ tools, 12+ agents)
                                    └──> Ollama MCP (3-agent preprocessing)
                                              │
                                              ▼
                                           Ollama (LLM backend)

Neo4j (optional)    Portainer (Docker UI)
```

> **Ollama is required.** The Ollama MCP server's three preprocessing agents
> call Ollama's `/api/chat` endpoint. Without it, the aggregation pipeline
> returns empty results.

---

## Usage

### Full Stack (Recommended)

```bash
git clone https://github.com/valITino/blhackbox.git
cd blhackbox
git submodule update --init --recursive
cp .env.example .env       # configure API keys and Neo4j password
docker compose up -d       # start core stack (6 containers)
make ollama-pull           # pull the Ollama model (REQUIRED)
```

### With Neo4j (7 containers)

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
| `ollama-mcp` | `crhacky/blhackbox:ollama-mcp` | - | default | 3-agent preprocessing pipeline |
| `ollama` | `ollama/ollama:latest` | - | default | LLM inference backend |
| `neo4j` | `neo4j:5` | `7474` `7687` | `neo4j` | Cross-session knowledge graph |
| `portainer` | `portainer/portainer-ce:latest` | `9443` `9000` | default | Docker management UI |

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
| `LOG_LEVEL` | `INFO` | Logging verbosity |
| `RESULTS_DIR` | `./results` | Scan output directory |

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

- **Base**: `python:3.13-slim-bookworm`
- **Entrypoint**: `ollama_mcp_server.py`
- **Depends on**: Ollama container (calls `/api/chat`)
- **Agents**: Ingestion, Processing, Synthesis — three sequential agents that parse, deduplicate, and merge raw tool output into an `AggregatedPayload`
- **NOT an official Ollama product** — this is a custom blhackbox component

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

Three custom images are built and pushed to Docker Hub via GitHub Actions:

```
PR opened  ───>  CI (lint + test + pip-audit)
                      │
PR merged  ───>  CI  ───>  Build & Push (3 images)  ───>  Docker Hub
                           (on CI success)
Tag v*     ──────────────>  Build & Push (3 images)  ───>  Docker Hub

Manual     ──────────────>  Build & Push (3 images)  ───>  Docker Hub
```

Docker Scout vulnerability scanning runs on the ollama-mcp image.

---

## Useful Commands

```bash
# Start core stack (6 containers)
docker compose up -d

# Start with Neo4j (7 containers)
docker compose --profile neo4j up -d

# Pull the Ollama model (REQUIRED)
make ollama-pull

# View MCP Gateway tool call log
make gateway-logs

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

**This tool is for authorized security testing only.** Unauthorized access to computer systems is illegal.

---

## Source

[GitHub Repository](https://github.com/valITino/blhackbox)
