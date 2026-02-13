# crhacky/blhackbox

**Autonomous pentesting framework powered by HexStrike AI**

---

## Quick Reference

| | |
|---|---|
| **Image** | `crhacky/blhackbox` |
| **Registry** | [Docker Hub](https://hub.docker.com/r/crhacky/blhackbox) |
| **Source** | [GitHub](https://github.com/crhacky/blhackbox) |
| **Base** | `python:3.13-slim-bookworm` |
| **Arch** | `linux/amd64` |
| **License** | MIT |

---

## Tags

| Tag | Description |
|---|---|
| `latest` | Latest stable build from `main` |
| `x.y.z` | Specific release version (e.g. `1.0.0`) |
| `x.y` | Minor release track (e.g. `1.0`) |
| `<sha>` | Exact commit build |
| `main` | Tracks the `main` branch head |

---

## What Is Blhackbox?

Blhackbox is an intelligent orchestration layer for [HexStrike AI](https://github.com/0x4m4/hexstrike-ai). It adds autonomous planning (LLM-powered via LangGraph), a persistent knowledge graph (Neo4j), and professional reporting (PDF/HTML) to HexStrike's 150+ security tools and 12+ AI agents.

```
                  ┌──────────────────────────────┐
                  │       Blhackbox Layer         │
                  │                               │
  CLI / AI ──────>│  Orchestrator  ─>  Planner    │
                  │       │                       │
                  │       v                       │
                  │  Knowledge Graph (Neo4j)      │
                  │       │                       │
                  │       v                       │
                  │  HexStrike API Client         │
                  └───────┬───────────────────────┘
                          v
                  ┌──────────────────────────────┐
                  │   HexStrike MCP Server        │
                  │   150+ tools · 12+ agents     │
                  └──────────────────────────────┘
```

---

## Usage

### Standalone (CLI)

```bash
docker run --rm crhacky/blhackbox --help
docker run --rm crhacky/blhackbox version
```

### Full Stack (Recommended)

The full stack includes HexStrike, Neo4j, and Blhackbox. Use the provided `docker-compose.yml`:

```bash
git clone https://github.com/crhacky/blhackbox.git
cd blhackbox
git submodule update --init --recursive
cp .env.example .env    # configure API keys and NEO4J_PASSWORD
docker compose up -d
docker compose exec blhackbox blhackbox recon --target example.com --authorized
```

### Compose Services

| Service | Image | Port | Role |
|---|---|---|---|
| `blhackbox` | Built from repo | - | Orchestration & CLI |
| `hexstrike` | Built from submodule | `8888` | MCP tool server (150+ tools) |
| `neo4j` | `neo4j:5-community` | `7474` `7687` | Knowledge graph (HTTP / Bolt) |
| `ollama` | `ollama/ollama` | `11434` | Local LLM (optional profile) |

Start with local LLM support:

```bash
docker compose --profile ollama up -d
```

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `HEXSTRIKE_URL` | `http://hexstrike:8888` | HexStrike API endpoint |
| `HEXSTRIKE_TIMEOUT` | `120` | Request timeout (seconds) |
| `HEXSTRIKE_MAX_RETRIES` | `3` | Max retries with exponential backoff |
| `NEO4J_URI` | `bolt://neo4j:7687` | Neo4j connection string |
| `NEO4J_USER` | `neo4j` | Neo4j username |
| `NEO4J_PASSWORD` | - | Neo4j password (**required**, min 8 chars) |
| `OPENAI_API_KEY` | - | OpenAI key for AI orchestrator |
| `OPENAI_MODEL` | `gpt-4o` | OpenAI model name |
| `ANTHROPIC_API_KEY` | - | Anthropic key for AI orchestrator |
| `ANTHROPIC_MODEL` | `claude-sonnet-4-20250514` | Anthropic model name |
| `OLLAMA_URL` | `http://ollama:11434` | Ollama endpoint |
| `OLLAMA_MODEL` | `llama3` | Ollama model name |
| `LLM_PROVIDER_PRIORITY` | `openai,anthropic,ollama` | LLM fallback order |
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

- **Non-root user**: Container runs as `blhackbox`, not root
- **No new privileges**: `security_opt: [no-new-privileges:true]` on all services
- **tmpfs**: `/tmp` mounted as `noexec,nosuid,size=256m`
- **Resource limits**: Memory 1G, CPU 1.0 for blhackbox; Memory 2G, CPU 2.0 for hexstrike/neo4j
- **Localhost-only ports**: All host port bindings use `127.0.0.1`
- **Healthchecks**: All services include Docker healthchecks for dependency ordering

---

## Volumes

When running with Docker Compose, these volumes are mounted:

| Path | Purpose |
|---|---|
| `/app/results` | Scan output and reports |
| `/app/wordlists` | Fuzzing wordlists (read-only) |
| `/app/blhackbox` | Source code (development live-reload) |

Named volumes for persistent data:

| Volume | Purpose |
|---|---|
| `hexstrike_data` | HexStrike application data |
| `neo4j_data` | Neo4j graph database |
| `neo4j_logs` | Neo4j logs |
| `ollama_data` | Ollama model storage |

---

## CI/CD Pipeline

Images are built and pushed automatically via GitHub Actions:

```
PR opened  ───>  CI (lint + test + pip-audit)
                      │
PR merged  ───>  CI  ───>  Build & Push  ───>  Docker Hub
                           (on CI success)
Tag v*     ──────────────>  Build & Push  ───>  Docker Hub

Manual     ──────────────>  Build & Push  ───>  Docker Hub
```

Tags pushed: `latest`, `x.y.z`, `x.y`, `main`, `<commit-sha>`

---

## Useful Commands

```bash
# Start the full stack
docker compose up -d

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
