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

Eleven custom images are published to `crhacky/blhackbox` on Docker Hub:

| Service | Tag | Dockerfile | Base |
|---|---|---|---|
| **Kali MCP** | `crhacky/blhackbox:kali-mcp` | `docker/kali-mcp.Dockerfile` | `kalilinux/kali-rolling` |
| **Metasploit MCP** | `crhacky/blhackbox:metasploit-mcp` | `docker/metasploit-mcp.Dockerfile` | `kalilinux/kali-rolling` |
| **WireMCP** | `crhacky/blhackbox:wire-mcp` | `docker/wire-mcp.Dockerfile` | `debian:bookworm-slim` |
| **Screenshot MCP** | `crhacky/blhackbox:screenshot-mcp` | `docker/screenshot-mcp.Dockerfile` | `python:3.13-slim` |
| **HexStrike** | `crhacky/blhackbox:hexstrike` | `docker/hexstrike.Dockerfile` | `python:3.13-slim-bookworm` |
| **HexStrike MCP** | `crhacky/blhackbox:hexstrike-mcp` | `docker/hexstrike-mcp.Dockerfile` | `python:3.13-slim` |
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
(container)   ├──> Metasploit MCP (SSE, port 9002)
              ├──> WireMCP (SSE, port 9003)
              ├──> Screenshot MCP (SSE, port 9004)
              ├──> HexStrike MCP (SSE, port 9005) ──> HexStrike API (REST, port 8888)
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
(host app)                                            └──> Ollama MCP
Note: HexStrike is a REST API, not routed through the MCP Gateway.
```

> **Ollama is required.** All 3 agent containers call Ollama via the official
> `ollama` Python package. Without it, the aggregation pipeline returns empty results.

---

## Usage

### Core Stack (12 containers)

```bash
git clone https://github.com/valITino/blhackbox.git
cd blhackbox
cp .env.example .env
# REQUIRED: Uncomment and set ANTHROPIC_API_KEY=sk-ant-... in .env
docker compose pull        # pull pre-built images (ollama + hexstrike-mcp build locally)
docker compose up -d       # start core stack
make ollama-pull           # pull the Ollama model (REQUIRED — default: llama3.1:8b)
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
| `kali-mcp` | `crhacky/blhackbox:kali-mcp` | `9001` | default | Kali Linux security tools (50+) |
| `metasploit-mcp` | `crhacky/blhackbox:metasploit-mcp` | `9002` | default | Metasploit Framework (13+ tools) |
| `wire-mcp` | `crhacky/blhackbox:wire-mcp` | `9003` | default | Wireshark/tshark (7 tools) |
| `screenshot-mcp` | `crhacky/blhackbox:screenshot-mcp` | `9004` | default | Screenshot MCP (headless Chromium, 4 tools) |
| `hexstrike` | `crhacky/blhackbox:hexstrike` | `8888` | default | HexStrike AI REST API (150+ tools) |
| `hexstrike-mcp` | `crhacky/blhackbox:hexstrike-mcp` | `9005` | default | HexStrike MCP adapter |
| `ollama-mcp` | `crhacky/blhackbox:ollama-mcp` | `9000` | default | Thin MCP orchestrator |
| `agent-ingestion` | `crhacky/blhackbox:agent-ingestion` | `8001` | default | Agent 1: parse raw output |
| `agent-processing` | `crhacky/blhackbox:agent-processing` | `8002` | default | Agent 2: deduplicate, compress |
| `agent-synthesis` | `crhacky/blhackbox:agent-synthesis` | `8003` | default | Agent 3: assemble payload |
| `ollama` | `crhacky/blhackbox:ollama` (built locally) | `11434` | default | LLM inference backend (llama3.1:8b) |
| `portainer` | `portainer/portainer-ce:latest` | `9443` | default | Docker management UI (HTTPS) |
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
    "metasploit":      { "type": "sse", "url": "http://metasploit-mcp:9002/sse" },
    "wireshark":       { "type": "sse", "url": "http://wire-mcp:9003/sse" },
    "screenshot":      { "type": "sse", "url": "http://screenshot-mcp:9004/sse" },
    "hexstrike":       { "type": "sse", "url": "http://hexstrike-mcp:9005/sse" },
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
| `NEO4J_URI` | `bolt://neo4j:7687` | Neo4j connection URI (optional) |
| `NEO4J_USER` | `neo4j` | Neo4j username (optional) |
| `NEO4J_PASSWORD` | - | Neo4j password, min 8 chars (optional) |
| `MSFRPC_USER` | `msf` | Metasploit RPC username |
| `MSFRPC_PASS` | `msf` | Metasploit RPC password |
| `SCREENSHOT_MCP_PORT` | `9004` | Screenshot MCP server port |
| `OPENAI_API_KEY` | - | For OpenAI MCP clients (optional) |

