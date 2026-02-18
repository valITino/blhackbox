# BLHACKBOX v2.0.0

[![CI](https://github.com/crhacky/blhackbox/actions/workflows/ci.yml/badge.svg)](https://github.com/crhacky/blhackbox/actions/workflows/ci.yml)
[![Docker](https://github.com/crhacky/blhackbox/actions/workflows/build-and-push.yml/badge.svg)](https://github.com/crhacky/blhackbox/actions/workflows/build-and-push.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Docker Hub](https://img.shields.io/docker/v/crhacky/blhackbox?label=Docker%20Hub&sort=semver)](https://hub.docker.com/r/crhacky/blhackbox)

**HexStrike Hybrid Autonomous Pentesting Framework**

Blhackbox is an intelligent orchestration and correlation layer that sits on top of [HexStrike AI MCP Server](https://github.com/0x4m4/hexstrike-ai). It adds autonomous planning via AI (LLM-powered), a persistent knowledge graph (Neo4j), and professional reporting capabilities to HexStrike's 150+ security tools and 12+ AI agents.

> HexStrike provides the tools. Blhackbox provides the brain.

---

## Legal Disclaimer

**This tool is intended for authorized security testing only.** You must have explicit written permission from the target owner before running any scans. Unauthorized access to computer systems is illegal and punishable by law. The developers assume no liability for misuse of this software.

---

## Table of Contents

- [Architecture](#architecture)
- [What Blhackbox Adds](#what-blhackbox-adds)
- [Quick Start](#quick-start)
- [CLI Reference](#cli-reference)
- [Makefile Shortcuts](#makefile-shortcuts)
- [Project Structure](#project-structure)
- [Adding Custom Modules](#adding-custom-modules)
- [Configuration](#configuration)
- [Testing](#testing)
- [CI/CD](#cicd)
- [Ethical Safeguards](#ethical-safeguards)
- [Contributing](#contributing)
- [License](#license)

---

## Architecture

```
┌─────────────────┐     ┌─────────────────────────────────────┐
│   AI Client     │     │         Blhackbox Layer              │
│ (Claude/Cursor) │────>│  ┌─────────────────────────────┐    │
└─────────────────┘     │  │   LangGraph Orchestrator     │    │
                        │  │   (plan -> execute -> analyze)│    │
                        │  └──────────────┬──────────────┘    │
                        │                 v                    │
                        │  ┌─────────────────────────────┐    │
                        │  │    Knowledge Graph (Neo4j)   │    │
                        │  │   Persistent attack surface  │    │
                        │  └──────────────┬──────────────┘    │
                        │                 v                    │
                        │  ┌─────────────────────────────┐    │
                        │  │   HexStrike API Client       │    │
                        │  │   + Custom Module Bridge     │    │
                        │  └──────────────┬──────────────┘    │
                        │                 │                    │
                        │  ┌─────────────────────────────┐    │
                        │  │   Reporting Engine           │    │
                        │  │   (PDF + HTML)               │    │
                        │  └─────────────────────────────┘    │
                        └─────────────────┼───────────────────┘
                                          v
                        ┌─────────────────────────────────────┐
                        │     HexStrike MCP Server            │
                        │  (150+ tools, 12+ AI agents)        │
                        └─────────────────────────────────────┘
```

### Orchestrator Flow

The LangGraph state machine follows this cycle:

```
gather_state -> plan -> execute -> analyze -> decide (continue / stop)
```

Each iteration queries the knowledge graph for context, uses the LLM planner to decide the next action, executes it via HexStrike, stores results back in the graph, and decides whether to continue or stop (up to `MAX_ITERATIONS`).

---

## What Blhackbox Adds

| Capability | Description |
|---|---|
| **Knowledge Graph** | Neo4j-powered persistent attack surface model with nodes for domains, IPs, ports, services, findings, and vulnerabilities |
| **AI Orchestrator** | LangGraph-based autonomous tool/agent selection with multi-provider LLM support (OpenAI, Anthropic, Ollama) |
| **Professional Reporting** | PDF and HTML reports with dark theme, interactive findings tables, and severity distribution charts |
| **Custom Module Bridge** | Extend HexStrike with custom Python modules without modifying the upstream project |
| **Tools Catalog** | Built-in catalog of 67+ tools across network, web, DNS, and intelligence categories |

---

## Quick Start

### Prerequisites

#### System Requirements

- **Python** >= 3.11 (3.13 used in Docker image)
- **Docker** and **Docker Compose** v2+
- **Git** (with submodule support)

> For detailed Docker setup, image tags, volumes, and troubleshooting, see [DOCKER.md](DOCKER.md).

#### Neo4j Aura (Knowledge Graph Database)

Blhackbox uses Neo4j as its persistent knowledge graph. You need a Neo4j instance — the easiest option is the free **Neo4j Aura** cloud tier:

1. **Create a Neo4j Aura account** at [console.neo4j.io](https://console.neo4j.io/) — sign up with email, Google, or GitHub
2. **Create a free AuraDB instance:**
   - Click **"New Instance"** in the Aura console
   - Select the **Free** tier (no credit card required)
   - Choose a region close to you
   - Set the instance name (e.g., `Blhackbox`)
3. **Save your credentials immediately** — the auto-generated password is shown **only once** at creation time:
   - **Connection URI** — e.g., `neo4j+s://xxxxxxxx.databases.neo4j.io`
   - **Username** — typically `neo4j`
   - **Password** — the generated password (store it securely)
   - **Instance ID** — shown in the Aura console dashboard
4. **Wait for the instance to be ready** (usually under a minute), then copy the connection details into your `.env` file

> **Alternatively**, you can use the local Neo4j Docker container included in `docker-compose.yml` — no Aura account required. Just set `NEO4J_URI=bolt://blhackbox-neo4j:7687` and a strong `NEO4J_PASSWORD` in your `.env`.

#### OpenAI Account (ChatGPT / GPT API)

An OpenAI API key is required if you want to use OpenAI models (default provider) for the AI orchestrator:

1. **Create an OpenAI account** at [platform.openai.com](https://platform.openai.com/)
2. **Add billing** — go to **Settings > Billing** and add a payment method (API usage is pay-per-use)
3. **Generate an API key** — go to **API Keys** ([platform.openai.com/api-keys](https://platform.openai.com/api-keys)), click **"Create new secret key"**, and copy it
4. **Paste the key** into your `.env` file as `OPENAI_API_KEY`
5. **Default model:** `o3` (OpenAI's most capable reasoning model)

> Note: The `o3` model requires Tier 3+ API access. If you don't have access, set `OPENAI_MODEL=gpt-4o` as a fallback.

#### Anthropic Account (Claude API)

An Anthropic API key is required if you want to use Claude models for the AI orchestrator:

1. **Create an Anthropic account** at [console.anthropic.com](https://console.anthropic.com/)
2. **Add billing** — go to **Settings > Billing** and add a payment method
3. **Generate an API key** — go to **API Keys** ([console.anthropic.com/settings/keys](https://console.anthropic.com/settings/keys)), click **"Create Key"**, and copy it
4. **Paste the key** into your `.env` file as `ANTHROPIC_API_KEY`
5. **Default model:** `claude-opus-4-20250514` (Anthropic's most capable model)

#### Ollama (Optional — Local LLM)

For offline or free local inference, you can use Ollama instead of cloud providers:

1. **No account required** — Ollama runs entirely locally
2. Ollama starts automatically with `docker compose up -d` (included in the default stack)
3. Pull a model: `make ollama-pull` (defaults to `llama3.3`)
4. **Default model:** `llama3.3`

> **Provider priority:** By default, Blhackbox tries providers in this order: `openai → anthropic → ollama`. You only need **at least one** configured provider for the AI orchestrator. You can change the priority via `LLM_PROVIDER_PRIORITY` in `.env`.

---

### Option A — Docker Pull (quickest)

Pull the pre-built image directly from Docker Hub — no clone required:

```bash
docker pull crhacky/blhackbox:latest

# Verify the image works
docker run --rm crhacky/blhackbox --help
docker run --rm crhacky/blhackbox version
```

> This gives you the CLI image only. For the full stack (Neo4j, HexStrike, Ollama, MCP Gateway), use Option B.

### Option B — Clone and Build (full stack)

#### 1. Clone and initialise

```bash
git clone https://github.com/crhacky/blhackbox.git
cd blhackbox
git submodule update --init --recursive
```

#### 2. Configure environment

```bash
cp .env.example .env
```

Edit `.env` and fill in your credentials:

```bash
# Neo4j — use your Aura connection details or keep defaults for local Docker
NEO4J_URI=neo4j+s://xxxxxxxx.databases.neo4j.io   # Aura URI (or bolt://blhackbox-neo4j:7687 for local)
NEO4J_USER=neo4j
NEO4J_PASSWORD=your-neo4j-password                 # REQUIRED — min 8 characters
NEO4J_DATABASE=neo4j
AURA_INSTANCEID=your-aura-instance-id              # from Aura console (optional)
AURA_INSTANCENAME=Blhackbox                        # your instance name (optional)

# At least one LLM provider API key
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
```

#### 3. Build and run

```bash
make build       # Build the blhackbox CLI image
make up          # Start infrastructure (Neo4j, Ollama, MCP Gateway, Portainer, blhackbox)
```

> **MCP servers (HexStrike, Kali, Aggregator):** By default these are managed by the MCP Gateway. To run them directly in compose instead, use `make up-direct`.

#### 4. Run your first recon

```bash
# Enter the blhackbox container
make shell

# Run reconnaissance (--authorized is mandatory)
blhackbox recon --target example.com --authorized

# Or with AI orchestrator (requires LLM API key)
blhackbox recon --target example.com --authorized --ai

# Run specific attack tools
blhackbox recon --target example.com --authorized --attacks "network/nmap,web/nuclei"

# Run all tools in order
blhackbox recon --target example.com --authorized --full
```

---

## CLI Reference

### Version and Catalog

```bash
# Show version and configuration
blhackbox version

# Display the full HexStrike tools catalog
blhackbox catalog
```

### Reconnaissance

```bash
# Basic recon via HexStrike intelligence
blhackbox recon --target <domain> --authorized

# AI-driven autonomous recon
blhackbox recon --target <domain> --authorized --ai

# Run specific tools
blhackbox recon --target <domain> --authorized --attacks "network/nmap,web/nuclei"

# Run all available tools sequentially
blhackbox recon --target <domain> --authorized --full

# Save output to a specific path
blhackbox recon --target <domain> --authorized --output ./results/scan.json
```

### Run Individual Tools

```bash
blhackbox run-tool \
  --category network \
  --tool nmap \
  --params '{"target": "example.com", "flags": ["-F"]}' \
  --authorized
```

### Agents

```bash
# List available HexStrike agents
blhackbox agents list

# Run a specific agent
blhackbox agents run --name bug_bounty --target example.com --authorized
```

### Knowledge Graph

```bash
# Execute a Cypher query
blhackbox graph query "MATCH (d:Domain) RETURN d LIMIT 10"

# Show summary for a target
blhackbox graph summary --target example.com
```

### Reporting

```bash
# Generate PDF report from session
blhackbox report --session <session-id> --format pdf

# Generate HTML report
blhackbox report --session <session-id> --format html
```

### Debug Mode

```bash
blhackbox --debug <command>   # Enable debug logging for any command
```

---

## Makefile Shortcuts

```bash
make help            # Show all available targets
make build           # Build Docker containers
make up              # Start services (detached)
make down            # Stop services
make logs            # Tail logs from all services
make logs-blhackbox  # Tail blhackbox logs only
make logs-hexstrike  # Tail hexstrike logs only
make shell           # Open a shell in the blhackbox container
make test            # Run tests in Docker
make test-local      # Run tests locally
make lint            # Ruff linting
make format          # Auto-format code
make clean           # Remove containers, volumes, and build artifacts
make reset-graph     # Reset the Neo4j knowledge graph
make wordlists       # Download common SecLists wordlists
make recon TARGET=example.com  # Quick recon (pass target via env var)
make report SESSION=<id>       # Generate PDF report for a session
```

---

## Project Structure

```
blhackbox/
├── .github/workflows/
│   ├── ci.yml                       # Lint, test, and pip-audit
│   └── build-and-push.yml           # Docker image build and push to Docker Hub
├── docker/                          # Dockerfiles (one per service)
│   ├── blhackbox.Dockerfile         # Multi-stage CLI image (Python 3.13)
│   ├── hexstrike.Dockerfile         # HexStrike MCP Server image
│   ├── aggregator.Dockerfile        # Aggregator MCP Server image
│   └── kali-mcp.Dockerfile          # Kali Linux MCP Server image
├── docker-compose.yml               # Full stack orchestration (8 services)
├── blhackbox-mcp-catalog.yaml       # MCP Gateway service catalog
├── blhackbox-mcp.json               # Claude Desktop MCP config (direct mode)
├── Makefile                         # Development shortcuts
├── DOCKER.md                        # Docker quick-reference guide
├── hexstrike/                       # Git submodule -> HexStrike AI
├── kali-mcp/                        # Kali Linux MCP server
│   ├── server.py                    # MCP server for Kali security tools
│   └── Dockerfile                   # Standalone build (kali-mcp context)
├── mcp_servers/                     # Custom MCP server implementations
│   └── blhackbox_aggregator_mcp.py  # Ollama preprocessing aggregator
├── blhackbox/
│   ├── __init__.py                  # Package version
│   ├── main.py                      # CLI entry point (Click)
│   ├── config.py                    # Pydantic settings
│   ├── exceptions.py                # Custom exception hierarchy
│   ├── agents/                      # AI agent implementations
│   │   ├── base_agent.py            # Abstract base agent
│   │   ├── web_agent.py             # Web reconnaissance agent
│   │   ├── vuln_agent.py            # Vulnerability analysis agent
│   │   ├── network_agent.py         # Network reconnaissance agent
│   │   ├── recon_agent.py           # General reconnaissance agent
│   │   ├── structure_agent.py       # Structure analysis agent
│   │   └── error_log_agent.py       # Error log analysis agent
│   ├── backends/                    # Execution backends
│   │   ├── base.py                  # Abstract backend base class
│   │   ├── hexstrike.py             # HexStrike backend client
│   │   └── local.py                 # Local execution backend
│   ├── clients/
│   │   └── hexstrike_client.py      # Async HexStrike HTTP client
│   ├── models/
│   │   ├── base.py                  # Target, Finding, ScanSession, Severity
│   │   ├── hexstrike.py             # HexStrike response models
│   │   ├── graph.py                 # Neo4j node/relationship models
│   │   └── aggregated_payload.py    # Aggregated payload model
│   ├── core/
│   │   ├── runner.py                # Simple scan runner
│   │   ├── knowledge_graph.py       # Neo4j async client
│   │   ├── graph_exporter.py        # HexStrike -> Neo4j translator
│   │   ├── orchestrator.py          # LangGraph state machine
│   │   ├── planner.py               # LLM-based action planner
│   │   └── exploit_generator.py     # Exploit generation module
│   ├── llm/
│   │   ├── client.py                # Multi-provider LLM client
│   │   ├── prompts.py               # System/user prompts
│   │   └── exploit_prompts.py       # Exploit-related prompts
│   ├── mcp/
│   │   └── server.py                # MCP Protocol server
│   ├── modules/
│   │   ├── base.py                  # HexStrikeModule base class
│   │   └── argus_bridge/            # Argus-inspired modules
│   │       ├── port_scan.py         # Port scanning
│   │       ├── subdomain_enum.py    # Subdomain enumeration
│   │       └── tech_detect.py       # Technology detection
│   ├── prompts/                     # LLM prompt templates
│   │   ├── claude_pentest_playbook.md
│   │   └── agents/                  # Per-agent system prompts
│   │       ├── web_agent.md
│   │       ├── vuln_agent.md
│   │       ├── network_agent.md
│   │       ├── recon_agent.md
│   │       ├── structure_agent.md
│   │       └── error_log_agent.md
│   ├── reporting/
│   │   ├── html_generator.py        # Interactive HTML reports
│   │   └── pdf_generator.py         # PDF via WeasyPrint
│   ├── utils/
│   │   ├── logger.py                # Rich logging
│   │   └── catalog.py               # Tools catalog utilities
│   └── data/
│       └── tools_catalog.json       # HexStrike tools catalog (67 entries)
├── scripts/
│   └── reset_graph.py               # Reset Neo4j database
├── tests/                           # pytest suite (53+ tests)
├── results/                         # Scan output (gitignored)
└── wordlists/                       # Fuzzing wordlists (gitignored)
```

---

## Adding Custom Modules

Create a new module by subclassing `HexStrikeModule`:

```python
from blhackbox.modules.base import HexStrikeModule
from blhackbox.models.base import Finding, Severity

class MyCustomModule(HexStrikeModule):
    name = "my_module"
    description = "Does something useful"
    category = "custom"
    version = "1.0.0"

    async def run(self, target: str, **kwargs) -> list[Finding]:
        self.clear_findings()

        # Use HexStrike tools through self._client
        result = await self._client.run_tool("web", "httpx", {"target": target})

        self.add_finding(
            target=target,
            title="My Custom Finding",
            description=str(result.output),
            severity=Severity.INFO,
        )

        return self.findings
```

See the built-in modules in `blhackbox/modules/argus_bridge/` for more examples (port scanning, subdomain enumeration, technology detection).

---

## Configuration

All settings are loaded from environment variables or `.env` via Pydantic Settings. See [`.env.example`](.env.example) for the full template.

| Variable | Default | Description |
|---|---|---|
| `HEXSTRIKE_URL` | `http://blhackbox-hexstrike:8888` | HexStrike API base URL |
| `HEXSTRIKE_TIMEOUT` | `120` | HTTP timeout (seconds) |
| `HEXSTRIKE_MAX_RETRIES` | `3` | Max retries with exponential backoff |
| `NEO4J_URI` | `bolt://blhackbox-neo4j:7687` | Neo4j connection URI (use `neo4j+s://...` for Aura) |
| `NEO4J_USER` | `neo4j` | Neo4j username |
| `NEO4J_PASSWORD` | *(required)* | Neo4j password (min 8 characters) |
| `NEO4J_DATABASE` | `neo4j` | Neo4j database name |
| `AURA_INSTANCEID` | *(optional)* | Neo4j Aura instance ID (informational) |
| `AURA_INSTANCENAME` | *(optional)* | Neo4j Aura instance name (informational) |
| `OPENAI_API_KEY` | *(optional)* | OpenAI API key for AI orchestrator |
| `OPENAI_MODEL` | `o3` | OpenAI model name (most capable reasoning model) |
| `ANTHROPIC_API_KEY` | *(optional)* | Anthropic API key for AI orchestrator |
| `ANTHROPIC_MODEL` | `claude-opus-4-20250514` | Anthropic model name (most capable Claude model) |
| `OLLAMA_URL` | `http://blhackbox-ollama:11434` | Ollama API URL (local LLM) |
| `OLLAMA_MODEL` | `llama3.3` | Ollama model name |
| `LLM_PROVIDER_PRIORITY` | `openai,anthropic,ollama` | Comma-separated fallback order |
| `MAX_ITERATIONS` | `10` | Max orchestrator iterations per session |
| `LOG_LEVEL` | `INFO` | Logging level |
| `RESULTS_DIR` | `./results` | Directory for scan output and reports |
| `WORDLISTS_DIR` | `./wordlists` | Directory for fuzzing wordlists |

---

## Testing

The test suite uses **pytest** with **pytest-asyncio** for async test support and **respx** for HTTP mocking.

### Running Tests

```bash
# Run tests locally
make test-local

# Run tests in Docker
make test

# Run with verbose output
pytest tests/ -v --tb=short

# Run with coverage
pytest tests/ --cov=blhackbox --cov-report=term-missing

# Run a specific test file
pytest tests/test_cli.py -v
```

### Test Structure

| Test File | Coverage |
|---|---|
| `test_hexstrike_client.py` | Async HTTP client, retries, error handling |
| `test_graph_exporter.py` | HexStrike-to-Neo4j translation |
| `test_reporting.py` | HTML and PDF report generation |
| `test_cli.py` | Click CLI commands and flags |
| `test_catalog.py` | Tools catalog loading and queries |
| `test_runner.py` | Tool execution runner |
| `test_config.py` | Pydantic settings and env loading |
| `test_modules.py` | Custom module base class and implementations |
| `test_planner.py` | LLM planner decision logic |
| `test_models.py` | Data model validation |
| `test_exploit.py` | Exploit generation guardrails |

---

## CI/CD

Two GitHub Actions workflows automate quality checks and image builds:

### CI Pipeline (`ci.yml`)

Runs on every push to `main`/`master` and all pull requests:

1. **Lint** — Ruff checks across `blhackbox/` and `tests/`
2. **Test** — Full pytest suite on Python 3.13
3. **Security** — `pip-audit` scans dependencies for known vulnerabilities

### Docker Build Pipeline (`build-and-push.yml`)

Triggers on merged PRs, version tags (`v*`), and manual dispatch:

1. Builds multi-stage Docker image from `docker/blhackbox.Dockerfile`
2. Runs Docker Scout vulnerability scan
3. Pushes to [Docker Hub](https://hub.docker.com/r/crhacky/blhackbox) with tags: `latest`, `x.y.z`, `x.y`, `main`, `<commit-sha>`

```bash
# Pull the latest image directly
docker pull crhacky/blhackbox:latest
```

```
PR opened  ───>  CI (lint + test + audit)
                      │
PR merged  ───>  CI  ───>  Build & Push  ───>  Docker Hub
                           (on CI success)
Tag v*     ──────────────>  Build & Push  ───>  Docker Hub
```

---

## Ethical Safeguards

1. **`--authorized` flag** is mandatory for all scanning commands — scans fail without it
2. **Warning banner** is displayed before every scan with a legal notice
3. **LLM safety prompts** prevent exploit generation and out-of-scope actions
4. **Rate limiting** via tenacity with exponential backoff on all HexStrike API calls
5. **Scope enforcement** in the AI orchestrator ensures tools stay within the authorized target
6. **Input validation** — SSRF/path-traversal prevention in the HexStrike client, Cypher injection prevention in the knowledge graph

---

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/my-feature`)
3. Make your changes and add tests
4. Run linting and tests:
   ```bash
   make lint
   make test-local
   ```
5. Commit and push your branch
6. Open a pull request

Code style is enforced by [Ruff](https://docs.astral.sh/ruff/) (line length: 100, target: Python 3.11). Type checking is done with [mypy](https://mypy-lang.org/).

---

## License

MIT License. See [LICENSE](LICENSE) for details.
