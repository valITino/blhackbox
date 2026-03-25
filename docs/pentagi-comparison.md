# PentAGI vs BLHACKBOX — Architecture Comparison & Optimization Roadmap

> Analysis date: 2026-03-25
> PentAGI repo: https://github.com/vxcontrol/pentagi
> Note: PentAGI source code was under licensing audit at time of analysis; details sourced from README, DeepWiki, forks (AlExAnDeR-O-G/pentagi), and cached Go source files at commit e97bbe5.

---

## 1. Multi-Agent Architecture Comparison

PentAGI implements a "simulated security firm" with 13 specialized AI agents, each with its own system prompt (`.tmpl` file), tool set, and optionally a different LLM model. BLHACKBOX uses Claude Code as a single orchestrating LLM that calls MCP tools directly.

### Agent Mapping

| PentAGI Agent | Role | Tool-Call Limit | Tools Available | BLHACKBOX Equivalent |
|---|---|---|---|---|
| **Primary Agent** | Orchestrator — decomposes tasks, delegates to specialists | 100 (general) | `adviser`, `coder`, `installer`, `pentester`, `searcher`, `memorist`, `ask_user` | Claude Code itself |
| **Pentester** | Runs security tools in Docker sandbox | 100 (general) | `terminal`, `file`, `hack_result`, guide tools | Kali MCP (70+ tools) |
| **Coder** | Writes custom exploit code in real-time | 100 (general) | `terminal`, `file`, `code_result`, `search_code`, `store_code`, guide tools | **None** |
| **Installer** | Installs packages/infra into Docker sandbox | 100 (general) | `terminal`, `file`, `browser`, `maintenance_result`, guide tools | **None** (pre-baked images) |
| **Assistant** | General-purpose helper | 100 (general) | Full tool set | Claude Code general capabilities |
| **Searcher** | Web research via 6 search engines | 20 (limited) | `google`, `duckduckgo`, `tavily`, `perplexity`, `traversaal`, `browser`, `search_answer`, `memorist` | Claude's WebSearch |
| **Memorist** | Long-term memory retrieval via vector store | 20 (limited) | `search_in_memory`, `terminal`, `file` | Neo4j (optional, manual Cypher) |
| **Enricher** | Enriches questions with context before Adviser | 20 (limited) | Vector store queries | **None** |
| **Adviser** | Strategic planning (often uses stronger model) | 20 (limited) | Receives enriched context, returns recommendations | Skill templates (static) |
| **Reflector** | Detects text-only responses, forces tool calls | 20 (limited) | Re-prompts agents to use barrier functions | **None** |
| **Generator** | Initial subtask decomposition (up to 15 subtasks) | 20 (limited) | `memorist`, `searcher`, `subtask_list` | Skill templates (static plans) |
| **Refiner** | Adjusts planned subtasks based on progress | 20 (limited) | Subtask modification | **None** |
| **Reporter** | Compiles final task reports | 20 (limited) | `report_result` only | `aggregate_results` MCP tool |
| **Summarizer** | Truncates/summarizes large tool outputs | 20 (limited) | Text processing | **None** |

### PentAGI Orchestration Flow (from Go source)

```
User submits task
  │
  ▼
Generator agent (generator.tmpl)
  │ Decomposes task into ≤15 subtasks
  │ Queries memorist for similar past tasks
  ▼
For each subtask:
  │
  ├─ Primary Agent (primary_agent.tmpl) — runs in a loop
  │   │ Has tools: adviser, coder, installer, pentester, searcher, memorist
  │   │
  │   ├─ Calls "pentester" → performPentester()
  │   │   ├─ Renders pentester.tmpl
  │   │   ├─ Gets tools: terminal, file, hack_result
  │   │   ├─ Executes commands in Docker (debian or kali-linux)
  │   │   └─ MUST call hack_result (barrier function) to return
  │   │
  │   ├─ Calls "coder" → performCoder()
  │   │   ├─ Renders coder.tmpl
  │   │   ├─ Gets tools: terminal, file, code_result, search_code
  │   │   ├─ Writes/tests exploit code in container
  │   │   └─ MUST call code_result (barrier function) to return
  │   │
  │   ├─ Calls "searcher" → performSearcher()
  │   │   ├─ Renders searcher.tmpl
  │   │   ├─ Gets tools: google, duckduckgo, tavily, perplexity, browser
  │   │   └─ MUST call search_result (barrier function) to return
  │   │
  │   ├─ Calls "adviser" → Enricher → Adviser chain
  │   │   ├─ Enricher fetches context from vector store
  │   │   ├─ Adviser (stronger model) provides strategic recommendation
  │   │   └─ Returns advice to Primary Agent
  │   │
  │   └─ If agent returns text instead of tool call:
  │       └─ Reflector (reflector.tmpl) re-prompts to use barrier function
  │
  ├─ Refiner agent adjusts remaining subtasks based on results
  │
  └─ Loop continues until Primary Agent calls "finaly" barrier

Reporter agent (reporter.tmpl)
  └─ Compiles all subtask results into final report
```

