# PentAGI vs BLHACKBOX — Architecture Comparison & Optimization Roadmap

> Analysis date: 2026-03-25
> PentAGI repo: https://github.com/vxcontrol/pentagi
> Note: PentAGI source code was under licensing audit at time of analysis; details sourced from README, DeepWiki, forks, and cached Go source files.

---

## 1. Multi-Agent Architecture Comparison

PentAGI implements a "simulated security firm" with 13 specialized AI agents, each with its own system prompt, tool set, and optionally a different LLM model. BLHACKBOX uses Claude Code as a single orchestrating LLM that calls MCP tools directly.

### Agent Mapping

| PentAGI Agent | Role | Tool-Call Limit | BLHACKBOX Equivalent |
|---|---|---|---|
| **Primary Agent** | Orchestrator — decomposes tasks, delegates to specialists | 100 (general) | Claude Code itself |
| **Pentester** | Runs security tools (nmap, metasploit, sqlmap) | 100 (general) | Kali MCP (70+ tools) |
| **Coder** | Writes custom exploit code in real-time | 100 (general) | **None** |
| **Installer** | Installs packages into Docker sandbox on demand | 100 (general) | **None** (pre-baked images) |
| **Assistant** | General-purpose helper | 100 (general) | Claude Code general capabilities |
| **Searcher** | Queries Tavily, DuckDuckGo, Sploitus, Google, Perplexity, Searxng | 20 (limited) | Claude's WebSearch |
| **Enricher** | Consults vector store for past findings | 20 (limited) | Neo4j (optional, manual Cypher) |
| **Adviser** | Strategic planning (often uses stronger model like Opus) | 20 (limited) | Skill templates (static) |
| **Reflector** | Detects loops, guides graceful completion near limits | 20 (limited) | **None** |
| **Generator** | Generates reports, payloads, complex content | 20 (limited) | Report generators (md/pdf/html) |
| **Refiner** | Iterates on outputs for quality | 20 (limited) | **None** |
| **Reporter** | Structured finding synthesis | 20 (limited) | `aggregate_results` MCP tool |
| **Planner** | Task decomposition and sequencing | 20 (limited) | Skill templates (static plans) |

### Key Architectural Differences

| Aspect | PentAGI | BLHACKBOX |
|---|---|---|
| **Orchestration** | Go backend with multi-agent delegation | Claude Code LLM is the orchestrator |
| **LLM calls** | Multiple LLM calls per agent, per task | Single LLM conversation |
| **Model routing** | Per-agent model selection (Opus for planning, Sonnet for code) | Single model per session |
| **Tool routing** | Backend routes tools to appropriate agent | Claude decides which MCP tool to call |
| **State management** | PostgreSQL + pgvector + Neo4j + Redis | JSON session files + optional Neo4j |
| **Protocol** | Custom REST/GraphQL API | MCP standard |

---

## 2. PentAGI Features to Adopt

### P0 — Critical (Highest ROI)

#### 2.1 Exploit Development Skill (Coder Agent equivalent)

PentAGI's Coder agent writes custom exploit code in real-time. This is the single biggest capability gap.

**Proposal**: Create a `/exploit-dev` skill that:
- Instructs Claude to enter "developer mode" for exploit writing
- Generates custom PoC scripts based on discovered vulnerabilities
- Adapts public exploits to the specific target environment
- Writes targeted payloads (reverse shells, SQLi chains, XSS payloads)
- Tests exploits inside the Kali container and iterates

The Kali MCP already has `msfvenom` for payload generation, but no workflow for *custom* exploit development.

#### 2.2 Vector Memory System (Enricher Agent equivalent)

PentAGI uses PostgreSQL + pgvector for semantic memory:
- Stores successful exploitation chains as vector embeddings
- Recalls similar past findings when approaching new targets
- Learns from failed attempts across sessions

BLHACKBOX stores sessions as JSON files — not searchable by similarity.

**Proposal**: Add a pgvector-backed memory service:
1. New MCP tool: `recall_similar_findings(description: str, limit: int) -> list[Finding]`
2. New MCP tool: `store_engagement_memory(session_id: str, embeddings: list)`
3. Auto-embed tool outputs and findings after each `aggregate_results` call
4. On new engagements, skill templates query similar past findings to inform strategy

Could be added as a new Docker service (`memory-mcp`) or integrated into the existing blhackbox MCP server.

### P1 — High Priority

#### 2.3 Loop Detection & Agent Supervision (Reflector Agent equivalent)

