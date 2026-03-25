# Vector Memory System — Design Document

> Status: Design (ready for implementation)
> Priority: P0
> Inspired by: PentAGI's Memorist agent + pgvector memory system

## Problem

BLHACKBOX stores engagement results as flat JSON files in `output/sessions/`.
There is no way to query past engagements by similarity — e.g., "what worked
last time I tested Apache 2.4.49?" or "show me all SQLi findings across all
engagements."

PentAGI solves this with PostgreSQL + pgvector, enabling semantic search
across past findings, exploit code, and successful attack patterns.

## Architecture

```
                                 ┌──────────────────┐
                                 │  Claude Code      │
                                 │  (MCP Client)     │
                                 └────────┬─────────┘
                                          │
                              MCP tool calls (SSE)
                                          │
                    ┌─────────────────────┼─────────────────────┐
                    │                     │                     │
                    ▼                     ▼                     ▼
             ┌──────────┐         ┌──────────┐         ┌──────────────┐
             │ Kali MCP │         │ Wire MCP │         │ Memory MCP   │ ← NEW
             │ :9001    │         │ :9003    │         │ :9005        │
             └──────────┘         └──────────┘         └──────┬───────┘
                                                              │
                                                    ┌─────────▼─────────┐
                                                    │  PostgreSQL       │
                                                    │  + pgvector       │
                                                    │  :5432            │
                                                    └───────────────────┘
```

## New Docker Service: `memory-mcp`

```yaml
# docker-compose.yml addition
memory-db:
  image: pgvector/pgvector:pg16
  container_name: blhackbox-memory-db
  profiles: ["memory"]
  restart: unless-stopped
  environment:
    POSTGRES_DB: blhackbox_memory
    POSTGRES_USER: blhackbox
    POSTGRES_PASSWORD: "${MEMORY_DB_PASSWORD:-blhackbox}"
  volumes:
    - memory_db_data:/var/lib/postgresql/data
  healthcheck:
    test: ["CMD-SHELL", "pg_isready -U blhackbox"]
    interval: 10s
    timeout: 5s
    retries: 5
  networks:
    - blhackbox_net

memory-mcp:
  image: crhacky/blhackbox:memory-mcp
  build:
    context: .
    dockerfile: docker/memory-mcp.Dockerfile
  container_name: blhackbox-memory-mcp
  profiles: ["memory"]
  restart: unless-stopped
  environment:
    DATABASE_URL: "postgresql://blhackbox:${MEMORY_DB_PASSWORD:-blhackbox}@memory-db:5432/blhackbox_memory"
    EMBEDDING_MODEL: "${MEMORY_EMBEDDING_MODEL:-text-embedding-3-small}"
    OPENAI_API_KEY: "${OPENAI_API_KEY:-}"
    ANTHROPIC_API_KEY: "${ANTHROPIC_API_KEY:-}"
    MCP_PORT: "9005"
  ports:
    - "${MEMORY_MCP_PORT:-9005}:9005"
  depends_on:
    memory-db:
      condition: service_healthy
  healthcheck:
    test: ["CMD-SHELL", "python3 -c \"import urllib.request; urllib.request.urlopen('http://localhost:9005/sse')\""]
    interval: 15s
    timeout: 10s
    retries: 5
    start_period: 10s
  networks:
    - blhackbox_net
```

## Database Schema

```sql
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE memories (
    id              SERIAL PRIMARY KEY,
    session_id      TEXT NOT NULL,
    target          TEXT NOT NULL,
    memory_type     TEXT NOT NULL,  -- 'finding', 'exploit', 'guide', 'search', 'general'
    title           TEXT NOT NULL,
    content         TEXT NOT NULL,
    severity        TEXT DEFAULT 'info',
    tool_source     TEXT DEFAULT '',
    tags            TEXT[] DEFAULT '{}',
    embedding       vector(1536),   -- text-embedding-3-small dimension
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Similarity search index (IVFFlat for speed, HNSW for accuracy)
CREATE INDEX ON memories USING hnsw (embedding vector_cosine_ops);

-- Filtered search indexes
CREATE INDEX ON memories (memory_type);
CREATE INDEX ON memories (target);
CREATE INDEX ON memories (severity);
CREATE INDEX ON memories USING GIN (tags);
```

## MCP Tools (6 tools)

### 1. `recall_similar` — Core semantic search