---

## Image Details

### Kali MCP (`crhacky/blhackbox:kali-mcp`)

- **Base**: `kalilinux/kali-rolling`
- **Tools (50+)**: nmap, masscan, hping3, subfinder, amass, fierce, dnsenum, dnsrecon, theharvester, nikto, gobuster, dirb, dirsearch, ffuf, feroxbuster, whatweb, wafw00f, wpscan, arjun, dalfox, sqlmap, hydra, medusa, john, hashcat, crackmapexec, evil-winrm, enum4linux-ng, responder, netexec, aircrack-ng, bettercap, binwalk, foremost, exiftool, steghide, curl, wget, netcat, socat, and more
- **Entrypoint**: Kali MCP server (`server.py`)
- **Transport**: SSE on port 9001
- **Privileged**: Yes (required for raw socket access)

### Metasploit MCP (`crhacky/blhackbox:metasploit-mcp`)

- **Base**: `kalilinux/kali-rolling` (includes `metasploit-framework`)
- **Tools (13+)**: list_exploits, list_payloads, run_exploit, run_auxiliary_module, run_post_module, generate_payload, list_sessions, send_session_command, terminate_session, list_listeners, start_listener, stop_job, msf_console_execute
- **Architecture**: FastMCP server connects to msfrpcd via MSF RPC
- **Entrypoint**: `entrypoint.sh` (starts msfrpcd + MCP server)
- **Transport**: SSE on port 9002
- **Privileged**: Yes (required for exploit execution)
- **Inspired by**: [GH05TCREW/MetasploitMCP](https://github.com/GH05TCREW/MetasploitMCP), [LYFTIUM-INC/msfconsole-mcp](https://github.com/LYFTIUM-INC/msfconsole-mcp)

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

### HexStrike (`crhacky/blhackbox:hexstrike`)

- **Base**: `python:3.13-slim-bookworm`
- **Entrypoint**: HexStrike Flask REST API server
- **Transport**: HTTP REST API on port 8888
- **Source**: [github.com/0x4m4/hexstrike-ai](https://github.com/0x4m4/hexstrike-ai)

### HexStrike MCP (`crhacky/blhackbox:hexstrike-mcp`)

- **Base**: `python:3.13-slim`
- **Role**: MCP adapter that bridges the HexStrike Flask REST API to MCP protocol
- **Transport**: SSE on port 9005
- **Depends on**: HexStrike container (calls `http://hexstrike:8888` internally)
- **Note**: Built locally — no pre-built Docker Hub image available yet

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

Eleven custom images are built and pushed to Docker Hub via GitHub Actions:

```
PR opened  ───>  CI (lint + test + pip-audit)
                      │
PR merged  ───>  CI  ───>  Build & Push (11 images)  ───>  Docker Hub
                           (on CI success)
Tag v*     ──────────────>  Build & Push (11 images)  ───>  Docker Hub

Manual     ──────────────>  Build & Push (11 images)  ───>  Docker Hub
```

Docker Scout vulnerability scanning runs on the ollama-mcp image.

---

## Useful Commands

```bash
# Pull all pre-built images from Docker Hub
docker compose pull

# Start core stack (12 containers)
docker compose up -d

# Start with MCP Gateway for Claude Desktop (13 containers)
make up-gateway

# Start with Neo4j (13 containers)
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
