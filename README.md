# BLHACKBOX v1.0.0

**HexStrike Hybrid Autonomous Pentesting Framework**

Blhackbox is an intelligent orchestration and correlation layer that sits on top of [HexStrike AI MCP Server](https://github.com/0x4m4/hexstrike-ai). It adds autonomous planning, a persistent knowledge graph, and professional reporting to HexStrike's 150+ security tools and 12+ AI agents.

---

## Legal Disclaimer

**This tool is intended for authorized security testing only.** You must have explicit written permission from the target owner before running any scans. Unauthorized access to computer systems is illegal and punishable by law. The developers assume no liability for misuse of this software.

---

## Architecture

```
┌─────────────────┐     ┌─────────────────────────────────────┐
│   AI Client     │     │         Blhackbox Layer              │
│ (Claude/Cursor) │────▶│  ┌─────────────────────────────┐    │
└─────────────────┘     │  │   LangGraph Orchestrator     │    │
                        │  └──────────────┬──────────────┘    │
                        │                 ▼                    │
                        │  ┌─────────────────────────────┐    │
                        │  │    Knowledge Graph (Neo4j)   │    │
                        │  └──────────────┬──────────────┘    │
                        │                 ▼                    │
                        │  ┌─────────────────────────────┐    │
                        │  │   HexStrike API Client       │    │
                        │  └──────────────┬──────────────┘    │
                        └─────────────────┼───────────────────┘
                                          ▼
                        ┌─────────────────────────────────────┐
                        │     HexStrike MCP Server            │
                        │  (150+ tools, 12+ AI agents)        │
                        └─────────────────────────────────────┘
```

## What Blhackbox Adds

| Capability | Description |
|---|---|
| **Knowledge Graph** | Neo4j-powered persistent attack surface model |
| **AI Orchestrator** | LangGraph-based autonomous tool/agent selection |
| **Professional Reporting** | PDF and HTML reports with severity charts |
| **Custom Module Bridge** | Extend HexStrike without modifying it |

HexStrike provides the tools. Blhackbox provides the brain.

---

## Quick Start

### Prerequisites

- Python >= 3.11 (3.13 used in Docker image)
- Docker and Docker Compose
- Git

> For detailed Docker setup, troubleshooting, and architecture details, see [DOCKER.md](DOCKER.md).

### 1. Clone and initialise

```bash
git clone https://github.com/crhacky/blhackbox.git
cd blhackbox
git submodule update --init --recursive
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env with your API keys and passwords
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
```

---

## CLI Reference

### Reconnaissance

```bash
# Basic recon via HexStrike intelligence
blhackbox recon --target <domain> --authorized

# AI-driven autonomous recon (Phase 3)
blhackbox recon --target <domain> --authorized --ai
```

### Run individual tools

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

### Other

```bash
blhackbox version
blhackbox --debug <command>   # Enable debug logging
```

### Makefile Shortcuts

```bash
make help         # Show all available targets
make build        # Build Docker containers
make up           # Start services (detached)
make down         # Stop services
make shell        # Open a shell in the blhackbox container
make test         # Run tests in Docker
make test-local   # Run tests locally
make lint         # Ruff linting
make format       # Auto-format code
make reset-graph  # Reset the Neo4j knowledge graph
make wordlists    # Download common SecLists wordlists
```

---

## Project Structure

```
blhackbox/
├── .github/workflows/
│   ├── ci.yml                # Lint, test, and pip-audit
│   └── build-and-push.yml    # Docker image build
├── docker-compose.yml        # HexStrike + Neo4j + Blhackbox (+ optional Ollama)
├── Dockerfile                # Multi-stage Blhackbox container (Python 3.13)
├── Makefile                  # Common tasks
├── DOCKER.md                 # Docker quick-reference guide
├── hexstrike/                # Git submodule -> HexStrike AI
├── blhackbox/
│   ├── main.py               # CLI entry point (Click)
│   ├── config.py             # Pydantic settings
│   ├── exceptions.py         # Custom exception hierarchy
│   ├── clients/
│   │   └── hexstrike_client.py  # Async HexStrike HTTP client
│   ├── models/
│   │   ├── base.py           # Target, Finding, ScanSession
│   │   ├── hexstrike.py      # HexStrike response models
│   │   └── graph.py          # Neo4j node/relationship models
│   ├── core/
│   │   ├── runner.py         # Simple scan runner
│   │   ├── knowledge_graph.py  # Neo4j async client
│   │   ├── graph_exporter.py # HexStrike -> Neo4j translator
│   │   ├── orchestrator.py   # LangGraph state machine
│   │   └── planner.py        # LLM-based action planner
│   ├── llm/
│   │   ├── client.py         # Multi-provider LLM client
│   │   └── prompts.py        # System/user prompts
│   ├── modules/
│   │   ├── base.py           # HexStrikeModule base class
│   │   └── argus_bridge/     # Argus-inspired modules
│   │       ├── port_scan.py      # Port scanning
│   │       ├── subdomain_enum.py # Subdomain enumeration
│   │       └── tech_detect.py    # Technology detection
│   ├── reporting/
│   │   ├── html_generator.py # Interactive HTML reports
│   │   └── pdf_generator.py  # PDF via WeasyPrint
│   └── utils/
│       └── logger.py         # Rich logging
├── scripts/
│   └── reset_graph.py        # Reset Neo4j database
├── tests/                    # pytest suite (53+ tests)
├── results/                  # Scan output (gitignored)
└── wordlists/                # Fuzzing wordlists (gitignored)
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

---

## Configuration

All settings are loaded from environment variables or `.env`. See [`.env.example`](.env.example) for the full template.

| Variable | Default | Description |
|---|---|---|
| `HEXSTRIKE_URL` | `http://hexstrike:8888` | HexStrike API base URL |
| `HEXSTRIKE_TIMEOUT` | `120` | HTTP timeout (seconds) |
| `HEXSTRIKE_MAX_RETRIES` | `3` | Max retries for failed requests |
| `NEO4J_URI` | `bolt://neo4j:7687` | Neo4j connection URI |
| `NEO4J_USER` | `neo4j` | Neo4j username |
| `NEO4J_PASSWORD` | (required) | Neo4j password |
| `OPENAI_API_KEY` | (optional) | OpenAI API key for AI orchestrator |
| `OPENAI_MODEL` | `gpt-4o` | OpenAI model name |
| `ANTHROPIC_API_KEY` | (optional) | Anthropic API key for AI orchestrator |
| `ANTHROPIC_MODEL` | `claude-sonnet-4-20250514` | Anthropic model name |
| `OLLAMA_URL` | `http://ollama:11434` | Ollama API URL (local LLM) |
| `OLLAMA_MODEL` | `llama3` | Ollama model name |
| `LLM_PROVIDER_PRIORITY` | `openai,anthropic,ollama` | Comma-separated fallback order |
| `MAX_ITERATIONS` | `10` | Max orchestrator iterations per session |
| `LOG_LEVEL` | `INFO` | Logging level |

---

## Ethical Safeguards

1. **`--authorized` flag** is mandatory for all scanning commands
2. **Warning banner** is displayed before every scan
3. **LLM safety prompts** prevent exploit generation and out-of-scope actions
4. **Rate limiting** via tenacity on all HexStrike API calls
5. **Scope enforcement** in the AI orchestrator

---

## License

MIT License. See [LICENSE](LICENSE) for details.