```python
@mcp.tool()
async def recall_similar(
    query: str,
    memory_type: str = "",
    threshold: float = 0.45,
    limit: int = 10,
) -> str:
    """Search past engagement memories by semantic similarity.

    Use this at the START of every engagement to recall relevant past
    findings, successful exploits, and attack patterns.

    Threshold guide (from PentAGI):
      0.45 — General recall (broad, may include tangential results)
      0.70 — Code/exploit recall (focused, high-relevance)
      0.75 — Search answer recall (verified findings only)
      0.80 — Pentest guide recall (proven methodologies only)

    Args:
        query: Natural language description of what to recall.
        memory_type: Filter by type: finding, exploit, guide, search, general, or '' for all.
        threshold: Minimum cosine similarity (0.0-1.0, default 0.45).
        limit: Maximum results to return (default 10).
    """
```

### 2. `store_finding` — Store a vulnerability finding

```python
@mcp.tool()
async def store_finding(
    session_id: str,
    target: str,
    title: str,
    content: str,
    severity: str = "info",
    tool_source: str = "",
    tags: list[str] = [],
) -> str:
    """Store a vulnerability finding for future recall.

    Call this after confirming a vulnerability to build long-term memory.
    Future engagements can recall similar findings.
    """
```

### 3. `store_exploit` — Store successful exploit code

```python
@mcp.tool()
async def store_exploit(
    session_id: str,
    target: str,
    title: str,
    code: str,
    language: str = "python",
    vulnerability: str = "",
    tags: list[str] = [],
) -> str:
    """Store successful exploit code for reuse in future engagements.

    Only store exploits that were CONFIRMED WORKING against a target.
    Include the target service/version in the title for accurate recall.
    """
```

### 4. `store_guide` — Store a pentest methodology/guide

```python
@mcp.tool()
async def store_guide(
    title: str,
    content: str,
    tags: list[str] = [],
) -> str:
    """Store a proven pentesting guide or methodology for future use.

    Call this when a specific approach worked well and should be
    remembered as a reusable pattern.
    """
```

### 5. `get_memory_stats` — Memory system statistics

```python
@mcp.tool()
async def get_memory_stats() -> str:
    """Get statistics about the memory system.

    Returns counts by memory type, most recent sessions, and
    top tags. Useful for understanding what knowledge is available.
    """
```

### 6. `auto_store_session` — Bulk import from AggregatedPayload

```python
@mcp.tool()
async def auto_store_session(
    session_file: str,
) -> str:
    """Import all findings from an AggregatedPayload session file.

    Reads a session JSON file (from aggregate_results), extracts all
    findings, and stores them as individual memories with embeddings.
    Call this after aggregate_results to populate the memory system.
    """
```

## Integration Points

### 1. Skill Templates

Add to all skill templates (after "Before you start:" section):

```markdown
> **Memory recall:** If the memory system is available, start by recalling
> similar past findings:
> ```
> recall_similar("pentesting [TARGET_TYPE] [SERVICE_VERSION]", threshold=0.45)
> ```
```

### 2. aggregate_results Hook

After `aggregate_results` succeeds, if memory-mcp is available:
- Auto-call `auto_store_session` with the session file
- Log: "Stored N findings in vector memory for future recall"

### 3. Exploit Development Skill

The `/exploit-dev` skill should:
- `recall_similar(query, memory_type="exploit", threshold=0.70)` before writing new code
- `store_exploit(...)` after confirming an exploit works

## Embedding Strategy

### Provider Options

1. **OpenAI text-embedding-3-small** (default) — 1536 dims, $0.02/1M tokens
2. **OpenAI text-embedding-3-large** — 3072 dims, higher quality
3. **Local via Ollama** — nomic-embed-text, mxbai-embed-large (free, private)
4. **Anthropic Voyager** — when available

### What Gets Embedded

The `content` field of each memory is embedded. For structured data, we
concatenate key fields:

```python
# Finding embedding text
f"Vulnerability: {title}\nSeverity: {severity}\nTarget: {target}\n"
f"Tool: {tool_source}\nDescription: {content[:2000]}"

# Exploit embedding text
f"Exploit: {title}\nLanguage: {language}\nVulnerability: {vulnerability}\n"
f"Code:\n{code[:3000]}"

# Guide embedding text
f"Guide: {title}\nMethodology:\n{content[:3000]}"
```

## Migration Path

1. **Phase 1** (this design): New `memory-mcp` service behind `--profile memory`
2. **Phase 2**: Auto-import existing session JSON files into pgvector
3. **Phase 3**: Add memory recall to all skill templates
4. **Phase 4**: Add memory store to aggregate_results pipeline
