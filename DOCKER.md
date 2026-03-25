# BLHACKBOX — Docker Reference

**MCP-based Autonomous Pentesting Framework**

---

## Quick Reference

All custom images are published to a single Docker Hub repository, differentiated by tag.

| | |
|:--|:--|
| **Repository** | [`crhacky/blhackbox`](https://hub.docker.com/r/crhacky/blhackbox) |
| **Registry** | [Docker Hub](https://hub.docker.com/r/crhacky/blhackbox) |
| **Source** | [GitHub](https://github.com/valITino/blhackbox) |
| **License** | MIT |

---

## Images & Tags

Four custom images are published to `crhacky/blhackbox` on Docker Hub:

| Service | Tag | Dockerfile | Base Image |
|:--|:--|:--|:--|
| **Kali MCP** | `crhacky/blhackbox:kali-mcp` | `docker/kali-mcp.Dockerfile` | `kalilinux/kali-rolling` |
| **WireMCP** | `crhacky/blhackbox:wire-mcp` | `docker/wire-mcp.Dockerfile` | `debian:bookworm-slim` |
| **Screenshot MCP** | `crhacky/blhackbox:screenshot-mcp` | `docker/screenshot-mcp.Dockerfile` | `python:3.13-slim` |
| **Claude Code** | `crhacky/blhackbox:claude-code` | `docker/claude-code.Dockerfile` | `node:22-slim` |

Official images (pulled directly, no custom build):

| Image | Purpose |
|:--|:--|
| `portainer/portainer-ce:latest` | Docker management UI |
| `docker/mcp-gateway:latest` | MCP Gateway (optional, `--profile gateway`) |
| `neo4j:5` | Knowledge graph (optional, `--profile neo4j`) |

### Pulling Images

```bash
docker compose pull    # pull ALL images (custom + official) in one command
```

---

## Architecture

In v2, **Claude (or ChatGPT) IS the orchestrator** natively via MCP.

### Claude Code in Docker — Direct SSE (no gateway)

```
Claude Code ──┬──▶ Kali MCP (SSE :9001)
(container)   │    70+ tools: nmap, sqlmap, hydra, msfconsole, msfvenom…
              │
              ├──▶ WireMCP (SSE :9003)
              │    7 tools: packet capture, pcap analysis, credential extraction
              │
              ├──▶ Screenshot MCP (SSE :9004)
              │    4 tools: web screenshots, element capture, annotations
              │
              │  After collecting raw outputs, Claude structures them directly:
              │    get_payload_schema() → parse/dedup/correlate → aggregate_results()
              │
              ▼
output/          Host-mounted directory for reports, screenshots, sessions
Portainer        Docker UI (https://localhost:9443)
Neo4j            Cross-session memory (optional)
```

### Claude Desktop / ChatGPT — via MCP Gateway

```
Claude Desktop ──▶ MCP Gateway (localhost:8080/mcp) ──┬──▶ Kali MCP
(host app)                                             ├──▶ WireMCP
                                                       └──▶ Screenshot MCP
```

---

## Usage

### Quick Start (Recommended)

```bash
git clone https://github.com/valITino/blhackbox.git
cd blhackbox
./setup.sh    # interactive wizard: prereqs, .env, pull, start, health
```

### Manual — Core Stack (4 containers)

```bash
git clone https://github.com/valITino/blhackbox.git && cd blhackbox
cp .env.example .env
# REQUIRED: set ANTHROPIC_API_KEY=sk-ant-... in .env
mkdir -p output/reports output/screenshots output/sessions
docker compose pull
docker compose up -d
```

### With Claude Code (Recommended)

```bash
make claude-code    # builds + launches Claude Code in Docker
```

### With MCP Gateway (for Claude Desktop / ChatGPT)

```bash
make up-gateway     # starts core + gateway on port 8080
```

### With Neo4j

```bash
docker compose --profile neo4j up -d
```

### Verify

```bash
make status         # container status table
make health         # MCP server health check
```

---

## Skills in Docker

The Claude Code container has full access to blhackbox skills — autonomous pentesting workflows invoked as slash commands.

### Quick start with skills

```bash
make claude-code                  # launch Claude Code in Docker
```

Then inside the session:

```
/quick-scan example.com           # fast triage scan
/full-pentest 10.0.0.1            # complete penetration test
/bug-bounty target.com            # bug bounty hunt (asks for scope interactively)
/api-security https://api.ex.com  # API security assessment
```

### How skills are mounted

Skills are available in the container via two mechanisms:

1. **Baked in** — `COPY .claude/skills /root/.claude/skills` in the Dockerfile ensures skills exist even when running the image standalone
2. **Volume mount** — `docker-compose.yml` mounts `./.claude/skills:/root/.claude/skills:ro` so edits to skills on the host are reflected immediately without rebuilding

### Available skills

| Skill | What it does |
|:--|:--|
| `/full-pentest` | Complete end-to-end penetration test (6 phases) |
| `/full-attack-chain` | Maximum-impact testing with attack chain construction |
| `/quick-scan` | Fast triage — exploits critical/high findings on the spot |
| `/recon-deep` | Comprehensive attack surface mapping (no exploitation) |
| `/web-app-assessment` | Focused web application security testing (OWASP Top 10) |
| `/network-infrastructure` | Network-level assessment with credential testing |
| `/osint-gathering` | Passive-only intelligence collection |
| `/vuln-assessment` | Systematic vulnerability identification and exploitation |
| `/api-security` | REST/GraphQL API testing (OWASP API Top 10) |
| `/bug-bounty` | Bug bounty hunting with exploitation-driven PoC reports |
| `/exploit-dev` | Custom exploit development — write, test, iterate on exploit code |

> **Note:** Skills are a Claude Code feature. Claude Desktop and ChatGPT use MCP templates via the gateway instead (`get_template` / `list_templates` tools).

---

## Compose Services

| Service | Image | Port | Profile | Role |
|:--|:--|:--:|:--:|:--|
| `kali-mcp` | `crhacky/blhackbox:kali-mcp` | `9001` | default | Kali Linux security tools + Metasploit (70+) |
| `wire-mcp` | `crhacky/blhackbox:wire-mcp` | `9003` | default | Wireshark / tshark (7 tools) |
| `screenshot-mcp` | `crhacky/blhackbox:screenshot-mcp` | `9004` | default | Screenshot MCP (headless Chromium, 4 tools) |
| `portainer` | `portainer/portainer-ce:latest` | `9443` | default | Docker management UI (HTTPS) |
| `claude-code` | `crhacky/blhackbox:claude-code` | — | `claude-code` | Claude Code CLI client (Docker) |
| `mcp-gateway` | `docker/mcp-gateway:latest` | `8080` | `gateway` | Single MCP entry point (host clients) |
| `neo4j` | `neo4j:5` | `7474` / `7687` | `neo4j` | Cross-session knowledge graph |

---

## MCP Connection Modes

### Claude Code in Docker (Direct SSE — no gateway)

The Claude Code container's `.mcp.json` connects directly to each server:

```json
{
  "mcpServers": {
    "kali":       { "type": "sse", "url": "http://kali-mcp:9001/sse" },
    "wireshark":  { "type": "sse", "url": "http://wire-mcp:9003/sse" },
    "screenshot": { "type": "sse", "url": "http://screenshot-mcp:9004/sse" }
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
|:--|:--|:--|
| `ANTHROPIC_API_KEY` | — | Required for Claude Code in Docker |
| `MCP_GATEWAY_PORT` | `8080` | MCP Gateway host port (optional) |
| `MSF_TIMEOUT` | `300` | Metasploit command timeout in seconds |
| `NEO4J_URI` | `bolt://neo4j:7687` | Neo4j connection URI (optional) |
| `NEO4J_USER` | `neo4j` | Neo4j username (optional) |
| `NEO4J_PASSWORD` | — | Neo4j password, min 8 chars (optional) |
| `SCREENSHOT_MCP_PORT` | `9004` | Screenshot MCP server port |
| `OPENAI_API_KEY` | — | For OpenAI MCP clients (optional) |

---

## Image Details

### Kali MCP — `crhacky/blhackbox:kali-mcp`

| | |
|:--|:--|
| **Base** | `kalilinux/kali-rolling` |
| **Transport** | SSE on port 9001 |
| **Privileged** | Yes (raw socket access) |
| **Entrypoint** | `entrypoint.sh` (starts PostgreSQL for MSF DB, then MCP server) |

**Tools (70+):** nmap, masscan, hping3, subfinder, amass, fierce, dnsenum, dnsrecon, theharvester, nikto, gobuster, dirb, dirsearch, ffuf, feroxbuster, whatweb, wafw00f, wpscan, arjun, dalfox, sqlmap, hydra, medusa, john, hashcat, crackmapexec, evil-winrm, enum4linux-ng, responder, netexec, aircrack-ng, bettercap, binwalk, foremost, exiftool, steghide, curl, wget, netcat, socat, **msfconsole**, **msfvenom**, and more.

**Metasploit:** Integrated via CLI (`msfconsole -qx`) — no msfrpcd daemon needed. Includes PostgreSQL for Metasploit DB support.

**MCP Tools:** `run_kali_tool`, `run_shell_command`, `list_available_tools`, `msf_search`, `msf_module_info`, `msf_run_module`, `msf_payload_generate`, `msf_console_execute`, `msf_status`

### WireMCP — `crhacky/blhackbox:wire-mcp`

| | |
|:--|:--|
| **Base** | `debian:bookworm-slim` |
| **Transport** | SSE on port 9003 |
| **Privileged** | Yes (packet capture) |
| **Entrypoint** | WireMCP server (`server.py`) |

**Tools (7):** `capture_packets`, `read_pcap`, `get_conversations`, `get_statistics`, `extract_credentials`, `follow_stream`, `list_interfaces`

**Inspired by:** [0xKoda/WireMCP](https://github.com/0xKoda/WireMCP), [khuynh22/mcp-wireshark](https://github.com/khuynh22/mcp-wireshark)

### Screenshot MCP — `crhacky/blhackbox:screenshot-mcp`

| | |
|:--|:--|
| **Base** | `python:3.13-slim` |
| **Transport** | SSE on port 9004 |
| **Entrypoint** | Screenshot MCP server (FastMCP + Playwright headless Chromium) |

**Tools (4):** `take_screenshot` (full-page web capture), `take_element_screenshot` (CSS selector targeting), `annotate_screenshot` (labels and highlight boxes), `list_screenshots` (evidence inventory)

### Claude Code — `crhacky/blhackbox:claude-code`

| | |
|:--|:--|
| **Base** | `node:22-slim` |
| **Entrypoint** | `claude-code-entrypoint.sh` (health checks + launch) |
| **MCP config** | Direct SSE to each server (no gateway dependency) |
| **Skills** | 11 pentesting skills mounted from `.claude/skills/` |
| **Requires** | `ANTHROPIC_API_KEY` in `.env` |

The Claude Code container includes the full skills system. Skills (`.claude/skills/`) and project instructions (`CLAUDE.md`) are baked into the image at build time and overridden by volume mounts at runtime for live updates.

---

## Portainer

Portainer CE provides a web dashboard for all blhackbox containers.

| | |
|:--|:--|
| **URL** | `https://localhost:9443` |
| **First run** | Create an admin account within 5 minutes of startup |
| **Missed the window?** | `docker compose restart portainer` |

> **Note:** Your browser will warn about the self-signed HTTPS certificate. This is expected — click "Advanced" and proceed.

---

## Volumes

### Named volumes (persistent data)

| Volume | Service | Purpose |
|:--|:--|:--|
| `neo4j_data` | neo4j | Neo4j graph database (optional) |
| `neo4j_logs` | neo4j | Neo4j logs (optional) |
| `portainer_data` | portainer | Portainer configuration |
| `wordlists` | — | Fuzzing wordlists |

### Host bind mounts (accessible on your local filesystem)

| Host Path | Container Path | Contents |
|:--|:--|:--|
| `./output/reports/` | `/root/reports/` | Generated pentest reports (.md, .pdf) |
| `./output/screenshots/` | `/tmp/screenshots/` | PoC evidence screenshots (.png) |
| `./output/sessions/` | `/root/results/` | Aggregated session JSON files |
| `./.claude/skills/` | `/root/.claude/skills/` | Pentesting skills (read-only, claude-code only) |
| `./CLAUDE.md` | `/root/CLAUDE.md` | Project instructions (read-only, claude-code only) |

---

## CI/CD Pipeline

Four custom images are built and pushed to Docker Hub via GitHub Actions:

```
PR opened  ─────▶  CI (lint + test + pip-audit)
                        │
PR merged  ─────▶  CI  ─────▶  Build & Push (4 images)  ─────▶  Docker Hub
                                (on CI success)

Tag v*     ──────────────────▶  Build & Push (4 images)  ─────▶  Docker Hub

Manual     ──────────────────▶  Build & Push (4 images)  ─────▶  Docker Hub
```

---

## Useful Commands

```bash
make setup              # Interactive setup wizard (first-time setup)
docker compose pull     # Pull all pre-built images
docker compose up -d    # Start core stack (4 containers)
make up-gateway         # Start with MCP Gateway (5 containers)
make claude-code        # Launch Claude Code in Docker
make health             # Health check all MCP servers
make status             # Container status table
make logs-kali          # Kali MCP logs
make logs-wireshark     # WireMCP logs
make logs-screenshot    # Screenshot MCP logs
make gateway-logs       # MCP Gateway logs
make down               # Stop all services
make clean              # Stop + remove volumes
```

---

## Security

- **Docker socket** — MCP Gateway (optional) and Portainer mount `/var/run/docker.sock`. This grants effective root on the host. Never expose ports 8080 or 9443 to the public internet.
- **Authorization** — Ensure you have written permission before scanning any target.
- **Neo4j** — Set a strong password in `.env`. Never use defaults in production.
- **Portainer** — Uses HTTPS with a self-signed certificate. Create a strong admin password on first run.

> **This tool is for authorized security testing only.** Unauthorized access to computer systems is illegal.

---

## Source

[GitHub Repository](https://github.com/valITino/blhackbox) · [Docker Hub](https://hub.docker.com/r/crhacky/blhackbox)
