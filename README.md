# BLHACKBOX v1.0.0

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

- Python >= 3.11 (3.13 used in Docker image)
- Docker and Docker Compose
- Git

> For detailed Docker setup, image tags, volumes, and troubleshooting, see [DOCKER.md](DOCKER.md).

### 1. Clone and initialise

```bash
git clone https://github.com/crhacky/blhackbox.git
cd blhackbox
git submodule update --init --recursive
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env — at minimum, set NEO4J_PASSWORD and one LLM API key
```

### 3. Build and run

```bash
make build
make up

# Optional: start with local Ollama LLM (no API key required)
docker compose --profile ollama up -d
```

### 4. Run your first recon

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
│   ├── ci.yml                   # Lint, test, and pip-audit
│   └── build-and-push.yml       # Docker image build and push
├── docker-compose.yml           # HexStrike + Neo4j + Blhackbox (+ optional Ollama)
├── Dockerfile                   # Multi-stage Blhackbox container (Python 3.13)
├── Makefile                     # Common tasks
├── DOCKER.md                    # Docker quick-reference guide
├── hexstrike/                   # Git submodule -> HexStrike AI
├── blhackbox/
│   ├── __init__.py              # Package version
│   ├── main.py                  # CLI entry point (Click)
│   ├── config.py                # Pydantic settings
│   ├── exceptions.py            # Custom exception hierarchy
│   ├── clients/
│   │   └── hexstrike_client.py  # Async HexStrike HTTP client
│   ├── models/
│   │   ├── base.py              # Target, Finding, ScanSession, Severity
│   │   ├── hexstrike.py         # HexStrike response models
│   │   └── graph.py             # Neo4j node/relationship models
│   ├── core/
│   │   ├── runner.py            # Simple scan runner
│   │   ├── knowledge_graph.py   # Neo4j async client
│   │   ├── graph_exporter.py    # HexStrike -> Neo4j translator
│   │   ├── orchestrator.py      # LangGraph state machine
│   │   ├── planner.py           # LLM-based action planner
│   │   └── exploit_generator.py # Exploit generation module
│   ├── llm/
│   │   ├── client.py            # Multi-provider LLM client
│   │   ├── prompts.py           # System/user prompts
│   │   └── exploit_prompts.py   # Exploit-related prompts
│   ├── modules/
│   │   ├── base.py              # HexStrikeModule base class
│   │   └── argus_bridge/        # Argus-inspired modules
│   │       ├── port_scan.py         # Port scanning
│   │       ├── subdomain_enum.py    # Subdomain enumeration
│   │       └── tech_detect.py       # Technology detection
│   ├── reporting/
│   │   ├── html_generator.py    # Interactive HTML reports
│   │   └── pdf_generator.py     # PDF via WeasyPrint
│   ├── utils/
│   │   ├── logger.py            # Rich logging
│   │   └── catalog.py           # Tools catalog utilities
│   └── data/
│       └── tools_catalog.json   # HexStrike tools catalog (67 entries)
├── scripts/
│   └── reset_graph.py           # Reset Neo4j database
├── tests/                       # pytest suite (53+ tests)
│   ├── conftest.py              # Shared fixtures
│   ├── test_hexstrike_client.py # HTTP client tests
│   ├── test_exploit.py          # Exploit generation tests
│   ├── test_graph_exporter.py   # Graph exporter tests
│   ├── test_reporting.py        # Reporting tests
│   ├── test_cli.py              # CLI command tests
│   ├── test_catalog.py          # Tools catalog tests
│   ├── test_runner.py           # Runner tests
│   ├── test_config.py           # Config loading tests
│   ├── test_modules.py          # Custom module tests
│   ├── test_planner.py          # LLM planner tests
│   └── test_models.py           # Data model tests
├── results/                     # Scan output (gitignored)
└── wordlists/                   # Fuzzing wordlists (gitignored)
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
| `HEXSTRIKE_URL` | `http://hexstrike:8888` | HexStrike API base URL |
| `HEXSTRIKE_TIMEOUT` | `120` | HTTP timeout (seconds) |
| `HEXSTRIKE_MAX_RETRIES` | `3` | Max retries with exponential backoff |
| `NEO4J_URI` | `bolt://neo4j:7687` | Neo4j connection URI |
| `NEO4J_USER` | `neo4j` | Neo4j username |
| `NEO4J_PASSWORD` | *(required)* | Neo4j password (min 8 characters) |
| `OPENAI_API_KEY` | *(optional)* | OpenAI API key for AI orchestrator |
| `OPENAI_MODEL` | `gpt-4o` | OpenAI model name |
| `ANTHROPIC_API_KEY` | *(optional)* | Anthropic API key for AI orchestrator |
| `ANTHROPIC_MODEL` | `claude-sonnet-4-20250514` | Anthropic model name |
| `OLLAMA_URL` | `http://ollama:11434` | Ollama API URL (local LLM) |
| `OLLAMA_MODEL` | `llama3` | Ollama model name |
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

1. Builds multi-stage Docker image
2. Pushes to [Docker Hub](https://hub.docker.com/r/crhacky/blhackbox) with tags: `latest`, `x.y.z`, `x.y`, `main`, `<commit-sha>`

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
