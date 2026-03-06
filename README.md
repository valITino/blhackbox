# BLHACKBOX v2.0.0

[![CI](https://github.com/valITino/blhackbox/actions/workflows/ci.yml/badge.svg)](https://github.com/valITino/blhackbox/actions/workflows/ci.yml)
[![Docker](https://github.com/valITino/blhackbox/actions/workflows/build-and-push.yml/badge.svg)](https://github.com/valITino/blhackbox/actions/workflows/build-and-push.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Docker Hub](https://img.shields.io/docker/v/crhacky/blhackbox?label=Docker%20Hub&sort=semver)](https://hub.docker.com/r/crhacky/blhackbox)

**MCP-based Autonomous Pentesting Framework**

> **LEGAL DISCLAIMER:** This tool is for **authorized security testing only**.
> You must have explicit written permission from the target owner before running
> any scans. Unauthorized testing is illegal.

---

## Table of Contents

- [How It Works](#how-it-works)
- [Architecture](#architecture)
- [Components](#components)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Tutorial 1: Claude Code (Docker) — Recommended](#tutorial-1-claude-code-docker--recommended)
- [Tutorial 2: Claude Code (Web)](#tutorial-2-claude-code-web)
- [Tutorial 3: Claude Desktop (Host + Gateway)](#tutorial-3-claude-desktop-host--gateway)
- [Tutorial 4: ChatGPT / OpenAI (Host + Gateway)](#tutorial-4-chatgpt--openai-host--gateway)
- [How Prompts Flow Through the System](#how-prompts-flow-through-the-system)
- [Do I Need the MCP Gateway?](#do-i-need-the-mcp-gateway)
- [Portainer Setup](#portainer-setup)
- [Ollama Preprocessing Pipeline](#ollama-mcp-server--preprocessing-pipeline)
- [Troubleshooting](#troubleshooting)
- [CLI Reference](#cli-reference)
- [Makefile Shortcuts](#makefile-shortcuts)
- [Docker Hub Images](#docker-hub-images)
- [Neo4j (Optional)](#neo4j-optional)
- [GPU Support for Ollama](#gpu-support-for-ollama)
- [Security Notes](#security-notes)
- [Project Structure](#project-structure)
- [License](#license)

---

## How It Works

In v2, **your AI client (Claude or ChatGPT) IS the orchestrator**. There is no
internal LangGraph orchestrator or LLM planner. Here is what happens when you
type a prompt:

1. **You type a prompt** in your AI client (Claude Code, Claude Desktop, or ChatGPT).
2. **The AI decides which tools to call** from four MCP servers: Kali Linux MCP (70+ security tools including Metasploit), WireMCP (7 packet analysis tools), Screenshot MCP (4 evidence capture tools), and the Ollama preprocessing pipeline.
3. **Each MCP server executes the tool call** in its Docker container and returns raw output to the AI.
4. **The AI collects all raw outputs** and sends them to the Ollama MCP server via `process_scan_results()`.
5. **Ollama preprocesses the data** through 3 agent containers in sequence (Ingestion -> Processing -> Synthesis), each calling the local Ollama LLM independently.
6. **The structured `AggregatedPayload` returns to the AI**, which writes the final pentest report.

Everything runs inside Docker containers. No tools are installed on your host machine.

---

## Architecture

Claude Code in Docker connects **directly** to each MCP server via SSE over
the internal Docker network. No MCP Gateway needed.

```
YOU (the user)
  |
  |  "docker compose run --rm claude-code" (or attach via Portainer)
  |
  v
CLAUDE CODE (Docker container on blhackbox_net)
  |
  |  Reads your prompt, decides which tools to call.
  |  Connects directly to each MCP server via SSE.
  |
  |--- kali (SSE, port 9001) ─────────────>  KALI MCP SERVER
  |                                            70+ tools: nmap, nikto, gobuster,
  |                                            sqlmap, hydra, msfconsole, msfvenom,
  |                                            john, hashcat, etc.
  |
  |--- wireshark (SSE, port 9003) ────────>  WIREMCP SERVER
  |                                            7 tools: packet capture, pcap
  |                                            analysis, credential extraction
  |
  |--- screenshot (SSE, port 9004) ──────>  SCREENSHOT MCP SERVER
  |                                            4 tools: web page screenshots,
  |                                            element capture, annotations
  |
  |--- ollama-pipeline (SSE, port 9000) ───>  OLLAMA MCP SERVER
                                               |
                                               |  Calls 3 agents in sequence:
                                               |
                                               |---> INGESTION  (port 8001)
                                               |     Calls Ollama -> structured data
                                               |
                                               |---> PROCESSING (port 8002)
                                               |     Calls Ollama -> deduplicated
                                               |
                                               |---> SYNTHESIS  (port 8003)
                                                     Calls Ollama -> AggregatedPayload
                                               |
                                               v
                                         AggregatedPayload -> back to Claude Code
                                               |
                                               v
                                         AI writes final pentest report
                                               |
                                               v (optional)
                                             NEO4J — cross-session memory

PORTAINER (https://localhost:9443) — Web UI for all containers
```

For host-based clients (Claude Desktop, ChatGPT), an **optional MCP Gateway**
aggregates all servers behind `localhost:8080/mcp`. See
[Do I Need the MCP Gateway?](#do-i-need-the-mcp-gateway).

---

## Components

| Container | What it does | Internal Port | Default Profile |
|-----------|-------------|:---:|:---:|
| **Kali MCP** | Kali Linux security tools + Metasploit Framework — 70+ tools (nmap, sqlmap, hydra, msfconsole, msfvenom, etc.) | 9001 | default |
| **WireMCP** | Wireshark/tshark — 7 packet capture and analysis tools | 9003 | default |
| **Screenshot MCP** | Headless Chromium — 4 screenshot and annotation tools | 9004 | default |
| **Ollama MCP** | Thin orchestrator — calls 3 agent containers in sequence | 9000 | default |
| **Agent: Ingestion** | Parses raw tool output into structured typed data | 8001 | default |
| **Agent: Processing** | Deduplicates, compresses, annotates errors | 8002 | default |
| **Agent: Synthesis** | Merges into final `AggregatedPayload` | 8003 | default |
| **Ollama** | Local LLM inference backend (llama3.1:8b by default) | 11434 | default |
| **Portainer** | Web UI for managing all containers | 9443 | default |
| **Claude Code** | Anthropic CLI MCP client in Docker | — | `claude-code` |
| **MCP Gateway** | Single entry point for host-based MCP clients | 8080 | `gateway` |
| **Neo4j** | Cross-session knowledge graph | 7474/7687 | `neo4j` |

---

## Prerequisites

- **Docker** and **Docker Compose** (Docker Engine on Linux, or Docker Desktop)
- At least **16 GB RAM** recommended (Ollama + all containers). The default model (`llama3.1:8b`) requires ~8 GB; larger models need more.
- An **Anthropic API key** from [console.anthropic.com](https://console.anthropic.com) (**required** for Claude Code)
- **NVIDIA Container Toolkit** (optional — for GPU-accelerated Ollama inference. See [GPU Support](#gpu-support-for-ollama))

---

## Installation

```bash
# 1. Clone the repo
git clone https://github.com/valITino/blhackbox.git
cd blhackbox

# 2. Create your .env file
cp .env.example .env
# REQUIRED: Uncomment and set your Anthropic API key in .env:
#   ANTHROPIC_API_KEY=sk-ant-...
# Without this, the Claude Code container cannot start.

# 3. Pull all pre-built Docker images
docker compose pull
# NOTE: The ollama image is built locally — this is normal.
# Docker Compose will build it automatically in the next step.

# 4. Start the core stack (9 containers)
docker compose up -d

# 5. Download the Ollama model (required — runs inside the container)
make ollama-pull
# This pulls llama3.1:8b (~4.7 GB download). First run may take several minutes.
```

**Verify everything is running:**

```bash
make status     # Container status
make health     # Quick health check of all MCP servers
```

You should see 9 containers, all "Up" or "healthy":
- `blhackbox-kali-mcp`
- `blhackbox-wire-mcp`
- `blhackbox-screenshot-mcp`
- `blhackbox-ollama-mcp`
- `blhackbox-agent-ingestion`
- `blhackbox-agent-processing`
- `blhackbox-agent-synthesis`
- `blhackbox-ollama`
- `blhackbox-portainer`

> **First time?** Open Portainer at `https://localhost:9443` and create an admin
> account within 5 minutes. See [Portainer Setup](#portainer-setup).

---

## Tutorial 1: Claude Code (Docker) — Recommended

Claude Code runs entirely inside a Docker container on the same network as all
other blhackbox services. It connects **directly** to each MCP server via SSE —
no MCP Gateway, no host install, no Node.js.

### Step 1: Start the stack

Follow [Installation](#installation) above. Make sure `ANTHROPIC_API_KEY` is
set in your `.env` file. All 9 containers must be healthy (`make health`).

### Step 2: Launch Claude Code

```bash
make claude-code
```

Or manually:

```bash
docker compose --profile claude-code run --rm claude-code
```

The entrypoint script checks each service and shows a status dashboard:

```
  ╔══════════════════════════════════════════════╗
  ║          blhackbox v2.0 — Claude Code       ║
  ║        MCP-based Pentesting Framework       ║
  ╚══════════════════════════════════════════════╝

Checking service connectivity...

  MCP Servers
  Kali MCP               [ OK ]
  WireMCP                [ OK ]
  Screenshot MCP         [ OK ]
  Ollama Pipeline        [ OK ]

──────────────────────────────────────────────────
  All 4 services connected.

  MCP servers (connected via SSE):
    kali            Kali Linux security tools + Metasploit (70+ tools)
    wireshark       WireMCP — tshark packet capture & analysis
    screenshot      Screenshot MCP — headless Chromium evidence capture
    ollama-pipeline Ollama preprocessing (3-agent pipeline)

  Quick start:
    /mcp              Check MCP server status
    Scan example.com for open ports and web vulnerabilities
──────────────────────────────────────────────────
```

You are now inside an interactive Claude Code session.

### Step 3: Verify the connection

```
/mcp
```

You should see the MCP servers listed: `kali`, `wireshark`,
`screenshot`, and `ollama-pipeline`, each with their available tools.

### Step 4: Run your first pentest

```
Scan example.com for open ports and web vulnerabilities
```

Claude Code will autonomously:
1. Call Kali tools (nmap, subfinder, nikto, etc.)
2. Search for exploits using Metasploit (`msf_search`)
3. Collect raw outputs from all tools
4. Send them to the Ollama preprocessing pipeline
5. Write a structured pentest report

### Monitoring (separate terminal)

```bash
make logs-kali             # Kali MCP server activity (includes Metasploit)
make logs-wireshark        # WireMCP activity
make logs-screenshot       # Screenshot MCP activity
make logs-ollama-mcp       # Ollama MCP server activity
make logs-agent-ingestion  # Ingestion Agent processing
make logs-agent-synthesis  # Synthesis Agent building payload
```

Or use **Portainer** at `https://localhost:9443` to see all container logs and
resource usage in one dashboard.

---

## Tutorial 2: Claude Code (Web)

Claude Code on [claude.ai/code](https://claude.ai/code) works as a web-based
coding agent. When you open this repo in a web session, the MCP server
configures itself automatically.

### How it works

1. **`.mcp.json`** (project root) — tells Claude Code to start the blhackbox
   MCP server via stdio
2. **`.claude/hooks/session-start.sh`** — auto-installs dependencies on session start

### Steps

1. Go to [claude.ai/code](https://claude.ai/code) and open this repository
2. Type `/mcp` to verify — you should see `blhackbox` with 6 tools
3. Type your prompt: `Scan example.com for open ports and web vulnerabilities`

> **Note:** The web session uses the blhackbox stdio MCP server directly
> (not the Docker stack). For the full Docker pipeline with Kali tools,
> Metasploit, and Ollama preprocessing, use [Tutorial 1](#tutorial-1-claude-code-docker--recommended).

---

## Tutorial 3: Claude Desktop (Host + Gateway)

Claude Desktop is a GUI app that cannot run in Docker. It connects to blhackbox
via the **MCP Gateway** on `localhost:8080`.

### Step 1: Start the stack with the gateway

```bash
docker compose up -d                          # core stack
docker compose --profile gateway up -d        # adds the MCP Gateway
# OR shortcut:
make up-gateway
```

### Step 2: Configure Claude Desktop

Open the config file:

- **macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`
- **Linux:** `~/.config/Claude/claude_desktop_config.json`

Add:

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

Restart Claude Desktop. You should see a hammer icon with available tools.

### Step 3: Run a pentest

Type your prompt in Claude Desktop. The flow is identical to Tutorial 1 — the
gateway routes tool calls to the same MCP servers (kali, wireshark, screenshot, ollama).

---

## Tutorial 4: ChatGPT / OpenAI (Host + Gateway)

ChatGPT/OpenAI clients also connect via the **MCP Gateway** on `localhost:8080`.

### Step 1: Start with gateway

```bash
make up-gateway
```

### Step 2: Configure your client

Point your MCP-capable OpenAI client at:

```
URL: http://localhost:8080/mcp
Transport: Streamable HTTP
```

The gateway is AI-agnostic — it serves the same tools to any MCP client.

---

## How Prompts Flow Through the System

```
STEP 1: YOU TYPE A PROMPT
  "Scan example.com for open ports and web vulnerabilities"
        |
        v
STEP 2: AI DECIDES WHICH TOOLS TO USE
  Claude picks tools from Kali MCP (includes Metasploit), WireMCP, and Screenshot MCP:
    - subfinder (Kali)           -> find subdomains
    - nmap -sV -sC (Kali)       -> port scan + service detection
    - nikto (Kali)               -> web server scanning
    - msf_search (Kali/MSF)      -> find matching exploits
    - capture_packets (WireMCP)  -> capture traffic during scanning
        |
        v
STEP 3: TOOLS EXECUTE IN DOCKER CONTAINERS
  Claude Code (Docker) connects directly via SSE.
  Claude Desktop / ChatGPT connect via the MCP Gateway.
  Each tool runs in its container and returns raw text.
        |
        v
STEP 4: AI SENDS RAW OUTPUTS TO OLLAMA FOR PROCESSING
  After collecting all raw outputs, the AI calls:
    process_scan_results(raw_outputs)
  on the Ollama MCP Server.
        |
        v
STEP 5: OLLAMA PIPELINE (3 AGENTS IN SEQUENCE)
  Agent 1: INGESTION (port 8001)
    Calls Ollama -> structured typed data
        |
        v
  Agent 2: PROCESSING (port 8002)
    Calls Ollama -> deduplicated + compressed
        |
        v
  Agent 3: SYNTHESIS (port 8003)
    Calls Ollama -> final AggregatedPayload
        |
        v
STEP 6: AI WRITES THE FINAL REPORT
  Executive summary, findings by severity, remediation, appendix.
        |
        v
STEP 7 (OPTIONAL): RESULTS STORED IN NEO4J
  Cross-session memory for recurring engagements.
```

---

## Do I Need the MCP Gateway?

| MCP Client | Gateway needed? | How it connects |
|------------|:---:|---|
| **Claude Code (Docker)** | **No** | Connects directly to each MCP server via SSE over Docker network |
| **Claude Code (Web)** | **No** | Uses stdio MCP server from `.mcp.json` |
| **Claude Desktop** | **Yes** | GUI app on host; needs `localhost:8080/mcp` gateway |
| **ChatGPT / OpenAI** | **Yes** | GUI/web app on host; needs `localhost:8080/mcp` gateway |

The MCP Gateway (`docker/mcp-gateway:latest`) aggregates all MCP servers
(kali, wireshark, screenshot, ollama) behind a single Streamable
HTTP endpoint at `localhost:8080/mcp`. It requires:
- Docker socket mount (`/var/run/docker.sock`)
- The `--profile gateway` flag to enable

Start the gateway only when you need it:

```bash
make up-gateway   # starts core stack + gateway
```

> **Why is it optional?** The gateway adds complexity, requires Docker socket
> access, and is designed primarily for Docker Desktop environments. On headless
> Linux servers, connecting directly via SSE is simpler and more reliable.

---

## Portainer Setup

Portainer CE provides a web UI for managing all blhackbox containers.

**URL:** `https://localhost:9443`

### First Run

On first launch, Portainer requires you to create an admin account **within 5
minutes**. If you miss the window:

```bash
docker compose restart portainer
```

Then open `https://localhost:9443` again and create your account.

### What you can do in Portainer

- View all container status, logs, and resource usage
- Restart individual containers
- Inspect environment variables and network configuration
- Monitor the health of each service

> **Note:** Your browser will warn about the self-signed HTTPS certificate.
> This is expected — click "Advanced" and proceed.

---

## Ollama MCP Server — Preprocessing Pipeline

The Ollama MCP Server is a thin orchestrator built with
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

---

## Troubleshooting

### Claude Code shows "Status: failed" for MCP servers

The MCP servers may not be healthy yet. Check with:

```bash
make health           # quick health check from host
make status           # container status
docker compose logs   # full logs
```

If a service shows `FAIL`, restart it:

```bash
docker compose restart kali-mcp        # restart one service
make restart-agents                    # restart all 3 agents
```

### Metasploit tools are slow or fail

Metasploit tools (`msf_search`, `msf_run_module`, etc.) use `msfconsole -qx`
for CLI execution. The first invocation takes **10-30 seconds** due to Ruby and
database initialization (cold start). Subsequent calls in the same container
session are faster.

If Metasploit commands fail:
1. Check if msfconsole is installed: `docker exec blhackbox-kali-mcp which msfconsole`
2. Check database status: use the `msf_status` tool
3. Check container logs: `make logs-kali`

### Portainer shows "Timeout" on first visit

You have 5 minutes after Portainer starts to create an admin account. If you
missed it, restart:

```bash
docker compose restart portainer
```

### Ollama model not pulled

The agents need a model loaded in Ollama. Without it, the preprocessing pipeline
returns empty results:

```bash
make ollama-pull     # pulls the model specified in .env (default: llama3.1:8b)
```

If the model fails to load with an "out of memory" error, your system doesn't
have enough RAM for the configured model. Try a smaller model:

```bash
# Edit .env and change OLLAMA_MODEL to a smaller model:
OLLAMA_MODEL=llama3.2:3b
# Then re-pull:
make ollama-pull
```

### MCP Gateway doesn't start

The gateway is **optional** — Claude Code in Docker does not use it. If you
need it for Claude Desktop / ChatGPT:

1. Ensure Docker socket exists: `ls -la /var/run/docker.sock`
2. Start with the gateway profile: `make up-gateway`
3. Check logs: `make gateway-logs`

### NVIDIA GPU errors on startup

GPU acceleration is disabled by default. If you enabled it by uncommenting the
`deploy` block and see errors, ensure the
[NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html)
is installed. See [GPU Support](#gpu-support-for-ollama).

### Container keeps restarting

Check its logs for the specific error:

```bash
docker compose logs <service-name>     # e.g., kali-mcp, ollama-mcp
```

Common causes:
- Missing Ollama model (agents can't start processing)
- Port conflict on the host
- Insufficient memory (increase to 16GB+)

---

## CLI Reference

```bash
# Show version and config
blhackbox version

# Run recon
blhackbox recon --target example.com
blhackbox recon --target example.com --attacks nmap,subfinder
blhackbox recon --target example.com --full

# Run a single tool
blhackbox run-tool -c network -t nmap -p '{"target":"example.com"}'
# Knowledge graph (requires Neo4j)
blhackbox graph query "MATCH (n) RETURN n LIMIT 10"
blhackbox graph summary -t example.com

# Generate reports
blhackbox report -s SESSION_ID --format pdf

# Start MCP server
blhackbox mcp
```

---

## Makefile Shortcuts

```bash
make help                  # Show all available targets
make pull                  # Pull all pre-built images from Docker Hub
make up                    # Start core stack (9 containers)
make up-full               # Start with Neo4j (10 containers)
make up-gateway            # Start with MCP Gateway for Claude Desktop (10 containers)
make down                  # Stop all services
make claude-code           # Build and launch Claude Code in Docker
make status                # Container status table
make health                # Quick health check of all MCP servers
make test                  # Run tests
make lint                  # Run linter
make ollama-pull           # Pull Ollama model
make portainer             # Open Portainer dashboard (shows setup instructions)
make gateway-logs          # Live MCP Gateway logs (requires --profile gateway)
make restart-agents        # Restart all 3 agent containers
make logs-kali             # Tail Kali MCP logs (includes Metasploit)
make logs-wireshark        # Tail WireMCP logs
make logs-screenshot       # Tail Screenshot MCP logs
make logs-ollama-mcp       # Tail Ollama MCP logs
make logs-agent-ingestion  # Tail Ingestion Agent logs
make logs-agent-processing # Tail Processing Agent logs
make logs-agent-synthesis  # Tail Synthesis Agent logs
make push-all              # Build and push all images to Docker Hub
```

---

## Build from Source (optional)

Only needed if you want to modify Dockerfiles or agent code:

```bash
git submodule update --init --recursive   # fetch kali-mcp source
docker compose build                      # build all custom images locally
docker compose up -d
```

---

## Docker Hub Images

All custom images are published to `crhacky/blhackbox`:

| Tag | Description |
|-----|-------------|
| `crhacky/blhackbox:kali-mcp` | Kali Linux MCP Server (70+ tools + Metasploit Framework) |
| `crhacky/blhackbox:wire-mcp` | WireMCP Server (tshark, 7 tools) |
| `crhacky/blhackbox:screenshot-mcp` | Screenshot MCP Server (headless Chromium, 4 tools) |
| `crhacky/blhackbox:ollama-mcp` | Ollama MCP Server (thin orchestrator) |
| `crhacky/blhackbox:agent-ingestion` | Agent 1: Ingestion |
| `crhacky/blhackbox:agent-processing` | Agent 2: Processing |
| `crhacky/blhackbox:agent-synthesis` | Agent 3: Synthesis |
| `crhacky/blhackbox:claude-code` | Claude Code CLI client (direct SSE to MCP servers) |

Custom-built locally (no pre-built image on Docker Hub):
- `crhacky/blhackbox:ollama` (wraps `ollama/ollama:latest` with auto-pull entrypoint)

Official images pulled directly:
- `portainer/portainer-ce:latest`
- `neo4j:5` (optional)
- `docker/mcp-gateway:latest` (optional)

---

## Neo4j (Optional)

Neo4j provides cross-session memory. Enable with `--profile neo4j`:

```bash
docker compose --profile neo4j up -d
```

Stores `AggregatedPayload` results as a graph after each session.
Useful for recurring engagements against the same targets.

---

## GPU Support for Ollama

GPU acceleration is **disabled by default** in `docker-compose.yml` for broad
compatibility. Ollama runs on CPU out of the box.

**If you have an NVIDIA GPU**, uncomment the `deploy` block under the `ollama`
service in `docker-compose.yml` to enable GPU acceleration:

```yaml
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: all
              capabilities: [gpu]
```

This requires the
[NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html)
to be installed on the host. GPU acceleration significantly speeds up Ollama
inference for the preprocessing pipeline.

---

## Security Notes

- **Docker socket**: MCP Gateway (optional) and Portainer mount
  `/var/run/docker.sock`. This grants effective root on the host. Never expose
  ports 8080 or 9443 to the public internet.
- **Authorization**: Ensure you have written permission before scanning any target.
- **Neo4j**: Set a strong password in `.env`. Never use defaults in production.
- **Agent containers**: Communicate only on the internal `blhackbox_net` Docker
  network. No ports are exposed to the host.
- **Portainer**: Uses HTTPS with a self-signed certificate. Create a strong
  admin password on first run.

---

## Project Structure

```
blhackbox/
├── .claude/
│   ├── settings.json               # Claude Code hooks config
│   └── hooks/
│       └── session-start.sh        # auto-setup for web sessions
├── .mcp.json                        # MCP server config (Claude Code Web)
├── docker/
│   ├── kali-mcp.Dockerfile          # Kali Linux + Metasploit Framework
│   ├── wire-mcp.Dockerfile
│   ├── screenshot-mcp.Dockerfile
│   ├── ollama.Dockerfile
│   ├── ollama-mcp.Dockerfile
│   ├── agent-ingestion.Dockerfile
│   ├── agent-processing.Dockerfile
│   ├── agent-synthesis.Dockerfile
│   ├── claude-code.Dockerfile       # MCP client container
│   └── claude-code-entrypoint.sh    # Startup script with health checks
├── kali-mcp/                        # Kali MCP server (70+ tools + Metasploit)
├── wire-mcp/                        # WireMCP server (tshark, 7 tools)
├── screenshot-mcp/                  # Screenshot MCP server (Playwright, 4 tools)
├── metasploit-mcp/                  # [DEPRECATED] Standalone MSF RPC server (kept for reference)
├── mcp_servers/
│   └── ollama_mcp_server.py         # thin MCP orchestrator
├── blhackbox/
│   ├── mcp/
│   │   └── server.py               # blhackbox MCP server (stdio)
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
│   ├── reporting/
│   │   ├── html_generator.py
│   │   └── pdf_generator.py
│   ├── modules/
│   ├── utils/
│   ├── data/
│   ├── main.py
│   ├── config.py
│   └── exceptions.py
├── blhackbox-mcp-catalog.yaml       # MCP Gateway catalog (optional)
├── docker-compose.yml
├── .env.example
├── Makefile
├── tests/
└── .github/workflows/
    ├── ci.yml
    └── build-and-push.yml
```

---

## License

MIT
