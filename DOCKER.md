# crhacky/blhackbox

**Autonomous pentesting framework powered by HexStrike AI**

---

## Quick Reference

| | |
|---|---|
| **Image** | `crhacky/blhackbox` |
| **Registry** | [Docker Hub](https://hub.docker.com/r/crhacky/blhackbox) |
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

Blhackbox is an intelligent orchestration layer for [HexStrike AI](https://github.com/0x4m4/hexstrike-ai). It adds autonomous planning, a persistent knowledge graph, and professional reporting to HexStrike's 150+ security tools and 12+ AI agents.

```
                  ┌──────────────────────────────┐
                  │       Blhackbox Layer         │
                  │                               │
  CLI / AI ──────▶│  Orchestrator  ─▶  Planner    │
                  │       │                       │
                  │       ▼                       │
                  │  Knowledge Graph (Neo4j)      │
                  │       │                       │
                  │       ▼                       │
                  │  HexStrike API Client         │
                  └───────┬───────────────────────┘
                          ▼
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
git clone https://github.com/your-org/blhackbox.git
cd blhackbox
cp .env.example .env    # configure API keys
docker compose up -d
docker compose exec blhackbox blhackbox recon --target example.com --authorized
```

### Compose Services

| Service | Image | Port | Role |
|---|---|---|---|
| `blhackbox` | Built from repo | - | Orchestration & CLI |
| `hexstrike` | Built from submodule | `8888` | MCP tool server |
| `neo4j` | `neo4j:5-community` | `7474` `7687` | Knowledge graph |
| `ollama` | `ollama/ollama` | `11434` | Local LLM (optional) |

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
| `NEO4J_URI` | `bolt://neo4j:7687` | Neo4j connection string |
| `NEO4J_USER` | `neo4j` | Neo4j username |
| `NEO4J_PASSWORD` | - | Neo4j password (required) |
| `OPENAI_API_KEY` | - | OpenAI key for AI orchestrator |
| `ANTHROPIC_API_KEY` | - | Anthropic key for AI orchestrator |
| `OLLAMA_URL` | `http://ollama:11434` | Ollama endpoint |
| `LLM_PROVIDER_PRIORITY` | `openai,anthropic,ollama` | LLM fallback order |
| `LOG_LEVEL` | `INFO` | Logging verbosity |

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

---

## Volumes

When running with Docker Compose, mount these for persistence:

| Path | Purpose |
|---|---|
| `/app/results` | Scan output and reports |
| `/app/wordlists` | Fuzzing wordlists |
| `/app/blhackbox` | Source code (dev mode live-reload) |

---

## CI/CD Pipeline

Images are built and pushed automatically:

```
PR opened  ──▶  CI (lint + test)
                     │
PR merged  ──▶  CI  ──▶  Build & Push  ──▶  Docker Hub
                          (on CI success)
Tag v*     ──────────────▶  Build & Push  ──▶  Docker Hub

Manual     ──────────────▶  Build & Push  ──▶  Docker Hub
```

---

## Security

- All scanning commands require the `--authorized` flag
- Container runs as non-root user
- LLM safety prompts prevent exploit generation
- Scope enforcement in the AI orchestrator

**This tool is for authorized security testing only.** Unauthorized access to computer systems is illegal.

---

## Source

[GitHub Repository](https://github.com/your-org/blhackbox)
