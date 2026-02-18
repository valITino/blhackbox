# crhacky/blhackbox

**Autonomous pentesting framework powered by HexStrike AI**

---

## Quick Reference (CLI Image)

> This page documents the `crhacky/blhackbox` CLI image — the only image published to Docker Hub. The other service images (HexStrike, Kali MCP, Aggregator) are built locally from source.

| | |
|---|---|
| **Image** | `crhacky/blhackbox` (CLI only) |
| **Registry** | [Docker Hub](https://hub.docker.com/r/crhacky/blhackbox) |
| **Source** | [GitHub](https://github.com/crhacky/blhackbox) |
| **Base** | `python:3.13-slim-bookworm` |
| **Arch** | `linux/amd64` |
| **License** | MIT |

---

## Tags (CLI Image Only)

Only the **`crhacky/blhackbox` CLI image** is published to Docker Hub. The other service images (HexStrike, Kali MCP, Aggregator) are built locally from source and are not pushed to any registry.

| Tag | Description |
|---|---|
| `latest` | Latest stable build from `main` |
| `x.y.z` | Specific release version (e.g. `2.0.0`) |
| `x.y` | Minor release track (e.g. `2.0`) |
| `<sha>` | Exact commit build |
| `main` | Tracks the `main` branch head |

### Locally Built Images

These images are built from Dockerfiles in `docker/` and exist only on your local Docker daemon. Use `make build-all` to build them:

| Image | Dockerfile | Purpose |
|---|---|---|
| `blhackbox-hexstrike:latest` | `docker/hexstrike.Dockerfile` | HexStrike MCP Server (150+ tools) |
| `blhackbox-kali-mcp:latest` | `docker/kali-mcp.Dockerfile` | Kali Linux MCP Server (15 tools) |
| `blhackbox-aggregator:latest` | `docker/aggregator.Dockerfile` | Ollama preprocessing pipeline |

---

## What Is Blhackbox?

Blhackbox is an intelligent orchestration layer for [HexStrike AI](https://github.com/0x4m4/hexstrike-ai). In v2.0, Claude operates externally as the MCP Host (orchestrator and final analyst), while Ollama runs locally as the mandatory preprocessing backend. The Aggregator MCP server dispatches raw tool output to specialized agents that call Ollama, then returns structured data to Claude.

```
  Claude (MCP Host) ──> MCP Gateway ──┬──> HexStrike MCP (150+ tools)
                                      ├──> Kali MCP (15 tools)
                                      └──> Aggregator MCP ──> Ollama (REQUIRED)

  Neo4j (Knowledge Graph)    Blhackbox CLI (Recon · Reports)
```

> **Ollama is mandatory.** All preprocessing agents call Ollama's `/api/chat` endpoint. Without it, the aggregation pipeline returns empty results.

---

## Usage

### Docker Pull (CLI image only)

Pull the pre-built **blhackbox CLI image** from Docker Hub — this is the only image published to Docker Hub:

```bash
docker pull crhacky/blhackbox:latest

# Verify the image works
docker run --rm crhacky/blhackbox --help
docker run --rm crhacky/blhackbox version
```

> This gives you the CLI image only. It cannot run scans on its own — it needs the full stack (Ollama, Neo4j, MCP servers). Use the Compose setup below.

### Full Stack (Recommended)

The full stack includes Ollama, Neo4j, MCP Gateway, Portainer, and Blhackbox. MCP servers (HexStrike, Kali, Aggregator) are either managed by the Gateway or run directly in compose.

```bash
git clone https://github.com/crhacky/blhackbox.git
cd blhackbox
git submodule update --init --recursive
cp .env.example .env       # configure NEO4J_PASSWORD (required)
make build-all             # build all local images (blhackbox, hexstrike, kali-mcp, aggregator)
docker compose up -d       # start infrastructure
make ollama-pull           # pull the Ollama model (REQUIRED for preprocessing)
docker compose exec blhackbox blhackbox recon --target example.com --authorized
```

> **Important:** `make ollama-pull` must be run after `docker compose up -d` because it pulls the model into the running Ollama container. Without a model, the Aggregator preprocessing pipeline will fail.

### Compose Services

`docker compose up` starts the default services. MCP servers (hexstrike, kali-mcp, aggregator) are managed by the MCP Gateway by default; use `--profile direct` to run them directly in compose.

| Service | Image | Port | Profile | Role |
|---|---|---|---|---|
| `mcp-gateway` | `docker/mcp-gateway` | `8080` | default | MCP entry point for Claude Desktop |
| `neo4j` | `neo4j:5-community` | `7474` `7687` | default | Knowledge graph (HTTP / Bolt) |
| `ollama` | `ollama/ollama` | `11434` | default | Local LLM inference backend (**required**) |
| `blhackbox` | Built from repo | - | default | Orchestration & CLI |
| `portainer` | `portainer/portainer-ce` | `9443` | default | Docker management UI |
| `hexstrike` | Built from submodule | `8888` | `direct` | HexStrike MCP tool server (150+ tools) |
| `kali-mcp` | Built from Kali rolling | - | `direct` | Kali Linux security tools (15 tools) |
| `aggregator` | Built from repo | - | `direct` | Ollama preprocessing pipeline |

```bash
# Default (MCP Gateway manages MCP servers)
docker compose up -d

# Direct mode (MCP servers run in compose, no Gateway)
docker compose --profile direct up -d
```

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `HEXSTRIKE_URL` | `http://blhackbox-hexstrike:8888` | HexStrike API endpoint |
| `HEXSTRIKE_TIMEOUT` | `120` | Request timeout (seconds) |
| `HEXSTRIKE_MAX_RETRIES` | `3` | Max retries with exponential backoff |
| `NEO4J_URI` | `bolt://blhackbox-neo4j:7687` | Neo4j connection string (use `neo4j+s://...` for Aura) |
| `NEO4J_USER` | `neo4j` | Neo4j username |
| `NEO4J_PASSWORD` | - | Neo4j password (**required**, min 8 chars) |
| `NEO4J_DATABASE` | `neo4j` | Neo4j database name |
| `OLLAMA_URL` | `http://blhackbox-ollama:11434` | Ollama endpoint (**required** — preprocessing backend) |
| `OLLAMA_MODEL` | `llama3.3` | Ollama model name (**required** — used by all preprocessing agents) |
| `OPENAI_API_KEY` | - | OpenAI key (optional — deprecated `--ai` mode only) |
| `OPENAI_MODEL` | `o3` | OpenAI model name (deprecated `--ai` mode only) |
| `ANTHROPIC_API_KEY` | - | Anthropic key (optional — deprecated `--ai` mode only) |
| `ANTHROPIC_MODEL` | `claude-opus-4-20250514` | Anthropic model name (deprecated `--ai` mode only) |
| `LLM_PROVIDER_PRIORITY` | `openai,anthropic,ollama` | Deprecated — v1 fallback chain (not used in v2.0) |
| `MAX_ITERATIONS` | `10` | Max orchestrator iterations per session |
| `LOG_LEVEL` | `INFO` | Logging verbosity |
| `RESULTS_DIR` | `./results` | Scan output directory |
| `WORDLISTS_DIR` | `./wordlists` | Fuzzing wordlists directory |

---

## Image Details

- **Base**: `python:3.13-slim-bookworm`
- **System libs**: Cairo, Pango, GDK-Pixbuf (for PDF report generation via WeasyPrint)
- **User**: Runs as non-root `blhackbox` user
- **Entrypoint**: `blhackbox` CLI
- **Workdir**: `/app`

### Layer Structure

```
python:3.13-slim-bookworm
  └─ system dependencies (apt, with security upgrades)
      └─ pip dependencies (requirements.txt)
          └─ application code
              └─ non-root user setup
```

### Security Hardening

- **Non-root users**: Each service runs as a dedicated non-root user (`blhackbox`, `hexstrike`, `aggregator`, `kali-runner`)
- **No new privileges**: `security_opt: [no-new-privileges:true]` on all services
- **tmpfs**: `/tmp` mounted as `noexec,nosuid,size=256m` on the blhackbox service
- **Resource limits**: Memory and CPU caps on every service (e.g. 1G/1CPU for blhackbox, 2G/2CPU for hexstrike/neo4j, 8G/4CPU for ollama)
- **Localhost-only ports**: All host port bindings use `127.0.0.1`
- **Healthchecks**: All services include Docker healthchecks for dependency ordering
- **Minimal capabilities**: kali-mcp uses `cap_add: [NET_RAW, NET_ADMIN]` instead of `privileged` mode
- **Multi-stage builds**: Custom Dockerfiles for blhackbox, hexstrike, and aggregator use multi-stage builds to exclude build tools from runtime images

---

## Volumes

When running with Docker Compose, these bind mounts are created for the blhackbox service:

| Path | Purpose |
|---|---|
| `/app/blhackbox` | Source code (development live-reload) |
| `/app/mcp_servers` | Custom MCP server source |
| `/app/results` | Scan output and reports |
| `/app/wordlists` | Fuzzing wordlists (read-only) |

Named volumes for persistent data:

| Volume | Service | Purpose |
|---|---|---|
| `hexstrike_data` | hexstrike | HexStrike application data |
| `neo4j_data` | neo4j | Neo4j graph database |
| `neo4j_logs` | neo4j | Neo4j logs |
| `ollama_data` | ollama | Ollama model storage |
| `portainer_data` | portainer | Portainer configuration and state |

---

## CI/CD Pipeline

The **blhackbox CLI image only** is built and pushed to Docker Hub automatically via GitHub Actions. The other service images (HexStrike, Kali MCP, Aggregator) are not part of the CI/CD pipeline — they are built locally.

```
PR opened  ───>  CI (lint + test + pip-audit)
                      │
PR merged  ───>  CI  ───>  Build & Push (blhackbox CLI only)  ───>  Docker Hub
                           (on CI success)
Tag v*     ──────────────>  Build & Push (blhackbox CLI only)  ───>  Docker Hub

Manual     ──────────────>  Build & Push (blhackbox CLI only)  ───>  Docker Hub
```

Tags pushed to `crhacky/blhackbox`: `latest`, `x.y.z`, `x.y`, `main`, `<commit-sha>`

---

## Useful Commands

```bash
# Build all local images (blhackbox, hexstrike, kali-mcp, aggregator)
make build-all

# Start the full stack
docker compose up -d

# Pull the Ollama model (REQUIRED — run after 'docker compose up -d')
make ollama-pull

# Enter the blhackbox container
docker compose exec blhackbox bash

# Run a scan
docker compose exec blhackbox blhackbox recon --target example.com --authorized

# Run tests in Docker
docker compose exec blhackbox pytest tests/ -v --tb=short

# View logs
docker compose logs -f blhackbox

# Reset the knowledge graph
docker compose exec blhackbox python -m scripts.reset_graph

# Stop and clean up
docker compose down -v --remove-orphans
```

---

## Security

- All scanning commands require the `--authorized` flag
- Container runs as non-root user with no new privileges
- LLM safety prompts prevent exploit generation
- Scope enforcement in the AI orchestrator
- SSRF/path-traversal prevention in the HexStrike client
- Cypher injection prevention in the knowledge graph

**This tool is for authorized security testing only.** Unauthorized access to computer systems is illegal.

---

## Source

[GitHub Repository](https://github.com/crhacky/blhackbox)
