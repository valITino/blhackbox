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

Eight custom images are published to `crhacky/blhackbox` on Docker Hub:

| Service | Tag | Dockerfile | Base |
|---|---|---|---|
| **Kali MCP** | `crhacky/blhackbox:kali-mcp` | `docker/kali-mcp.Dockerfile` | `kalilinux/kali-rolling` |
| **WireMCP** | `crhacky/blhackbox:wire-mcp` | `docker/wire-mcp.Dockerfile` | `debian:bookworm-slim` |
| **Screenshot MCP** | `crhacky/blhackbox:screenshot-mcp` | `docker/screenshot-mcp.Dockerfile` | `python:3.13-slim` |
| **Ollama MCP** | `crhacky/blhackbox:ollama-mcp` | `docker/ollama-mcp.Dockerfile` | `python:3.13-slim` |
| **Agent: Ingestion** | `crhacky/blhackbox:agent-ingestion` | `docker/agent-ingestion.Dockerfile` | `python:3.13-slim` |
| **Agent: Processing** | `crhacky/blhackbox:agent-processing` | `docker/agent-processing.Dockerfile` | `python:3.13-slim` |
| **Agent: Synthesis** | `crhacky/blhackbox:agent-synthesis` | `docker/agent-synthesis.Dockerfile` | `python:3.13-slim` |
| **Claude Code** | `crhacky/blhackbox:claude-code` | `docker/claude-code.Dockerfile` | `node:22-slim` |

Custom-built locally (no pre-built image on Docker Hub):
- `crhacky/blhackbox:ollama` — wraps `ollama/ollama:latest` with auto-pull entrypoint (`docker/ollama.Dockerfile`)

Official images pulled directly (no custom build):
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
(container)   │    70+ tools: nmap, sqlmap, hydra, msfconsole, msfvenom, etc.
              ├──> WireMCP (SSE, port 9003)
              ├──> Screenshot MCP (SSE, port 9004)
              │
              │  After collecting raw outputs, Claude structures them directly:
              │    get_payload_schema() → parse/dedup/correlate → aggregate_results()
              │
              └──> (optional) Ollama MCP (SSE, port 9000)
                        │
                        ├──► agent-ingestion:8001
                        ├──► agent-processing:8002
                        └──► agent-synthesis:8003
                                  │
                                  ▼
                               Ollama (LLM backend)

