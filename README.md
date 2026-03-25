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
| **Skills** | [Skills Overview](#skills--slash-commands) · [Available Skills](#available-skills) · [How Skills Work](#how-skills-work) |
| **Tutorials** | [Claude Code (Docker)](#tutorial-1-claude-code-docker--recommended) · [Claude Code (Web)](#tutorial-2-claude-code-web) · [Claude Desktop](#tutorial-3-claude-desktop-host--gateway) · [ChatGPT / OpenAI](#tutorial-4-chatgpt--openai-host--gateway) |
| **Advanced** | [Advanced Usage & FAQ](#advanced-usage--faq) |
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
  │                                      hydra, msfconsole, msfvenom, searchsploit…
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

## Skills / Slash Commands

Skills are native Claude Code commands that launch autonomous pentesting workflows. Instead of copy-pasting templates or editing placeholders, just type a slash command with your target.

### Available Skills

| Skill | Description | Example |
|:--|:--|:--|
| `/full-pentest` | Complete end-to-end penetration test | `/full-pentest example.com` |
| `/full-attack-chain` | Maximum-impact testing with attack chain construction | `/full-attack-chain 10.0.0.0/24` |
| `/quick-scan` | Fast triage — exploits critical findings on the spot | `/quick-scan 192.168.1.100` |
| `/recon-deep` | Comprehensive attack surface mapping | `/recon-deep example.com` |
| `/web-app-assessment` | Focused web application security testing | `/web-app-assessment https://app.example.com` |
| `/network-infrastructure` | Network-level assessment with credential testing | `/network-infrastructure 10.0.0.0/24` |
| `/osint-gathering` | Passive-only intelligence collection | `/osint-gathering example.com` |
| `/vuln-assessment` | Systematic vulnerability identification and exploitation | `/vuln-assessment example.com` |
| `/api-security` | REST/GraphQL API testing (OWASP API Top 10) | `/api-security https://api.example.com` |
| `/bug-bounty` | Bug bounty hunting with exploitation-driven PoC reports | `/bug-bounty target.com` |
| `/exploit-dev` | Custom exploit development — write, test, iterate on exploit code | `/exploit-dev CVE-2021-44228 on 10.0.0.5` |

### How Skills Work

Skills live in `.claude/skills/<name>/SKILL.md`. Claude Code discovers them automatically.

**Simple skills** (single target) — pass the target directly:

```
/quick-scan example.com
```

**Multi-input skills** (bug-bounty, full-attack-chain, api-security, web-app-assessment) — Claude asks for additional details interactively:

```
/bug-bounty example.com
```

Claude will then ask:
> I need the bug bounty program details to stay in scope:
> 1. Program scope — What domains/assets are in scope?
> 2. Out-of-scope exclusions — What targets or areas are excluded?
> 3. Program rules — Any specific rules or restrictions?

This replaces the old manual placeholder editing (`[TARGET]`, `[SCOPE]`, etc.) with a conversational UX.

### Skills vs MCP Templates

| | Skills (`/slash-command`) | MCP Templates (`get_template`) |
|---|---|---|
| **Client** | Claude Code only | Any MCP client (Claude Desktop, ChatGPT) |
| **Input** | `$ARGUMENTS` + interactive prompts | `[TARGET]` placeholder replacement |
| **Invocation** | `/full-pentest example.com` | `get_template("full-pentest", target="example.com")` |
| **Docker** | Mounted into claude-code container | Served via blhackbox MCP server |

Both paths coexist. Skills are the preferred UX for Claude Code users. MCP templates remain available for Claude Desktop and ChatGPT via the gateway.

---

## Components

| Container | Description | Port | Profile |
|:--|:--|:--:|:--:|
| **Kali MCP** | Kali Linux security tools + Metasploit — 70+ tools (nmap, sqlmap, hydra, msfconsole, msfvenom, searchsploit, etc.) | `9001` | default |
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
| `output/reports/` | `./output/reports/` | Generated pentest reports (Markdown, PDF) |
| `output/screenshots/` | `./output/screenshots/` | Screenshot MCP captures and annotations (read-only in Claude Code) |
| `output/sessions/` | `./output/sessions/` | `AggregatedPayload` session JSONs |

> **Path convention:** Inside the Claude Code container, use `output/reports/`, `output/sessions/`, etc. (relative to the working directory). These are symlinked to the bind-mounted paths (`/root/reports/`, `/root/results/`, `/tmp/screenshots/`) so files appear on the host automatically. Direct paths like `/root/reports/` also work.

Additionally, a shared Docker volume (`shared-output`) connects Kali MCP and Claude Code:

| Container | Mount Path | Access | Purpose |
|:--|:--|:--:|:--|
| Kali MCP | `/root/output/` | read-write | Tool output files (recon data, payloads) |
| Claude Code | `/root/kali-data/` | read-only | Access Kali's recon artifacts |

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

## Advanced Features

### Exploit Development (`/exploit-dev`)

A dedicated workflow for writing custom exploit code — inspired by PentAGI's Coder agent. Instead of just running scanners, Claude enters "developer mode" to write, test, and iterate on exploit code inside the Kali container.

```
/exploit-dev CVE-2021-44228 on 10.0.0.5:8080
```

The workflow: research the vulnerability → search ExploitDB and Metasploit → design the exploit → write Python/bash code → test in the Kali container → iterate on failures → capture evidence. See `.claude/skills/exploit-dev/SKILL.md`.

### ExploitDB Search (`search_exploits` / `get_exploit_code`)

Kali MCP now includes dedicated tools for searching ExploitDB via `searchsploit`:

- **`search_exploits`** — Search ExploitDB for known exploits, shellcode, and papers. Returns structured JSON with titles, paths, platforms, and dates.
- **`get_exploit_code`** — Read the full source code of an ExploitDB exploit. Useful for understanding and adapting public exploits.

These complement `msf_search` (Metasploit modules) for comprehensive exploit coverage.

### Loop Detection & Agent Supervision

A `PreToolUse` hook (`.claude/hooks/loop-detector.sh`) tracks MCP tool calls per session and detects when the AI gets stuck in a loop — inspired by PentAGI's Reflector agent.

- **Warns** when the same tool is called 3 times with identical arguments
- **Blocks** at 4 identical calls with instructions to reassess
- **Session checkpoints** at 50 and 80 total MCP calls to prompt aggregation

### Automatic Knowledge Graph Population

When Neo4j is enabled (`--profile neo4j`), `aggregate_results` now automatically creates graph nodes for every host, service, vulnerability, subdomain, and endpoint from the `AggregatedPayload`. Previously, only a flat session node was stored.

The graph enables cross-session queries like:
```cypher
MATCH (d:Domain)-[:RESOLVES_TO]->(ip)-[:HAS_PORT]->(p)-[:RUNS_SERVICE]->(s)
WHERE d.name = 'example.com'
RETURN ip, p, s
```

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

The entrypoint script checks each service and shows a status dashboard with available skills.

You are now inside an interactive Claude Code session.

### Step 3 — Verify the connection

```
/mcp
```

You should see `kali`, `wireshark`, and `screenshot`, each with their available tools.

### Step 4 — Run your first pentest

Use a skill (slash command) with your target:

```
/quick-scan example.com
```

Or for a full engagement:

```
/full-pentest example.com
```

Claude Code will autonomously:

1. Call Kali tools (nmap, subfinder, nikto, sqlmap, msfconsole, etc.)
2. Capture network traffic and extract credentials via WireMCP
3. Take screenshot evidence via Screenshot MCP
4. Structure, deduplicate, and correlate findings into an `AggregatedPayload`
5. Validate via `aggregate_results()` and write a structured pentest report

See [Available Skills](#available-skills) for all 11 pentesting workflows.

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
2. The session-start hook auto-installs dependencies and injects verification
3. Type `/mcp` to verify — you should see `blhackbox` with its tools
4. Use a skill: `/quick-scan example.com`

Skills (`.claude/skills/`) are automatically available in web sessions since they're checked into the repo.

> **Note:** The web session uses the blhackbox stdio MCP server (not the Docker stack). For the full Docker stack with Kali tools, Metasploit, WireMCP, and Screenshot MCP, use [Tutorial 1](#tutorial-1-claude-code-docker--recommended).

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

## Advanced Usage & FAQ

### How do I run a full pentest from start to finish?

```
/full-pentest example.com
```

This single command triggers a 6-phase autonomous workflow: passive recon, active scanning, web enumeration, exploitation with data extraction, data aggregation into `AggregatedPayload`, and professional report generation. Claude handles everything — tool selection, evidence collection, PoC creation, and the final report.

### How do I run a bug bounty hunt with scope restrictions?

```
/bug-bounty target.com
```

Claude will ask you interactively for the program scope, out-of-scope exclusions, and program rules before starting. It filters all discovered assets against your scope and only tests in-scope targets.

### How do I test an API with authentication?

```
/api-security https://api.example.com/v1
```

Claude will ask if you have API documentation (Swagger/OpenAPI URL), an API key, or auth tokens. Provide what you have — Claude adapts the assessment accordingly, testing both authenticated and unauthenticated paths.

### How do I chain a recon into a full pentest?

Run recon first, then follow up with the full pentest using the same target:

```
/recon-deep example.com
```

Review the recon report, then:

```
/full-pentest example.com
```

The full pentest will independently rediscover the attack surface and go deeper into exploitation. If you have Neo4j enabled (`--profile neo4j`), findings from both sessions are stored in the knowledge graph for cross-session correlation.

### How do I test a web app with credentials?

```
/web-app-assessment https://app.example.com
```

Claude will ask: "Do you have credentials or session tokens for authenticated testing?" Provide your cookie, auth header, or username/password. Claude tests both authenticated and unauthenticated areas.

### How do I quickly triage a new target?

```
/quick-scan 192.168.1.100
```

Quick scan runs parallel discovery (ports, subdomains, technologies, WAF detection) and immediately exploits any critical or high-severity findings it discovers. It finishes with a concise report and recommends which deeper assessment to run next.

### Can I use natural language instead of skills?

Yes. Skills are shortcuts, not requirements. You can always type free-form prompts:

```
Scan example.com for open ports, test for SQL injection on any web services found,
and write a report with PoC evidence for every finding.
```

Claude will use the MCP tools directly. Skills just give Claude a structured playbook to follow.

### How do I create my own custom skill?

Create a directory in `.claude/skills/` with a `SKILL.md` file:

```
.claude/skills/my-custom-scan/
└── SKILL.md
```

The `SKILL.md` file has YAML frontmatter and markdown instructions:

```yaml
---
name: my-custom-scan
description: Custom scan focusing on specific vulnerability class
---

# My Custom Scan

The target is: **$ARGUMENTS**

If no target was provided, ask the user for one.

## Steps
1. ...your custom methodology...
```

Claude Code will discover it automatically as `/my-custom-scan`.

### How do subdirectory CLAUDE.md files work?

The repo has directory-scoped `CLAUDE.md` files that enforce local development rules:

| File | Rules |
|:--|:--|
| `blhackbox/mcp/CLAUDE.md` | MCP tool validation, verification document handling |
| `blhackbox/models/CLAUDE.md` | `AggregatedPayload` schema contract, PoC fields mandatory |
| `blhackbox/backends/CLAUDE.md` | `shell=False` enforcement, tool allowlisting |
| `blhackbox/reporting/CLAUDE.md` | Report path conventions, WeasyPrint compatibility |

These load on-demand when Claude Code touches files in those directories. They don't bloat context for unrelated work.

### Where do reports go?

All output is stored in `./output/` on your host (bind-mounted from Docker):

```
output/
├── reports/       ← Pentest reports (.md, .pdf) organized by date
├── screenshots/   ← PoC evidence screenshots (.png)
└── sessions/      ← AggregatedPayload session JSONs
```

Reports follow the naming convention: `output/reports/reports-DDMMYYYY/report-<target>-DDMMYYYY.md`

### How do I set up authorization for a lab/CTF?

Minimal self-authorized setup in `verification.env`:

```bash
AUTHORIZATION_STATUS=ACTIVE
ENGAGEMENT_ID=LAB-2026-001
AUTHORIZATION_DATE=2026-03-15
EXPIRATION_DATE=2026-12-31
AUTHORIZING_ORGANIZATION=My Lab
TESTER_NAME=Your Name
TARGET_1=192.168.1.0/24
TARGET_1_TYPE=network
TESTING_START=2026-03-15 00:00
TESTING_END=2026-12-31 23:59
SIGNATORY_NAME=Your Name
SIGNATURE_DATE=2026-03-15
```

Then: `make inject-verification`

See [Authorization & Verification](#authorization--verification) for the full setup.

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

For a minimal self-authorized lab setup, see [How do I set up authorization for a lab/CTF?](#how-do-i-set-up-authorization-for-a-labctf) in the Advanced FAQ.

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
├── CLAUDE.md                            Project-wide development rules
├── .claude/
│   ├── settings.json                    Claude Code hooks config
│   ├── verification-active.md           Rendered authorization (git-ignored)
│   ├── hooks/
│   │   ├── session-start.sh             Auto-setup for web sessions
│   │   └── loop-detector.sh             MCP tool loop detection (Reflector pattern)
│   └── skills/                          Pentesting skill slash commands
│       ├── full-pentest/SKILL.md        /full-pentest
│       ├── full-attack-chain/SKILL.md   /full-attack-chain
│       ├── quick-scan/SKILL.md          /quick-scan
│       ├── recon-deep/SKILL.md          /recon-deep
│       ├── web-app-assessment/SKILL.md  /web-app-assessment
│       ├── network-infrastructure/SKILL.md /network-infrastructure
│       ├── osint-gathering/SKILL.md     /osint-gathering
│       ├── vuln-assessment/SKILL.md     /vuln-assessment
│       ├── api-security/SKILL.md        /api-security
│       ├── bug-bounty/SKILL.md          /bug-bounty
│       └── exploit-dev/SKILL.md         /exploit-dev
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
│   │   ├── server.py                    blhackbox MCP server (stdio)
│   │   └── CLAUDE.md                    MCP development rules
│   ├── models/
│   │   ├── aggregated_payload.py        AggregatedPayload Pydantic model
│   │   ├── base.py, graph.py
│   │   └── CLAUDE.md                    Schema contract rules
│   ├── backends/
│   │   ├── local.py                     CLI tool execution backend
│   │   └── CLAUDE.md                    Backend safety rules (shell=False)
│   ├── prompts/
│   │   ├── templates/                   11 pentest template .md files
│   │   ├── claude_playbook.md           Pentest playbook for MCP host
│   │   ├── verification.md              Authorization template
│   │   └── inject_verification.py       Renders template → active document
│   ├── reporting/
│   │   ├── html_generator.py, pdf_generator.py, md_generator.py
│   │   └── CLAUDE.md                    Reporting path conventions
│   ├── core/                            Knowledge graph, exporters
│   ├── modules/                         Custom analysis modules
│   ├── utils/                           Logging, tool catalog
│   ├── data/                            tools_catalog.json
│   ├── main.py                          CLI interface
│   ├── config.py                        Centralized settings
│   └── exceptions.py                    Custom exception hierarchy
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
