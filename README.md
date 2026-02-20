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

---

## Table of Contents

- [How It Works](#how-it-works)
- [Architecture](#architecture)
- [Components](#components)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Tutorial 1: Claude Code (Docker)](#tutorial-1-claude-code-docker)
- [Tutorial 2: Claude Code (Web)](#tutorial-2-claude-code-web)
- [Tutorial 3: Claude Desktop (Host Install)](#tutorial-3-claude-desktop-host-install)
- [Tutorial 4: ChatGPT / OpenAI (Host Install)](#tutorial-4-chatgpt--openai-host-install)
- [How Prompts Flow Through the System](#how-prompts-flow-through-the-system)
- [Ollama Preprocessing Pipeline](#ollama-mcp-server--preprocessing-pipeline)
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

1. **You type a prompt** in your AI client (Claude Desktop, Claude Code, or ChatGPT).
2. **The AI decides which tools to call** from the two MCP servers: Kali Linux MCP (nmap, nikto, gobuster, etc.) and HexStrike MCP (150+ security tools, 12+ AI agents).
3. **The MCP Gateway routes each tool call** to the correct container and returns raw output to the AI.
4. **The AI collects all raw outputs** and sends them to the Ollama MCP server via `process_scan_results()`.
5. **Ollama preprocesses the data** through 3 agent containers in sequence (Ingestion -> Processing -> Synthesis), each calling the local Ollama LLM independently.
6. **The structured `AggregatedPayload` returns to the AI**, which writes the final pentest report.

Everything runs inside Docker containers. No tools are installed on your host machine.

---

## Architecture

```
YOU (the user)
  |
  |  Type a prompt like: "Run a full recon on example.com"
  |
  v
MCP HOST
  |  Claude Code (Docker container on blhackbox_net)    <-- fully Dockerized
  |  Claude Desktop (host install, connects via localhost) <-- GUI, not Dockerizable
  |  ChatGPT / OpenAI (host install, connects via localhost)
  |
  |  The AI reads your prompt and decides which tools to use.
  |  It connects to the MCP Gateway (single entry point).
  |
  v
DOCKER MCP GATEWAY (localhost:8080 / mcp-gateway:8080)
  |
  |  Routes each MCP tool call to the correct server container.
  |
  |--- Tool calls (recon, scanning, enumeration) --->  KALI MCP SERVER
  |                                                     nmap, nikto, gobuster,
  |                                                     subfinder, whois, etc.
  |
  |--- Tool calls (AI agents, advanced scans) ------>  HEXSTRIKE MCP SERVER
  |                                                     150+ tools, 12+ agents
  |
  |  Raw outputs from both servers return to the AI.
  |  The AI then calls process_scan_results() on:
  |
  |--- process_scan_results(raw_outputs) ----------->  OLLAMA MCP SERVER
                                                        |
                                                        |  Calls 3 agents in sequence via HTTP:
                                                        |
                                                        |---> Agent 1: INGESTION (port 8001)
                                                        |     Parses raw text -> structured data
                                                        |     Calls Ollama /api/chat internally
                                                        |
                                                        |---> Agent 2: PROCESSING (port 8002)
                                                        |     Deduplicates, compresses, annotates
                                                        |     Calls Ollama /api/chat internally
                                                        |
                                                        |---> Agent 3: SYNTHESIS (port 8003)
                                                              Merges into AggregatedPayload
                                                              Calls Ollama /api/chat internally
                                                        |
                                                        v
                                                  AggregatedPayload
                                                        |
                                                        v
                                              Back to MCP HOST (the AI)
                                                        |
                                                        v
                                              AI writes final pentest report
                                                        |
                                                        v (optional)
                                                      NEO4J
                                                 Stores results for
                                                cross-session memory
```

---

## Components

| Container | What it does | Port |
|-----------|-------------|------|
| **MCP Gateway** | Single entry point for all MCP clients. Routes tool calls. | 8080 |
| **Kali MCP** | Runs Kali Linux security tools (nmap, nikto, gobuster, subfinder, etc.) | stdio |
| **HexStrike MCP** | 150+ security tools, 12+ AI agents | 8888 |
| **Ollama MCP** | Thin orchestrator that calls the 3 agent containers in sequence | stdio |
| **Agent: Ingestion** | Parses raw tool output into structured typed data | 8001 |
| **Agent: Processing** | Deduplicates, compresses, annotates errors with security relevance | 8002 |
| **Agent: Synthesis** | Merges everything into the final `AggregatedPayload` | 8003 |
| **Ollama** | Local LLM inference backend (llama3.3 by default) | 11434 |
| **Claude Code** | (Optional) Anthropic CLI MCP client running in Docker | — |
| **Portainer** | Web UI for managing and monitoring all containers | 9443 |
| **Neo4j** | (Optional) Cross-session knowledge graph for recurring engagements | 7474/7687 |

---

## Prerequisites

- **Docker** and **Docker Compose** installed on your machine
- **NVIDIA Container Toolkit** (GPU acceleration is enabled by default — see [GPU Support](#gpu-support-for-ollama) to disable if no NVIDIA GPU)
- At least **16 GB RAM** recommended (Ollama + all containers)
- An **API key** for your AI client:
  - Claude Desktop or Claude Code: `ANTHROPIC_API_KEY` from [console.anthropic.com](https://console.anthropic.com)
  - ChatGPT / OpenAI: `OPENAI_API_KEY` from [platform.openai.com](https://platform.openai.com)

---

## Installation

This is the same for **all three tutorials** below. Do this first.

```bash
# 1. Clone the repo
git clone https://github.com/valITino/blhackbox.git
cd blhackbox

# 2. Create your .env file and add your API keys
cp .env.example .env
# Edit .env — fill in ANTHROPIC_API_KEY and/or OPENAI_API_KEY

# 3. Pull all pre-built Docker images (no local builds needed)
docker compose pull

# 4. Start the core stack (9 containers)
docker compose up -d

# 5. Download the Ollama model (required — runs inside the container)
make ollama-pull
```

That's it. All 10 Docker images are pre-built on Docker Hub. No local builds,
no submodules, no Python install needed.

**Verify everything is running:**

```bash
make status
# You should see 9 containers, all "Up" or "healthy"
```

> **With Neo4j** (cross-session memory): `docker compose --profile neo4j up -d`

---

## Which MCP Clients Can Run in Docker?

| Client | Docker? | Why |
|--------|---------|-----|
| **Claude Code (Docker)** | **Yes** — runs as a container on `blhackbox_net` | CLI tool. Works headless in a container. |
| **Claude Code (Web)** | No — runs on claude.ai/code | Web sessions use the repo's `.mcp.json` directly. |
| **Claude Desktop** | No — must install on host | GUI app. Needs a display server. |
| **ChatGPT / OpenAI** | No — must install on host | Web/GUI app. No headless MCP client available. |

> **Recommendation:** Use **Tutorial 1 (Claude Code Docker)** for a fully
> Dockerized setup, or **Tutorial 2 (Claude Code Web)** for the fastest
> zero-install experience.

---

## Tutorial 1: Claude Code (Docker)

Claude Code is Anthropic's CLI tool for developers. It supports MCP natively
and **runs entirely inside a Docker container** — no Node.js, no npm, no host
install. The container connects to the MCP Gateway over the internal Docker
network.

### Step 1: Start the blhackbox stack

Follow the [Installation](#installation) steps above if you haven't already.
Make sure your `.env` file has your `ANTHROPIC_API_KEY` set.

All containers must be running (`make status` to verify).

### Step 2: Build and launch Claude Code

```bash
make claude-code
```

Or manually:

```bash
docker compose --profile claude-code build claude-code
docker compose run --rm claude-code
```

This builds a container with Claude Code pre-installed and pre-configured to
connect to the MCP Gateway on the internal Docker network. No Node.js, no npm,
no manual config files needed.

The container drops you into an interactive Claude Code session. The MCP
connection to blhackbox is already configured — Claude Code connects to
`http://mcp-gateway:8080/sse` over the Docker network automatically.

### Step 3: Verify the connection

Once inside the Claude Code session, type:

```
/mcp
```

You should see `blhackbox` listed as a connected MCP server with all available
tools from Kali, HexStrike, and the Ollama pipeline.

### Step 4: Run your first pentest

Inside the Claude Code session, type your prompt:

```
Run a full recon and vulnerability scan on example.com --authorized
```

**What happens next (the full prompt flow):**

1. Claude Code reads your prompt and decides which tools to call. It picks
   from the **Kali MCP Server** tools (nmap, nikto, subfinder, etc.) and
   **HexStrike MCP Server** tools (150+ security tools, AI agents).
2. Each tool call goes through the **MCP Gateway** over the Docker network,
   which routes it to the correct container.
3. Raw text output from each tool returns to Claude Code through the gateway.
4. Claude Code collects all raw outputs across multiple phases (recon,
   scanning, enumeration) — potentially 10-20+ tool calls.
5. Claude Code calls `process_scan_results()` on the **Ollama MCP Server**,
   passing all raw outputs as a single batch.
6. The Ollama MCP Server pipelines the data through 3 agents:
   - **Ingestion** (port 8001): calls Ollama LLM -> structured data
   - **Processing** (port 8002): calls Ollama LLM -> deduplicated + compressed
   - **Synthesis** (port 8003): calls Ollama LLM -> final `AggregatedPayload`
7. The `AggregatedPayload` returns to Claude Code.
8. Claude Code writes the **final pentest report** directly in your terminal.

You will see each tool call and its output printed in the terminal as Claude
Code works through the phases. The final report is output at the end.

> **Alternative:** If you prefer not to use Docker for Claude Code, see
> [Tutorial 2: Claude Code (Web)](#tutorial-2-claude-code-web) or install
> Claude Code on your host with `npm install -g @anthropic-ai/claude-code`
> and run `claude` from the repo root — the `.mcp.json` is already configured.

### Monitoring (optional)

In a separate terminal, watch tool calls in real time:

```bash
make gateway-logs          # every MCP call as it happens
make logs-agent-ingestion  # Ingestion Agent processing
make logs-agent-synthesis  # Synthesis Agent building the payload
```

---

## Tutorial 2: Claude Code (Web)

Claude Code runs on [claude.ai/code](https://claude.ai/code) as a web-based
coding agent. When you open this repository in a web session, the MCP server
configures itself automatically — no Docker, no npm, no manual setup.

### How it works

The repo ships with two files that handle everything:

1. **`.mcp.json`** (project root) — tells Claude Code to start the blhackbox
   MCP server via stdio:
   ```json
   {
     "mcpServers": {
       "blhackbox": {
         "command": ".venv/bin/blhackbox",
         "args": ["mcp"]
       }
     }
   }
   ```

2. **`.claude/hooks/session-start.sh`** — a SessionStart hook that runs
   automatically when a web session starts. It creates a Python virtual
   environment and installs the `blhackbox` package (which provides the
   `.venv/bin/blhackbox` binary that `.mcp.json` references).

### Step 1: Open the repo in Claude Code Web

Go to [claude.ai/code](https://claude.ai/code) and open this repository.
The SessionStart hook runs automatically — it installs dependencies and
configures the environment. No action needed.

### Step 2: Verify the connection

Type:

```
/mcp
```

You should see `blhackbox` listed with 6 tools:
- `recon` — multi-tool reconnaissance
- `run_tool` — execute a single security tool
- `query_graph` — Cypher queries against Neo4j
- `get_findings` — retrieve findings for a target
- `list_tools` — discover available tools
- `generate_report` — produce HTML/PDF reports

### Step 3: Run your first pentest

```
Run a full recon on example.com --authorized
```

The blhackbox MCP server orchestrates tool execution via HexStrike, stores
results in the knowledge graph, and returns structured findings directly to
Claude Code.

> **Note:** The web session uses the blhackbox stdio MCP server directly
> (not the Docker MCP Gateway). The Docker stack is not required — Claude
> Code talks to HexStrike's API and Neo4j over the network. For the full
> Docker pipeline with Kali tools and Ollama preprocessing, use
> [Tutorial 1](#tutorial-1-claude-code-docker).

---

## Tutorial 3: Claude Desktop (Host Install)

Claude Desktop is Anthropic's GUI app with built-in MCP support. It connects
to blhackbox's MCP Gateway and uses all the security tools directly from the
chat window.

> **Why not Docker?** Claude Desktop is a graphical application that needs a
> display server (macOS/Windows/Linux desktop). It cannot run headless in a
> Docker container. You install it on your host machine and it connects to the
> blhackbox containers running in Docker.

### Step 1: Install Claude Desktop

Download from [claude.ai/download](https://claude.ai/download) and install it.

### Step 2: Start the blhackbox stack

Follow the [Installation](#installation) steps above if you haven't already.
All containers must be running.

### Step 3: Configure Claude Desktop to connect to blhackbox

Open the Claude Desktop config file:

- **macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`
- **Linux:** `~/.config/Claude/claude_desktop_config.json`

Add the following:

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

> **Note:** Claude Desktop runs on your host, so it connects via `localhost`.
> The MCP Gateway port (8080) is exposed to the host by docker-compose.

Save the file and **restart Claude Desktop**.

### Step 4: Verify the connection

After restarting, you should see a **hammer icon** (tools) in the Claude Desktop
chat input area. Click it to see the list of available MCP tools from Kali,
HexStrike, and the Ollama pipeline. If you see tools listed, the connection works.

### Step 5: Run your first pentest

Type a prompt in the Claude Desktop chat. For example:

```
Run a full recon and vulnerability scan on example.com --authorized
```

**What happens next (the full prompt flow):**

1. Claude reads your prompt and decides which tools to call first. It will
   typically start with recon tools from the **Kali MCP Server** (subfinder,
   nmap, whois, dig) and **HexStrike MCP Server** (OSINT agents, WHOIS agent).
2. The **MCP Gateway** (localhost:8080) receives each tool call from Claude and
   routes it to the correct container (Kali or HexStrike).
3. Each tool runs inside its Docker container and returns raw text output back
   through the gateway to Claude.
4. Claude collects all raw outputs (it may run 10-20+ tool calls across the
   recon, scanning, and enumeration phases).
5. Claude calls `process_scan_results()` on the **Ollama MCP Server**, passing
   all collected raw outputs.
6. The Ollama MCP Server sends the data through 3 agents in sequence:
   - **Ingestion Agent** (port 8001): calls Ollama LLM to parse raw text into structured data
   - **Processing Agent** (port 8002): calls Ollama LLM to deduplicate, compress, and annotate
   - **Synthesis Agent** (port 8003): calls Ollama LLM to merge into final `AggregatedPayload`
7. The `AggregatedPayload` (structured findings, vulnerabilities, metadata)
   returns to Claude through the MCP Gateway.
8. Claude writes the **final pentest report** with executive summary, findings
   by severity, remediation recommendations, and appendix.

You will see Claude working through each step in the chat, calling tools and
displaying progress. The final report appears directly in the conversation.

### Monitoring (optional)

While Claude is working, you can watch the tool calls in real time:

```bash
make gateway-logs          # see every MCP tool call as it happens
make logs-agent-ingestion  # watch the Ingestion Agent process data
make logs-agent-synthesis  # watch the Synthesis Agent build the payload
```

Or open **Portainer** at `https://localhost:9443` to see all containers,
their logs, and resource usage in a web UI.

---

## Tutorial 4: ChatGPT / OpenAI (Host Install)

ChatGPT (and OpenAI-compatible clients) can also connect to blhackbox through
the MCP Gateway. The flow is identical — the AI decides which tools to call,
blhackbox executes them in Docker containers, and the Ollama pipeline processes
the results.

> **Why not Docker?** There is no standard headless MCP client for
> OpenAI that can be packaged as a Docker image. ChatGPT Desktop is a GUI app
> (same limitation as Claude Desktop), and the OpenAI API alone is not an MCP
> client. You need a host-installed MCP client that supports the OpenAI API.

### Step 1: Set up an OpenAI-compatible MCP client

OpenAI does not have native MCP support in the standard ChatGPT app at this time.
You need an **OpenAI-compatible client that supports MCP**. Options include:

- **ChatGPT Desktop** (if MCP support is available in your version)
- **Open-source MCP clients** configured with your OpenAI API key
- **Custom scripts** using the OpenAI API + an MCP client library

The key requirement: the client must support connecting to an MCP server via
SSE transport at `http://localhost:8080/sse`.

### Step 2: Start the blhackbox stack

Follow the [Installation](#installation) steps above. Make sure your `.env`
file has your `OPENAI_API_KEY` set:

```bash
# In .env
OPENAI_API_KEY=sk-...
```

All containers must be running (`make status` to verify).

### Step 3: Configure the OpenAI client to connect to blhackbox

Point your MCP-capable OpenAI client at the blhackbox MCP Gateway:

```
MCP Server URL: http://localhost:8080/sse
Transport: SSE
```

The exact configuration depends on your client. The MCP Gateway exposes the
same tools regardless of which AI is connecting — Kali tools, HexStrike tools,
and the Ollama processing pipeline are all available.

> **Note:** Like Claude Desktop, OpenAI clients run on your host and connect
> via `localhost:8080`. Only the blhackbox backend runs in Docker.

### Step 4: Verify the connection

Your client should show the available MCP tools after connecting. Look for
tools from Kali (nmap, nikto, etc.), HexStrike (security agents), and the
Ollama pipeline (process_scan_results).

### Step 5: Run your first pentest

Type a prompt in your OpenAI client:

```
Run a full recon and vulnerability scan on example.com --authorized
```

**What happens next (the full prompt flow):**

1. ChatGPT/OpenAI reads your prompt and decides which tools to call from the
   two MCP servers: **Kali MCP** (nmap, nikto, subfinder, etc.) and
   **HexStrike MCP** (150+ tools, 12+ AI agents).
2. Each tool call goes through the **MCP Gateway** (localhost:8080) to the
   correct Docker container. The gateway does not care which AI is calling —
   it routes the same way for Claude or OpenAI.
3. Raw text output returns to the OpenAI client.
4. The AI collects all raw outputs and calls `process_scan_results()` on the
   **Ollama MCP Server**.
5. The Ollama MCP Server sends data through 3 agents sequentially:
   - **Ingestion** (port 8001): Ollama LLM parses raw text -> structured data
   - **Processing** (port 8002): Ollama LLM deduplicates and compresses
   - **Synthesis** (port 8003): Ollama LLM merges into `AggregatedPayload`
6. The `AggregatedPayload` returns to the OpenAI client.
7. ChatGPT/OpenAI writes the **final pentest report**.

The prompt flow is identical to the Claude tutorials. The MCP Gateway is
AI-agnostic — it serves tools to any MCP-compatible client.

### Monitoring (optional)

```bash
make gateway-logs          # watch tool calls from any client
make logs-agent-ingestion  # Ingestion Agent logs
make logs-agent-synthesis  # Synthesis Agent logs
```

---

## How Prompts Flow Through the System

This section explains the end-to-end data flow for the Docker-based tutorials
(1, 3, and 4). The flow is the same regardless of which AI client you use.
Tutorial 2 (Claude Code Web) uses the blhackbox stdio MCP server directly
and skips the MCP Gateway.

```
STEP 1: YOU TYPE A PROMPT
  "Run a full recon on example.com --authorized"
        |
        v
STEP 2: AI DECIDES WHICH TOOLS TO USE
  The AI (Claude or ChatGPT) reads your prompt and autonomously
  picks tools from the Kali MCP Server and HexStrike MCP Server.
  Example tool calls the AI might make:
    - subfinder (Kali)      -> find subdomains
    - nmap -sV -sC (Kali)   -> port scan + service detection
    - nikto (Kali)           -> web server scanning
    - whois (Kali)           -> domain registration info
    - HexStrike OSINT agent  -> OSINT gathering
    - HexStrike vuln agent   -> vulnerability scanning
        |
        v
STEP 3: MCP GATEWAY ROUTES TOOL CALLS TO CONTAINERS
  localhost:8080 receives each call and forwards it:
    - Kali tools    -> blhackbox-kali-mcp container
    - HexStrike     -> blhackbox-hexstrike container
  Raw text output returns through the gateway to the AI.
        |
        v
STEP 4: AI SENDS RAW OUTPUTS TO OLLAMA FOR PROCESSING
  After collecting all raw outputs, the AI calls:
    process_scan_results(raw_outputs)
  on the Ollama MCP Server.
        |
        v
STEP 5: OLLAMA PIPELINE (3 AGENTS IN SEQUENCE)
  The Ollama MCP Server calls 3 containers via HTTP:

  Agent 1: INGESTION (blhackbox-agent-ingestion:8001)
    Input:  raw text from all tools
    Action: calls Ollama /api/chat with ingestion prompt
    Output: structured typed data (hosts, ports, services, vulns)
        |
        v
  Agent 2: PROCESSING (blhackbox-agent-processing:8002)
    Input:  structured data from Agent 1
    Action: calls Ollama /api/chat with processing prompt
    Output: deduplicated, compressed data + annotated error_log
        |
        v
  Agent 3: SYNTHESIS (blhackbox-agent-synthesis:8003)
    Input:  processed data from Agent 2
    Action: calls Ollama /api/chat with synthesis prompt
    Output: final AggregatedPayload
        |
        v
STEP 6: AGGREGATED PAYLOAD RETURNS TO THE AI
  The AggregatedPayload contains:
    - findings: hosts, vulnerabilities, endpoints
    - error_log: scan errors with security_relevance ratings
    - metadata: tools_run, compression_ratio, duration, etc.
        |
        v
STEP 7: AI WRITES THE FINAL REPORT
  The AI uses the structured payload to write a professional
  pentest report with:
    - Executive summary
    - Findings by severity (critical/high/medium/low/info)
    - Remediation recommendations
    - Appendix with full scan metadata
        |
        v
STEP 8 (OPTIONAL): RESULTS STORED IN NEO4J
  If Neo4j is enabled, the AggregatedPayload is stored in the
  knowledge graph for cross-session memory and recurring engagements.
```

**Key point:** The AI client (Claude or ChatGPT) is the orchestrator. It
decides which tools to call, when to call them, and in what order. The MCP
Gateway simply routes calls. The Ollama pipeline simply preprocesses data.
The intelligence lives in the AI client.

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

---

## Makefile Shortcuts

```bash
make pull                  # Pull all pre-built images from Docker Hub
make up                    # Start core stack (9 containers)
make up-full               # Start with Neo4j (10 containers)
make down                  # Stop all services
make claude-code           # Build and launch Claude Code in Docker
make test                  # Run tests
make lint                  # Run linter
make status                # Health status of all containers
make ollama-pull           # Pull Ollama model
make portainer             # Open Portainer dashboard
make gateway-logs          # Live MCP tool call log
make restart-agents        # Restart all 3 agent containers
make logs-agent-ingestion  # Tail Ingestion Agent logs
make push-all              # Build and push all images to Docker Hub
```

---

## Build from Source (optional)

Only needed if you want to modify Dockerfiles or agent code:

```bash
git submodule update --init --recursive   # fetch kali-mcp + hexstrike source
docker compose build                      # build all 6 custom images locally
docker compose up -d
```

---

## Docker Hub Images

All custom images are published to `crhacky/blhackbox`:

| Tag | Description |
|-----|-------------|
| `crhacky/blhackbox:kali-mcp` | Kali Linux MCP Server |
| `crhacky/blhackbox:hexstrike` | HexStrike AI MCP Server |
| `crhacky/blhackbox:ollama-mcp` | Ollama MCP Server (thin orchestrator) |
| `crhacky/blhackbox:agent-ingestion` | Agent 1: Ingestion |
| `crhacky/blhackbox:agent-processing` | Agent 2: Processing |
| `crhacky/blhackbox:agent-synthesis` | Agent 3: Synthesis |

MCP client container (built locally from `docker/claude-code.Dockerfile`):

| Tag | Description |
|-----|-------------|
| `blhackbox-claude-code` | Claude Code CLI client (connects to gateway on Docker network) |

Official images pulled directly:
- `ollama/ollama:latest`
- `neo4j:5`
- `portainer/portainer-ce:latest`
- `docker/mcp-gateway:latest`
- `node:22-slim` (base for Claude Code container)

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

NVIDIA GPU acceleration is **enabled by default** in `docker-compose.yml` under
the `ollama` service. This requires the
[NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html)
to be installed on the host.

**If you do NOT have an NVIDIA GPU**, comment out the `deploy` block in
`docker-compose.yml` under the `ollama` service:

```yaml
    # deploy:
    #   resources:
    #     reservations:
    #       devices:
    #         - driver: nvidia
    #           count: all
    #           capabilities: [gpu]
```

Ollama will fall back to CPU-only inference automatically when the GPU block is
removed.

---

## Security Notes

- **Docker socket**: MCP Gateway and Portainer mount `/var/run/docker.sock`.
  This grants effective root on the host. Never expose ports 8080 or 9443 to
  the public internet.
- **Authorization**: The `--authorized` flag is mandatory on all scan commands.
- **Neo4j**: Set a strong password in `.env`. Never use defaults in production.
- **Agent containers**: Do not expose ports to the host — they communicate only
  on the internal `blhackbox_net` Docker network.

---

## Project Structure

```
blhackbox/
├── .claude/
│   ├── settings.json               # Claude Code hooks config
│   └── hooks/
│       └── session-start.sh        # auto-setup for web sessions
├── .mcp.json                        # MCP server config (Claude Code)
├── docker/
│   ├── kali-mcp.Dockerfile
│   ├── hexstrike.Dockerfile
│   ├── ollama-mcp.Dockerfile
│   ├── agent-ingestion.Dockerfile
│   ├── agent-processing.Dockerfile
│   ├── agent-synthesis.Dockerfile
│   └── claude-code.Dockerfile       # MCP client container
├── kali-mcp/                        # adapted community Kali MCP server
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

---

## License

MIT
