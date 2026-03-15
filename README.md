```
╔═══════════════════════════════════════════════════════════════════════════════╗
║                                                                               ║
║  ██████╗ ██╗       ██╗  ██╗ █████╗  ██████╗██╗  ██╗██████╗  ██████╗ ██╗  ██╗  ║
║  ██╔══██╗██║       ██║  ██║██╔══██╗██╔════╝██║ ██╔╝██╔══██╗██╔═══██╗╚██╗██╔╝  ║
║  ██████╔╝██║       ███████║███████║██║     █████╔╝ ██████╔╝██║   ██║ ╚███╔╝   ║
║  ██╔══██╗██║       ██╔══██║██╔══██║██║     ██╔═██╗ ██╔══██╗██║   ██║ ██╔██╗   ║
║  ██████╔╝███████╗  ██║  ██║██║  ██║╚██████╗██║  ██╗██████╔╝╚██████╔╝██╔╝ ██╗  ║
║  ╚═════╝ ╚══════╝  ╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝╚═╝  ╚═╝╚═════╝  ╚═════╝ ╚═╝  ╚═╝  ║
║                                                                               ║
╠═══════════════════════════════════════════════════════════════════════════════╣
║                                                                               ║
║                   MCP-based Autonomous Pentesting Framework                   ║
║           Recon  ·  Exploitation  ·  Post-Exploitation  ·  Reporting          ║
║                                                                               ║
╠═══════════════════════════════════════════════════════════════════════════════╣
║             by valITino  ·  Docker · Python · FastMCP · Metasploit            ║
║                                                                               ║
╠═══════════════════════════════════════════════════════════════════════════════╣
║       ⚠  Authorized security testing only — unauthorized use is illegal       ║
║                                                                               ║
╚═══════════════════════════════════════════════════════════════════════════════╝
```

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