### Barrier Function Pattern (Critical Design)

Each sub-agent has a mandatory "barrier function" — a special tool it MUST call to terminate its loop and return results to the Primary Agent:

| Agent | Barrier Function | Purpose |
|---|---|---|
| Pentester | `hack_result` | Report pentest findings |
| Coder | `code_result` | Return written code |
| Searcher | `search_result` | Return research |
| Installer | `maintenance_result` | Report infra changes |
| Memorist | `memorist_result` | Return recalled data |
| Reporter | `report_result` | Return compiled report |
| Generator | `subtask_list` | Return subtask plan |

Without calling its barrier function, an agent's loop continues (up to `maxRetries=3`). The Reflector catches agents that produce text-only responses and forces them back to tool use.

### Key Architectural Differences

| Aspect | PentAGI | BLHACKBOX |
|---|---|---|
| **Orchestration** | Go backend with multi-agent delegation loops | Claude Code LLM is the orchestrator |
| **LLM calls** | Multiple LLM calls per agent, per subtask (N agents × M retries) | Single LLM conversation thread |
| **Model routing** | Per-agent model selection via `ProviderOptionsType` | Single model per session (or manual `/fast` toggle) |
| **Tool routing** | Backend assigns restricted tool sets per agent type | Claude decides which MCP tool to call |
| **Tool isolation** | Each agent sees ONLY its allowed tools (enforced in Go) | All MCP tools visible to Claude simultaneously |
| **State management** | PostgreSQL + pgvector + Neo4j + Redis | JSON session files + optional Neo4j |
| **Execution sandbox** | Ephemeral Docker containers per flow (debian or kali-linux) | Persistent Docker containers (Kali MCP, Wire MCP) |
| **Protocol** | Custom REST/GraphQL API | MCP standard |
| **LLM framework** | Custom Go agent loop on vxcontrol/langchaingo fork | Native Claude Code / MCP protocol |
| **Retry logic** | `maxRetries=3` per agent chain, 5s delay between retries | No systematic retry mechanism |

---

## 2. PentAGI Features to Adopt

### P0 — Critical (Highest ROI)

#### 2.1 Exploit Development Skill (Coder Agent equivalent)

PentAGI's Coder agent (`coder.tmpl`) has `terminal`, `file`, `code_result`, `search_code`, and `store_code` tools. It writes exploit code in a Docker container, tests it, iterates, and must call `code_result` to return. Critically, successful code is stored via `store_code` for reuse in future engagements (vector-indexed).

This is the single biggest capability gap in BLHACKBOX.

**Proposal**: Create a `/exploit-dev` skill that:
- Instructs Claude to enter "developer mode" for exploit writing
- Generates custom PoC scripts based on discovered vulnerabilities
- Adapts public exploits to the specific target environment
- Writes targeted payloads (reverse shells, SQLi chains, XSS payloads)
- Tests exploits inside the Kali container via `run_kali_tool("python3", ...)` and iterates
- Captures successful exploit code in the AggregatedPayload `poc_payload` field

The Kali MCP already has `msfvenom` for payload generation and `python3` for script execution, but no structured workflow for *custom* exploit development with test-iterate-store loops.

#### 2.2 Vector Memory System (Memorist + Enricher Agent equivalent)