output/          Host-mounted directory for reports, screenshots, sessions
Portainer        Docker UI (https://localhost:9443)
Neo4j            Cross-session memory (optional)
```

**Claude Desktop / ChatGPT (host)** connect via the MCP Gateway:

```
Claude Desktop ──> MCP Gateway (localhost:8080/mcp) ──┬──> Kali MCP
(host app)                                            ├──> WireMCP
                                                      └──> Screenshot MCP
```

> **Ollama is optional since v2.1.** The MCP host (Claude) now handles data
> aggregation directly. The Ollama pipeline is kept as an optional fallback
> for local-only / offline processing. Enable with `--profile ollama`.

---

## Usage

### Quick Start (Recommended)

```bash
git clone https://github.com/valITino/blhackbox.git
cd blhackbox
./setup.sh                 # interactive wizard: prereqs, .env, pull, start, health
```

### Manual — Core Stack (4 containers)

```bash
git clone https://github.com/valITino/blhackbox.git
cd blhackbox
cp .env.example .env
# REQUIRED: Uncomment and set ANTHROPIC_API_KEY=sk-ant-... in .env
mkdir -p output/reports output/screenshots output/sessions
docker compose pull
docker compose up -d
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
| `kali-mcp` | `crhacky/blhackbox:kali-mcp` | `9001` | default | Kali Linux security tools + Metasploit (70+) |
| `wire-mcp` | `crhacky/blhackbox:wire-mcp` | `9003` | default | Wireshark/tshark (7 tools) |
| `screenshot-mcp` | `crhacky/blhackbox:screenshot-mcp` | `9004` | default | Screenshot MCP (headless Chromium, 4 tools) |
| `portainer` | `portainer/portainer-ce:latest` | `9443` | default | Docker management UI (HTTPS) |
| `claude-code` | `crhacky/blhackbox:claude-code` | - | `claude-code` | Claude Code CLI client (Docker) |
| `mcp-gateway` | `docker/mcp-gateway:latest` | `8080` | `gateway` | Single MCP entry point (host clients) |
| `neo4j` | `neo4j:5` | `7474` `7687` | `neo4j` | Cross-session knowledge graph |
| `ollama-mcp` | `crhacky/blhackbox:ollama-mcp` | `9000` | `ollama` | Thin MCP orchestrator (optional) |
| `agent-ingestion` | `crhacky/blhackbox:agent-ingestion` | `8001` | `ollama` | Agent 1: parse raw output (optional) |
| `agent-processing` | `crhacky/blhackbox:agent-processing` | `8002` | `ollama` | Agent 2: deduplicate, compress (optional) |
| `agent-synthesis` | `crhacky/blhackbox:agent-synthesis` | `8003` | `ollama` | Agent 3: assemble payload (optional) |
| `ollama` | `crhacky/blhackbox:ollama` (built locally) | `11434` | `ollama` | LLM inference backend (optional) |

---

## MCP Connection Modes

### Claude Code in Docker (Direct SSE — no gateway)

The Claude Code container's `.mcp.json` connects directly to each server:

```json
{
  "mcpServers": {
    "kali":            { "type": "sse", "url": "http://kali-mcp:9001/sse" },
    "wireshark":       { "type": "sse", "url": "http://kali-mcp:9003/sse" },
    "screenshot":      { "type": "sse", "url": "http://screenshot-mcp:9004/sse" },
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
| `OLLAMA_MODEL` | `llama3.1:8b` | Ollama model for preprocessing agents |
| `MCP_GATEWAY_PORT` | `8080` | MCP Gateway host port (optional) |
| `MSF_TIMEOUT` | `300` | Metasploit command timeout in seconds |
| `NEO4J_URI` | `bolt://neo4j:7687` | Neo4j connection URI (optional) |
| `NEO4J_USER` | `neo4j` | Neo4j username (optional) |
| `NEO4J_PASSWORD` | - | Neo4j password, min 8 chars (optional) |
| `SCREENSHOT_MCP_PORT` | `9004` | Screenshot MCP server port |
| `OPENAI_API_KEY` | - | For OpenAI MCP clients (optional) |

---

## Image Details

### Kali MCP (`crhacky/blhackbox:kali-mcp`)

- **Base**: `kalilinux/kali-rolling`
- **Tools (70+)**: nmap, masscan, hping3, subfinder, amass, fierce, dnsenum, dnsrecon, theharvester, nikto, gobuster, dirb, dirsearch, ffuf, feroxbuster, whatweb, wafw00f, wpscan, arjun, dalfox, sqlmap, hydra, medusa, john, hashcat, crackmapexec, evil-winrm, enum4linux-ng, responder, netexec, aircrack-ng, bettercap, binwalk, foremost, exiftool, steghide, curl, wget, netcat, socat, **msfconsole**, **msfvenom**, and more
- **Metasploit**: Integrated via CLI (`msfconsole -qx`) — no msfrpcd daemon needed. Includes PostgreSQL for Metasploit DB support.
- **MCP Tools**: `run_kali_tool`, `run_shell_command`, `list_available_tools`, `msf_search`, `msf_module_info`, `msf_run_module`, `msf_payload_generate`, `msf_console_execute`, `msf_status`
- **Entrypoint**: `entrypoint.sh` (starts PostgreSQL for MSF DB, then MCP server)
- **Transport**: SSE on port 9001
- **Privileged**: Yes (required for raw socket access)

### WireMCP (`crhacky/blhackbox:wire-mcp`)

- **Base**: `debian:bookworm-slim`
- **Tools (7)**: capture_packets, read_pcap, get_conversations, get_statistics, extract_credentials, follow_stream, list_interfaces
- **Entrypoint**: WireMCP server (`server.py`)
- **Transport**: SSE on port 9003
- **Privileged**: Yes (required for packet capture)
- **Inspired by**: [0xKoda/WireMCP](https://github.com/0xKoda/WireMCP), [khuynh22/mcp-wireshark](https://github.com/khuynh22/mcp-wireshark)

### Screenshot MCP (`crhacky/blhackbox:screenshot-mcp`)

- **Base**: `python:3.13-slim`
- **Tools (4)**: take_screenshot (full-page web capture), take_element_screenshot (CSS selector targeting), annotate_screenshot (labels and highlight boxes), list_screenshots (evidence inventory)
- **Entrypoint**: Screenshot MCP server (FastMCP + Playwright headless Chromium)
- **Transport**: SSE on port 9004

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
| `ollama_models` | ollama | Ollama model storage (optional) |
| `neo4j_data` | neo4j | Neo4j graph database (optional) |
| `neo4j_logs` | neo4j | Neo4j logs (optional) |
| `portainer_data` | portainer | Portainer configuration |
| `wordlists` | - | Fuzzing wordlists |

Host bind mounts for output (accessible on your local filesystem):

| Host Path | Container Path | Purpose |
|---|---|---|
| `./output/reports/` | `/root/reports/` | Generated pentest reports (.md, .pdf) |
| `./output/screenshots/` | `/tmp/screenshots/` | PoC evidence screenshots (.png) |
| `./output/sessions/` | `/root/results/` | Aggregated session JSON files |

---

## CI/CD Pipeline

Eight custom images are built and pushed to Docker Hub via GitHub Actions:

```
PR opened  ───>  CI (lint + test + pip-audit)
                      │
PR merged  ───>  CI  ───>  Build & Push (8 images)  ───>  Docker Hub
                           (on CI success)
Tag v*     ──────────────>  Build & Push (8 images)  ───>  Docker Hub

Manual     ──────────────>  Build & Push (8 images)  ───>  Docker Hub
```

Docker Scout vulnerability scanning runs on the ollama-mcp image.

---

## Useful Commands

```bash
# Interactive setup wizard (recommended for first-time setup)
make setup

# Pull all pre-built images from Docker Hub
docker compose pull

# Start core stack (4 containers)
docker compose up -d

# Start with MCP Gateway for Claude Desktop (5 containers)
make up-gateway

# Start with Neo4j (5 containers)
docker compose --profile neo4j up -d

# Start with Ollama pipeline (9 containers, optional)
docker compose --profile ollama up -d

# Launch Claude Code in Docker
make claude-code

# Pull the Ollama model (only if using --profile ollama)
make ollama-pull

# Check health of all MCP servers
make health

# Container status
make status

# View service logs
make logs-kali
make logs-wireshark
make logs-screenshot
make gateway-logs

# Stop and clean up
make down
make clean                 # also removes volumes
```

---

## GPU Support

GPU acceleration is **disabled by default** for broad compatibility. Ollama runs
on CPU out of the box.

If you have an NVIDIA GPU, uncomment the `deploy` block under the `ollama`
service in `docker-compose.yml` and install the
[NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html)
on the host. GPU acceleration significantly speeds up Ollama inference.

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