PentAGI's Reflector agent detects stuck agents and guides graceful completion.

**Proposal**: Implement as a session-start hook:
1. Track tool calls per session (tool name + args hash)
2. Detect patterns: same tool called >3 times with identical args
3. Inject system message: "You appear to be repeating. Reassess your approach or try an alternative tool."
4. Warn when approaching context limits: "You've used N tool calls. Begin wrapping up findings."

#### 2.4 Automatic Knowledge Graph Population

PentAGI uses Graphiti to automatically extract entities and relationships from agent interactions.

BLHACKBOX's `aggregate_results` already produces structured `AggregatedPayload` with hosts, services, vulnerabilities, and endpoints. This data should auto-populate Neo4j.

**Proposal**: After `aggregate_results` validation succeeds, automatically:
1. Create `(:Host)` nodes from `findings.hosts`
2. Create `(:Service)` nodes from `findings.services`
3. Create `(:Vulnerability)` nodes from `findings.vulnerabilities`
4. Create `(:Endpoint)` nodes from `findings.endpoints`
5. Create relationships: `(:Host)-[:RUNS]->(:Service)`, `(:Service)-[:HAS_VULN]->(:Vulnerability)`, etc.

This is low-effort since the structured data already exists in the payload.

### P2 — Medium Priority

#### 2.5 Multi-Model Routing in Skills

PentAGI assigns different models per agent role for cost/quality optimization.

**Proposal**: Skills could specify model preferences:
```yaml
# In SKILL.md frontmatter
phases:
  planning: opus      # Deep strategic reasoning
  recon: haiku        # Fast, cheap parsing
  exploitation: opus  # Complex exploit development
  reporting: sonnet   # Balanced quality
```

This is partially achievable today via the `Agent` tool's `model` parameter but isn't systematized.

#### 2.6 Exploit Database Search Tool

PentAGI integrates Sploitus search for exploit discovery. BLHACKBOX relies on generic web search.

**Proposal**: Add a Kali MCP tool `search_exploits(query: str, type: str)` that queries:
- `searchsploit` (local ExploitDB)
- Sploitus API (remote exploit aggregator)
- Metasploit module search (`msfconsole -qx "search ..."`)

### P3 — Lower Priority

#### 2.7 Dynamic Package Installation

PentAGI's Installer agent can `apt-get install` new tools at runtime.

**Proposal**: Add `install_package(name: str)` to Kali MCP. Low effort, edge case utility.

#### 2.8 Strategic Pre-Planning Agent (Adviser equivalent)

PentAGI's Adviser uses a stronger model for strategic analysis before execution.

**Proposal**: A `/plan-engagement` skill that uses Opus to:
1. Analyze the target scope
2. Research the target's technology stack
3. Propose a prioritized attack plan
4. Estimate which tools and phases are most likely to yield results

---

## 3. Where BLHACKBOX is Already Superior

| Area | BLHACKBOX | PentAGI |
|---|---|---|
| **Tool breadth** | 70+ Kali tools via MCP | ~20 tools |
| **Network analysis** | Dedicated WireMCP (tshark, pcap, credential extraction) | No packet analysis |
| **Evidence capture** | Screenshot MCP (Playwright, annotations, element capture) | Basic scraper only |
| **Client flexibility** | Claude Code + Claude Desktop + ChatGPT via MCP Gateway | Web UI only |
| **Infrastructure simplicity** | 3 containers core stack | 10+ containers |
| **Workflow templates** | 10 production-ready slash command skills | No equivalent |
| **PoC rigor** | Mandatory `evidence`, `poc_steps`, `poc_payload` fields | No enforced PoC structure |
| **Protocol standard** | MCP-native (works with any MCP client) | Custom API |
| **Authorization framework** | verification.env with legal workflow | No equivalent |
| **Metasploit integration** | Full msfconsole + msfvenom via CLI | Basic Metasploit |
| **Report formats** | MD + PDF + HTML with AggregatedPayload contract | Less structured |

---

## 4. Summary

PentAGI's multi-agent architecture provides deeper autonomous reasoning through specialization and cross-session learning. BLHACKBOX's MCP-native architecture provides broader tool access, simpler deployment, and better evidence rigor.

The three highest-ROI improvements to close the gap:
1. **Exploit development skill** — matches PentAGI's Coder agent
2. **Vector memory system** — matches PentAGI's pgvector-based learning
3. **Loop detection guardrails** — matches PentAGI's Reflector agent

These additions would capture PentAGI's key differentiators while preserving BLHACKBOX's architectural advantages.