PentAGI's memory system has two layers from the Go source:
- **Memorist agent** (`memory.go`): Similarity search with threshold 0.45, documents tagged with flow ID, task ID, subtask ID, and type metadata
- **Searcher store** (`search.go`): Higher threshold 0.75 for storing/retrieving search answers — avoids storing low-quality results
- Documents embedded via pgvector in PostgreSQL; each agent can call `search_in_memory` and `store_*` tools

BLHACKBOX stores sessions as flat JSON files — not searchable by similarity.

**Proposal**: Add a pgvector-backed memory service:
1. New MCP tool: `recall_similar_findings(description: str, threshold: float = 0.45, limit: int = 10) -> list[Finding]`
2. New MCP tool: `store_engagement_memory(session_id: str, finding_type: str, content: str)` — auto-embeds via API
3. Auto-embed tool outputs and findings after each `aggregate_results` call (tag with session_id, target, tool_source)
4. On new engagements, skill templates query similar past findings to inform strategy
5. Use dual thresholds like PentAGI: 0.45 for broad recall, 0.75 for high-confidence matches

Could be added as a new Docker service (`memory-mcp`) using PostgreSQL + pgvector, or integrated into the existing blhackbox MCP server.

### P1 — High Priority

#### 2.3 Loop Detection & Agent Supervision (Reflector Agent equivalent)

PentAGI's Reflector (`reflector.tmpl`) catches two specific failure modes from the Go source:
1. **Text-only responses**: Agent produces analysis text instead of calling a tool → Reflector re-prompts to use the barrier function
2. **Tool-call limit approach**: When an agent nears its limit (100 for general, 20 for limited agents), Reflector guides graceful completion

PentAGI also has retry logic: `maxRetriesToCallAgentChain = 3` with `delayBetweenRetries = 5s`.

**Proposal**: Implement as a Claude Code hook (session-start or pre-tool):
1. Track tool calls per session (tool name + args hash)
2. Detect patterns: same tool called >3 times with identical args
3. Inject system message: "You appear to be repeating. Reassess your approach or try an alternative tool."
4. Warn when approaching context limits: "You've used N tool calls. Begin wrapping up findings."
5. Track total token usage and inject aggregation reminder at 70% context window

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

## 4. PentAGI Source Code Reference (Key Files)

For implementation reference, these are the critical Go source files in PentAGI's backend:

| File | What It Contains |
|---|---|
| `backend/pkg/providers/provider.go` | `FlowProvider` interface: `GenerateSubtasks`, `RefineSubtasks`, `PerformAgentChain`, `GetTaskResult` |
| `backend/pkg/providers/performers.go` | Agent loop: `performAgentChain()`, `performCoder()`, `performPentester()`, `performSearcher()`, `performInstaller()`, `performMemorist()` |
| `backend/pkg/providers/handlers.go` | Handler factories per agent: `adviserHandler`, `coderHandler`, `pentesterHandler`, `searcherHandler`, `summarizeResultHandler` |
| `backend/pkg/tools/tools.go` | `FlowToolsExecutor` and `ContextToolsExecutor` interfaces; per-agent tool set factory methods |
| `backend/pkg/tools/registry.go` | 31 tool definitions with type classification (Environment, SearchNetwork, SearchVectorDb, Agent, Barrier) |
| `backend/pkg/tools/terminal.go` | Docker container command execution (default 5min timeout, hard limit 20min) |
| `backend/pkg/tools/memory.go` | Vector store similarity search (threshold 0.45) |
| `backend/pkg/tools/search.go` | Search answer retrieval/storage (threshold 0.75) |
| `backend/pkg/templates/templates.go` | 21 `PromptType` constants, `Prompter` interface, embedded `.tmpl` files |
| `backend/pkg/templates/prompts/*.tmpl` | 21 prompt templates (one per agent type + utilities) |

---

## 5. Summary

PentAGI's multi-agent architecture provides deeper autonomous reasoning through specialization and cross-session learning. BLHACKBOX's MCP-native architecture provides broader tool access, simpler deployment, and better evidence rigor.

The three highest-ROI improvements to close the gap:
1. **Exploit development skill** — matches PentAGI's Coder agent
2. **Vector memory system** — matches PentAGI's pgvector-based learning
3. **Loop detection guardrails** — matches PentAGI's Reflector agent

These additions would capture PentAGI's key differentiators while preserving BLHACKBOX's architectural advantages.