| | |
|---|---|
| **Getting Started** | [How It Works](#how-it-works) · [Architecture](#architecture) · [Prerequisites](#prerequisites) · [Installation](#installation) |
| **Tutorials** | [Claude Code (Docker)](#tutorial-1-claude-code-docker--recommended) · [Claude Code (Web)](#tutorial-2-claude-code-web) · [Claude Desktop](#tutorial-3-claude-desktop-host--gateway) · [ChatGPT / OpenAI](#tutorial-4-chatgpt--openai-host--gateway) |
| **Reference** | [Components](#components) · [Output Files](#output-files) · [CLI Reference](#cli-reference) · [Makefile Shortcuts](#makefile-shortcuts) · [Docker Hub Images](#docker-hub-images) |
| **Operations** | [Prompt Flow](#how-prompts-flow-through-the-system) · [MCP Gateway](#do-i-need-the-mcp-gateway) · [Portainer Setup](#portainer-setup) · [Neo4j](#neo4j-optional) · [Troubleshooting](#troubleshooting) |
| **Security** | [Authorization & Verification](#authorization--verification) · [Security Notes](#security-notes) |
| **Project** | [Project Structure](#project-structure) · [Build from Source](#build-from-source-optional) · [License](#license) |

---

## How It Works

In v2, **your AI client (Claude or ChatGPT) IS the orchestrator**. There is no internal LangGraph orchestrator or LLM planner. Here is what happens when you type a prompt:

1. **You type a prompt** in your AI client (Claude Code, Claude Desktop, or ChatGPT).
2. **The AI decides which tools to call** from three MCP servers — Kali MCP (70+ security tools including Metasploit), WireMCP (7 packet analysis tools), and Screenshot MCP (4 evidence capture tools).
3. **Each MCP server executes the tool** in its Docker container and returns raw output.
4. **The AI structures the results** — parsing, deduplicating, correlating, and building an `AggregatedPayload` directly.
5. **The AI validates and persists** the payload via `aggregate_results()`, then writes the final pentest report.

Everything runs inside Docker containers. No tools are installed on your host machine.

---

## Architecture

Claude Code in Docker connects **directly** to each MCP server via SSE over the internal Docker network — no MCP Gateway needed.

```
YOU (the user)
  │
  │  docker compose run --rm claude-code
  │  (or attach via Portainer)
  │
  ▼
CLAUDE CODE (Docker container on blhackbox_net)
  │
  │  Reads your prompt, decides which tools to call.
  │  Connects directly to each MCP server via SSE.
  │
  ├── kali (SSE :9001) ──────────────▶  KALI MCP SERVER
  │                                      70+ tools: nmap, nikto, gobuster, sqlmap,
  │                                      hydra, msfconsole, msfvenom, john, hashcat…
  │
  ├── wireshark (SSE :9003) ─────────▶  WIREMCP SERVER
  │                                      7 tools: packet capture, pcap analysis,
  │                                      credential extraction
  │
  ├── screenshot (SSE :9004) ────────▶  SCREENSHOT MCP SERVER
  │                                      4 tools: web page screenshots, element
  │                                      capture, annotations
  │
  │  After collecting raw outputs, Claude structures them directly:
  │    get_payload_schema() → parse/dedup/correlate → aggregate_results()
  │
  ▼
AggregatedPayload → generate_report() → final pentest report
  │
  ▼ (optional)
NEO4J — cross-session memory

PORTAINER (https://localhost:9443) — web UI for all containers
```

For host-based clients (Claude Desktop, ChatGPT), an **optional MCP Gateway** aggregates all servers behind `localhost:8080/mcp`. See [Do I Need the MCP Gateway?](#do-i-need-the-mcp-gateway)

---

## Components

| Container | Description | Port | Profile |
|:--|:--|:--:|:--:|
| **Kali MCP** | Kali Linux security tools + Metasploit — 70+ tools (nmap, sqlmap, hydra, msfconsole, msfvenom, etc.) | `9001` | default |
| **WireMCP** | Wireshark / tshark — 7 packet capture and analysis tools | `9003` | default |
| **Screenshot MCP** | Headless Chromium — 4 screenshot and annotation tools | `9004` | default |
| **Portainer** | Web UI for managing all containers | `9443` | default |
| **Claude Code** | Anthropic CLI MCP client in Docker | — | `claude-code` |
| **MCP Gateway** | Single entry point for host-based MCP clients | `8080` | `gateway` |
| **Neo4j** | Cross-session knowledge graph | `7474` / `7687` | `neo4j` |

---

## Output Files

All output files are stored in `./output/` on your host via Docker bind mounts — no need to `docker cp`.

```
output/
├── reports/       ← Pentest reports (.md, .pdf)
├── screenshots/   ← PoC evidence screenshots (.png)
└── sessions/      ← Aggregated session JSON files
```

| Container Path | Host Path | Contents |
|:--|:--|:--|
| `/root/reports/` | `./output/reports/` | Generated pentest reports (Markdown, PDF) |
| `/tmp/screenshots/` | `./output/screenshots/` | Screenshot MCP captures and annotations |
| `/root/results/` | `./output/sessions/` | `AggregatedPayload` session JSONs |

The `output/` directory is created automatically by `setup.sh`. For manual installs: `mkdir -p output/reports output/screenshots output/sessions`

> **Note:** `output/` is git-ignored. Back up important reports separately.

---

## Prerequisites

- **Docker** and **Docker Compose** (Docker Engine on Linux, or Docker Desktop)
- At least **8 GB RAM** recommended (4 containers in the core stack)
- An **Anthropic API key** from [console.anthropic.com](https://console.anthropic.com) (required for Claude Code)

---

## Installation

### Quick Start (Recommended)

```bash
git clone https://github.com/valITino/blhackbox.git
cd blhackbox
./setup.sh
```

The setup wizard will:

1. Check prerequisites (Docker, Docker Compose, disk space)
2. Let you choose optional components (Neo4j, MCP Gateway)
3. Prompt for your `ANTHROPIC_API_KEY` (required for Claude Code in Docker)
4. Generate `.env` and create the `output/` directory
5. Pull Docker images and start all services
6. Wait for health checks to pass

Non-interactive flags:

```bash
./setup.sh --api-key sk-ant-... --minimal      # Core stack only
./setup.sh --api-key sk-ant-... --with-neo4j   # Core + Neo4j
./setup.sh --help                               # All options
```

Or use the Makefile shortcut: `make setup`

### Manual Installation

```bash
# 1. Clone
git clone https://github.com/valITino/blhackbox.git && cd blhackbox

# 2. Configure
cp .env.example .env
# REQUIRED: set ANTHROPIC_API_KEY=sk-ant-... in .env

# 3. Create output directories
mkdir -p output/reports output/screenshots output/sessions

# 4. Pull images and start
docker compose pull
docker compose up -d
```

**Set up authorization** (required before running pentests):

```bash
# 5. Fill in engagement details
nano verification.env
# Set AUTHORIZATION_STATUS=ACTIVE after completing all fields

# 6. Render the active verification document
make inject-verification
```

See [Authorization & Verification](#authorization--verification) for details.

**Verify everything is running:**

```bash
make status     # Container status
make health     # MCP server health check
```

You should see 4 healthy containers: `blhackbox-kali-mcp`, `blhackbox-wire-mcp`, `blhackbox-screenshot-mcp`, `blhackbox-portainer`.

> **Tip:** Open Portainer at `https://localhost:9443` and create an admin account within 5 minutes. See [Portainer Setup](#portainer-setup).

---

## Tutorial 1: Claude Code (Docker) — Recommended

Claude Code runs entirely inside a Docker container on the same network as all blhackbox services. It connects **directly** to each MCP server via SSE — no MCP Gateway, no host install, no Node.js.

### Step 1 — Start the stack

Follow [Installation](#installation) above. Make sure `ANTHROPIC_API_KEY` is set in `.env` and all core containers are healthy (`make health`).

### Step 2 — Launch Claude Code

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

  ──────────────────────────────────────────────
  All 3 services connected.

  MCP servers (connected via SSE):
    kali            Kali Linux security tools + Metasploit (70+ tools)
    wireshark       WireMCP — tshark packet capture & analysis
    screenshot      Screenshot MCP — headless Chromium evidence capture

  Data aggregation:
    You (Claude) handle parsing, deduplication, and synthesis directly.
    Use get_payload_schema + aggregate_results to validate & persist.

  Quick start:
    /mcp              Check MCP server status
    Scan example.com for open ports and web vulnerabilities
  ──────────────────────────────────────────────
```

You are now inside an interactive Claude Code session.

### Step 3 — Verify the connection

```
/mcp
```

You should see `kali`, `wireshark`, and `screenshot`, each with their available tools.

### Step 4 — Run your first pentest

```
Scan example.com for open ports and web vulnerabilities
```

Claude Code will autonomously:

1. Call Kali tools (nmap, subfinder, nikto, etc.)
2. Search for exploits using Metasploit (`msf_search`)
3. Collect raw outputs from all tools
4. Structure, deduplicate, and correlate findings into an `AggregatedPayload`
5. Validate via `aggregate_results()` and write a structured pentest report

### Monitoring (separate terminal)

```bash
make logs-kali         # Kali MCP server activity (includes Metasploit)
make logs-wireshark    # WireMCP activity
make logs-screenshot   # Screenshot MCP activity
```

Or use **Portainer** at `https://localhost:9443` for a unified dashboard.

---

## Tutorial 2: Claude Code (Web)

Claude Code on [claude.ai/code](https://claude.ai/code) works as a web-based coding agent. When you open this repo in a web session, the MCP server configures itself automatically.

### How it works

- **`.mcp.json`** (project root) — tells Claude Code to start the blhackbox MCP server via stdio
- **`.claude/hooks/session-start.sh`** — auto-installs dependencies on session start

### Steps

1. Go to [claude.ai/code](https://claude.ai/code) and open this repository
2. Type `/mcp` to verify — you should see `blhackbox` with 6 tools
3. Type your prompt: `Scan example.com for open ports and web vulnerabilities`

> **Note:** The web session uses the blhackbox stdio MCP server directly (not the Docker stack). For the full Docker stack with Kali tools and Metasploit, use [Tutorial 1](#tutorial-1-claude-code-docker--recommended).

---

## Tutorial 3: Claude Desktop (Host + Gateway)

Claude Desktop is a GUI app that cannot run in Docker. It connects to blhackbox via the **MCP Gateway** on `localhost:8080`.

### Step 1 — Start the stack with the gateway

```bash
docker compose up -d                        # core stack
docker compose --profile gateway up -d      # adds the MCP Gateway
# OR shortcut:
make up-gateway
```

### Step 2 — Configure Claude Desktop

Open the config file:

| Platform | Path |
|:--|:--|
| macOS | `~/Library/Application Support/Claude/claude_desktop_config.json` |
| Windows | `%APPDATA%\Claude\claude_desktop_config.json` |
| Linux | `~/.config/Claude/claude_desktop_config.json` |

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

### Step 3 — Run a pentest

Type your prompt in Claude Desktop. The flow is identical to Tutorial 1 — the gateway routes tool calls to the same MCP servers.

---

## Tutorial 4: ChatGPT / OpenAI (Host + Gateway)

ChatGPT / OpenAI clients also connect via the **MCP Gateway** on `localhost:8080`.

### Step 1 — Start with gateway

```bash
make up-gateway
```

### Step 2 — Configure your client

Point your MCP-capable OpenAI client at:

| Setting | Value |
|:--|:--|
| URL | `http://localhost:8080/mcp` |
| Transport | Streamable HTTP |

The gateway is AI-agnostic — it serves the same tools to any MCP client.

---

## How Prompts Flow Through the System

```
STEP 1 ─ YOU TYPE A PROMPT
  "Scan example.com for open ports and web vulnerabilities"
          │
          ▼
STEP 2 ─ AI DECIDES WHICH TOOLS TO USE
  Claude picks tools from Kali MCP (incl. Metasploit), WireMCP, Screenshot MCP:
    • subfinder (Kali)           → find subdomains
    • nmap -sV -sC (Kali)       → port scan + service detection
    • nikto (Kali)               → web server scanning
    • msf_search (Kali/MSF)      → find matching exploits
    • capture_packets (WireMCP)  → capture traffic during scanning
          │
          ▼
STEP 3 ─ TOOLS EXECUTE IN DOCKER CONTAINERS
  Claude Code (Docker) connects directly via SSE.
  Claude Desktop / ChatGPT connect via the MCP Gateway.
  Each tool runs in its container and returns raw text.
          │
          ▼
STEP 4 ─ AI STRUCTURES THE RESULTS
  The AI parses, deduplicates, correlates, and structures all raw
  outputs into an AggregatedPayload directly.
  No external pipeline — the MCP host is the brain.
          │
          ▼
STEP 5 ─ AI VALIDATES AND PERSISTS
  Calls aggregate_results(payload=...) to validate the
  AggregatedPayload against the Pydantic schema and save it.
          │
          ▼
STEP 6 ─ AI WRITES THE FINAL REPORT
  Executive summary, findings by severity, remediation, appendix.
          │
          ▼
STEP 7 ─ (OPTIONAL) RESULTS STORED IN NEO4J
  Cross-session memory for recurring engagements.
```

---

## Do I Need the MCP Gateway?

| MCP Client | Gateway? | How it connects |
|:--|:--:|:--|
| **Claude Code (Docker)** | No | Direct SSE to each MCP server over Docker network |
| **Claude Code (Web)** | No | Stdio MCP server from `.mcp.json` |
| **Claude Desktop** | **Yes** | Host GUI app → `localhost:8080/mcp` gateway |
| **ChatGPT / OpenAI** | **Yes** | Host GUI/web app → `localhost:8080/mcp` gateway |

The MCP Gateway (`docker/mcp-gateway:latest`) aggregates all MCP servers behind a single Streamable HTTP endpoint at `localhost:8080/mcp`. It requires Docker socket mount (`/var/run/docker.sock`) and the `--profile gateway` flag.

```bash
make up-gateway   # starts core stack + gateway
```

> **Why optional?** The gateway adds complexity, requires Docker socket access, and is designed for Docker Desktop environments. On headless Linux servers, direct SSE is simpler and more reliable.

---

## Portainer Setup

Portainer CE provides a web UI for managing all blhackbox containers.

**URL:** `https://localhost:9443`

### First Run

On first launch, Portainer requires you to create an admin account **within 5 minutes**. If you miss the window:

```bash
docker compose restart portainer
```

Then open `https://localhost:9443` again and create your account.

### What you can do

- View all container status, logs, and resource usage
- Restart individual containers
- Inspect environment variables and network configuration
- Monitor the health of each service

> **Note:** Your browser will warn about the self-signed HTTPS certificate. This is expected — click "Advanced" and proceed.

---

## Troubleshooting

### Claude Code shows "Status: failed" for MCP servers

The MCP servers may not be healthy yet:

```bash
make health           # quick health check
make status           # container status
docker compose logs   # full logs
```

If a service shows `FAIL`, restart it:

```bash
docker compose restart kali-mcp
```

### Metasploit tools are slow or fail

Metasploit tools (`msf_search`, `msf_run_module`, etc.) use `msfconsole -qx` for CLI execution. The first invocation takes **10–30 seconds** due to Ruby and database initialization (cold start). Subsequent calls are faster.

If Metasploit commands fail:

1. Check installation: `docker exec blhackbox-kali-mcp which msfconsole`
2. Check database status: use the `msf_status` tool
3. Check container logs: `make logs-kali`

### Portainer shows "Timeout" on first visit

You have 5 minutes after Portainer starts to create an admin account. Missed it? Run `docker compose restart portainer`.

### MCP Gateway doesn't start

The gateway is optional — Claude Code in Docker does not use it. If you need it for Claude Desktop / ChatGPT:

1. Ensure Docker socket exists: `ls -la /var/run/docker.sock`
2. Start with the gateway profile: `make up-gateway`
3. Check logs: `make gateway-logs`

### Container keeps restarting

Check its logs:

```bash
docker compose logs <service-name>   # e.g., kali-mcp, wire-mcp
```

Common causes: port conflict on the host, insufficient memory.

---

## CLI Reference

```bash
blhackbox version                                        # Show version and config
blhackbox recon --target example.com                     # Run recon
blhackbox recon --target example.com --attacks nmap,subfinder
blhackbox recon --target example.com --full              # Full recon suite
blhackbox run-tool -c network -t nmap -p '{"target":"example.com"}'  # Single tool
blhackbox graph query "MATCH (n) RETURN n LIMIT 10"     # Neo4j query
blhackbox graph summary -t example.com                   # Target summary
blhackbox report -s SESSION_ID --format pdf              # Generate report
blhackbox mcp                                            # Start MCP server
```

---

## Makefile Shortcuts

| Target | Description |
|:--|:--|
| `make setup` | Interactive setup wizard (prereqs, .env, pull, start, health) |
| `make help` | Show all available targets |
| `make pull` | Pull all pre-built images from Docker Hub |
| `make up` | Start core stack (4 containers) |
| `make up-full` | Start with Neo4j (5 containers) |
| `make up-gateway` | Start with MCP Gateway for Claude Desktop (5 containers) |
| `make down` | Stop all services |
| `make claude-code` | Build and launch Claude Code in Docker |
| `make status` | Container status table |
| `make health` | Quick health check of all services |
| `make test` | Run tests |
| `make lint` | Run linter |
| `make portainer` | Open Portainer dashboard |
| `make gateway-logs` | Live MCP Gateway logs |
| `make logs-kali` | Tail Kali MCP logs (includes Metasploit) |
| `make logs-wireshark` | Tail WireMCP logs |
| `make logs-screenshot` | Tail Screenshot MCP logs |
| `make inject-verification` | Render verification.env → active authorization document |
| `make push-all` | Build and push all images to Docker Hub |

---

## Build from Source (optional)

Only needed if you want to modify Dockerfiles or agent code:

```bash
git submodule update --init --recursive   # fetch kali-mcp source
docker compose build                      # build all images locally
docker compose up -d
```

---

## Docker Hub Images

All custom images are published to `crhacky/blhackbox`:

| Tag | Description |
|:--|:--|
| `crhacky/blhackbox:kali-mcp` | Kali Linux MCP Server (70+ tools + Metasploit Framework) |
| `crhacky/blhackbox:wire-mcp` | WireMCP Server (tshark, 7 tools) |
| `crhacky/blhackbox:screenshot-mcp` | Screenshot MCP Server (headless Chromium, 4 tools) |
| `crhacky/blhackbox:claude-code` | Claude Code CLI client (direct SSE to MCP servers) |

Official images pulled directly:

| Image | Purpose |
|:--|:--|
| `portainer/portainer-ce:latest` | Docker management UI |
| `neo4j:5` | Knowledge graph (optional) |
| `docker/mcp-gateway:latest` | MCP Gateway (optional) |

---

## Neo4j (Optional)

Neo4j provides cross-session memory. Enable with `--profile neo4j`:

```bash
docker compose --profile neo4j up -d
```

Stores `AggregatedPayload` results as a graph after each session. Useful for recurring engagements against the same targets.

---

## Authorization & Verification

Before running any pentest template, blhackbox requires an **active verification document** — explicit written authorization confirming you have permission to test the target. Without it, Claude Code will refuse to execute offensive actions.

### How it works

```
verification.env              You fill in engagement details (target, scope,
      │                       testing window, authorized activities, signatory)
      │
      ▼
inject_verification.py        Renders the template with your values
      │
      ▼
verification.md               Template with {{PLACEHOLDER}} tokens
      │
      ▼
.claude/verification-         Active document loaded into Claude Code session.
  active.md                   Automatically appended to every pentest template.
```

When you load a pentest template (via the `get_template` MCP tool), the active verification document is automatically appended as authorization context. If none exists, Claude will prompt you to set one up.

### Step-by-step setup

**1. Edit `verification.env`** in the project root:

```bash
nano verification.env    # or vim, code, etc.
```

Fill in **all** fields across the 6 sections:

| Section | Fields |
|:--|:--|
| **Engagement ID** | `ENGAGEMENT_ID`, `AUTHORIZATION_DATE`, `EXPIRATION_DATE`, `AUTHORIZING_ORGANIZATION`, `TESTER_NAME`, `TESTER_EMAIL`, `CLIENT_CONTACT_NAME`, `CLIENT_CONTACT_EMAIL` |
| **Scope** | `TARGET_1` through `TARGET_3` (with `_TYPE` and `_NOTES`), `OUT_OF_SCOPE`, `ENGAGEMENT_TYPE`, `CREDENTIALS` |
| **Activities** | Toggle each `PERMIT_*` field (`x` = allowed, blank = denied): recon, scanning, enumeration, exploitation, data extraction, credential testing, post-exploitation, traffic capture, screenshots |
| **Testing Window** | `TESTING_START`, `TESTING_END`, `TIMEZONE`, `EMERGENCY_CONTACT`, `EMERGENCY_PHONE` |
| **Legal** | `APPLICABLE_STANDARDS`, `REPORT_CLASSIFICATION`, `REPORT_DELIVERY` |
| **Signature** | `SIGNATORY_NAME`, `SIGNATORY_TITLE`, `SIGNATORY_ORGANIZATION`, `SIGNATURE_DATE`, `DIGITAL_SIGNATURE` |

**2. Activate** — set the status field:

```bash
AUTHORIZATION_STATUS=ACTIVE
```

**3. Inject** — render the active document:

```bash
make inject-verification
```

Or directly: `python -m blhackbox.prompts.inject_verification`

On success:

```
Verification document activated → .claude/verification-active.md
Engagement: PENTEST-2026-001
Targets: example.com, 10.0.0.0/24
Window: 2026-03-01 09:00 — 2026-03-31 17:00 UTC
Authorized by: Jane Smith
```

**4. Start your session** — Claude Code will automatically pick up the verification document. On Claude Code Web, the session-start hook runs `inject-verification` automatically if `verification.env` exists.

### Validation rules

The injection script validates before rendering:

- `AUTHORIZATION_STATUS` must be `ACTIVE`
- All required fields must be filled (`ENGAGEMENT_ID`, `AUTHORIZATION_DATE`, `EXPIRATION_DATE`, `AUTHORIZING_ORGANIZATION`, `TESTER_NAME`, `TARGET_1`, `TESTING_START`, `TESTING_END`, `SIGNATORY_NAME`, `SIGNATURE_DATE`)
- `EXPIRATION_DATE` must not be in the past

If any check fails, the script exits with an error explaining what to fix.

### Files involved

| File | Purpose |
|:--|:--|
| `verification.env` | User-fillable config with engagement details, scope, and permissions |
| `blhackbox/prompts/verification.md` | Template with `{{PLACEHOLDER}}` tokens |
| `blhackbox/prompts/inject_verification.py` | Renders the template into the active document |
| `.claude/verification-active.md` | Rendered active authorization (git-ignored) |

### Example: self-authorized lab testing

For testing your own assets (lab, CTF, etc.):

```bash
# In verification.env:
AUTHORIZATION_STATUS=ACTIVE
ENGAGEMENT_ID=LAB-2026-001
AUTHORIZATION_DATE=2026-03-09
EXPIRATION_DATE=2026-12-31
AUTHORIZING_ORGANIZATION=My Lab
TESTER_NAME=Your Name
TESTER_EMAIL=you@example.com
TARGET_1=192.168.1.0/24
TARGET_1_TYPE=network
TARGET_1_NOTES=Home lab network
TESTING_START=2026-03-09 00:00
TESTING_END=2026-12-31 23:59
SIGNATORY_NAME=Your Name
SIGNATORY_TITLE=Asset Owner
SIGNATORY_ORGANIZATION=My Lab
SIGNATURE_DATE=2026-03-09
DIGITAL_SIGNATURE=SELF-AUTHORIZED
```

Then run `make inject-verification` and start your Claude Code session.

---

## Security Notes

- **Docker socket** — MCP Gateway (optional) and Portainer mount `/var/run/docker.sock`. This grants effective root on the host. Never expose ports 8080 or 9443 to the public internet.
- **Authorization** — Set up a [verification document](#authorization--verification) before running any pentest. Claude Code will not execute offensive actions without active authorization. The rendered document (`.claude/verification-active.md`) is git-ignored.
- **Neo4j** — Set a strong password in `.env`. Never use defaults in production.
- **Portainer** — Uses HTTPS with a self-signed certificate. Create a strong admin password on first run.

---

## Project Structure

```
blhackbox/
├── setup.sh                             Interactive setup wizard
├── .claude/
│   ├── settings.json                    Claude Code hooks config
│   ├── verification-active.md           Rendered authorization (git-ignored)
│   └── hooks/
│       └── session-start.sh             Auto-setup for web sessions
├── output/                              Host-accessible outputs (git-ignored)
│   ├── reports/                         Generated pentest reports
│   ├── screenshots/                     PoC evidence captures
│   └── sessions/                        Aggregated session JSONs
├── verification.env                     Pentest authorization config
├── .mcp.json                            MCP server config (Claude Code Web)
├── docker/
│   ├── kali-mcp.Dockerfile              Kali Linux + Metasploit Framework
│   ├── wire-mcp.Dockerfile
│   ├── screenshot-mcp.Dockerfile
│   ├── claude-code.Dockerfile           MCP client container
│   └── claude-code-entrypoint.sh        Startup script with health checks
├── kali-mcp/                            Kali MCP server (70+ tools + Metasploit)
├── wire-mcp/                            WireMCP server (tshark, 7 tools)
├── screenshot-mcp/                      Screenshot MCP server (Playwright, 4 tools)
├── blhackbox/
│   ├── mcp/
│   │   └── server.py                    blhackbox MCP server (stdio)
│   ├── models/
│   │   ├── aggregated_payload.py        AggregatedPayload Pydantic model
│   │   ├── base.py
│   │   └── graph.py
│   ├── prompts/
│   │   ├── claude_playbook.md           Pentest playbook for MCP host
│   │   ├── verification.md              Authorization template
│   │   └── inject_verification.py       Renders template → active document
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
├── blhackbox-mcp-catalog.yaml           MCP Gateway catalog (optional)
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
