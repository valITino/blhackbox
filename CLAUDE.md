# BLHACKBOX v2.0 — Claude Code Instructions

Behavioral guidelines + project-specific rules. Read the whole file before touching anything.

---

## ⚠️ Mandatory Protocol — Read Before Touching Anything

Before making **any** fix, refactor, addition, or change — no matter how small it looks — you must complete all three phases below in order. **No exceptions.**

> **Note on tradeoffs:** Generic coding guidance often says "for trivial tasks, use judgment and skip the ceremony." That shortcut **does not apply here.** This is a security-sensitive pentesting framework where a one-line change can break authorization checks, shell-injection guards, or a stable schema contract. Bias toward caution over speed, always.

### Phase 1: Web Research — Cast a Wide Net

Search the web for current, accurate information on **anything the task touches** that may have changed, broken, or gained known issues since your training cutoff. Err on the side of over-researching. The goal is to catch surprises *before* you write code, not after.

At minimum, research:

- **Every framework, library, package, runtime, or base image involved in the change** — current API, deprecations, breaking changes between versions, known CVEs, security advisories
- **Every external tool, CLI, flag, or service** whose behavior the change depends on — verify signatures, current output format, and auth/permission model
- **Every protocol, spec, or standard** the change interacts with — look for recent revisions
- **Domain context relevant to the task** — e.g., current security best practices, exploit techniques, detection signatures, compliance requirements — whatever applies to *this* specific change

Then broaden: is there a recent post-mortem, GitHub issue, or advisory describing a bug very similar to what you're about to fix or introduce? Check.

If your web research is inconclusive, contradicts your prior assumptions, or returns nothing relevant — **say so explicitly** before proceeding. Do not silently fill gaps with memory.

### Phase 2: Full Codebase Review — Understand the Blast Radius

Read the **actual current state** of the codebase. Do not rely on memory from previous sessions, and do not trust summaries — open the files.

Baseline reading (always, every session):

- `CLAUDE.md` (this file) and `README.md`
- Top-level configuration: build/orchestration files, dependency manifests, environment templates, any manifest that controls what the AI client sees (e.g., MCP server registrations)

Task-specific reading (scale to the change):

- **Every file you plan to modify — in full**, not just the region you're touching. Adjacent code often encodes invariants that aren't obvious from the target line alone.
- **Every file that imports or is imported by the files you're touching** — to see the blast radius
- **Related tests, schemas, fixtures, type definitions, and Pydantic models** — they describe the contract you're about to honor or break
- **Any documentation, comment, or prompt template** that references the behavior you're changing
- **Any orchestration or glue layer** (compose files, Makefile targets, entrypoints) that wires the touched component into the rest of the system

If mid-review you discover the change touches more than you thought, **expand the review** — do not push ahead with a partial picture.

### Phase 3: Understand Before Acting

Before writing code, answer these internally:

1. **Root cause** — not the symptom, the actual root cause?
2. **Blast radius** — which other files, modules, behaviors, or contracts does this change affect?
3. **Stable contracts** — does the fix break any stable internal contract that downstream consumers rely on? Examples include the `AggregatedPayload` schema (consumed by `aggregate_results` and report generation), MCP tool signatures, and any documented prompt/template structure.
4. **Security invariants** — does it violate any core safety rule? Shell-injection safety (`shell=False`), secret/API-key handling, Pydantic validation of MCP tool inputs, authorization checks tied to the active verification document.
5. **Simplicity** — is there a simpler fix that achieves the same result?

Only after answering all five — write the fix.

---

## Implementation Principles

These govern *how* you write code once the mandatory protocol is complete. They complement Phase 3, not replace it.

### 1. Think Before Coding
**Don't assume. Don't hide confusion. Surface tradeoffs.**

- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them — don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

### 2. Simplicity First
**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask yourself: *"Would a senior engineer say this is overcomplicated?"* If yes, simplify.

### 3. Surgical Changes
**Touch only what you must. Clean up only your own mess.**

When editing existing code:
- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it — don't delete it.

When your changes create orphans:
- Remove imports/variables/functions that **your** changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: every changed line should trace directly to the user's request.

### 4. Goal-Driven Execution
**Define success criteria. Loop until verified.**

Transform tasks into verifiable goals:
- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan:
```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```

Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.

---

## Project Purpose

BLHACKBOX is an MCP-based autonomous pentesting framework. The AI client (Claude Code, Claude Desktop, or ChatGPT) IS the orchestrator — it decides which tools to call, collects raw outputs, and structures them directly into an `AggregatedPayload` via the `aggregate_results` MCP tool before writing the final pentest report.

The MCP host handles all data aggregation directly.

---

## Code Standards

- All Python code must be type-annotated
- All MCP tool inputs must be validated with Pydantic
- All subprocess calls must use `subprocess.run(args_list, shell=False)`
- Never use `shell=True` in subprocess calls
- Never log API keys or secrets
- The `AggregatedPayload` schema (`blhackbox/models/aggregated_payload.py`) is the contract between the MCP host and the reporting tools — do not break it without updating all consumers

---

## Adding a New MCP Server

Follow the existing conventions in the repo — don't invent new patterns. Before you start, read at least one existing server end-to-end to match its structure.

1. Create `new-mcp/` directory alongside the existing server directories
2. Write a Dockerfile matching project conventions (non-root user, health check required, minimal base image)
3. Implement the server using the same MCP framework and transport the other servers use
4. Add the service to `docker-compose.yml` under the appropriate profile
5. Add a `make logs-<n>` target to `Makefile` (use backticks around `<n>` in docs so it renders)
6. Update `.mcp.json` if the server should also be available in the Claude Code Web path
7. Document the exposed tools in the README components table
8. Add unit tests — at minimum, Pydantic validation tests for every tool input

---

## Key Reference Links

| Resource | URL |
|----------|-----|
| MCP Protocol spec | https://modelcontextprotocol.io |
| FastMCP (Python MCP framework) | https://pypi.org/project/fastmcp |
| MCP Gateway | https://hub.docker.com/r/docker/mcp-gateway |
| Portainer CE | https://docs.portainer.io |
| Docker Hub (blhackbox) | https://hub.docker.com/r/crhacky/blhackbox |

---

## Verification Document — Authorization for Pentesting

Before executing any pentest template or offensive action, Claude Code **must** check for an active verification document. This document provides the explicit written authorization that Claude requires before performing security testing activities.

### How it works

1. **User fills in** `verification.env` in the project root with engagement details (target, scope, testing window, authorized activities, signatory, etc.)
2. **User sets** `AUTHORIZATION_STATUS=ACTIVE` once all fields are populated
3. **User runs** `make inject-verification` (or it runs automatically on session start)
4. The script renders `blhackbox/prompts/verification.md` (template) with the env values and writes the active document to `.claude/verification-active.md`
5. Claude Code reads this file at session start to confirm authorization

### Checking authorization at runtime

When a pentest template is loaded (via `get_template` MCP tool), the active verification document is automatically appended as authorization context. If no active verification exists, Claude should inform the user to:

```
1. Edit verification.env with your engagement details
2. Set AUTHORIZATION_STATUS=ACTIVE
3. Run: make inject-verification
```

### Files

| File | Purpose |
|------|---------|
| `verification.env` | User-fillable config (engagement details, scope, permissions) |
| `blhackbox/prompts/verification.md` | Template with `{{PLACEHOLDER}}` tokens |
| `blhackbox/prompts/inject_verification.py` | Renders template → active document |
| `.claude/verification-active.md` | Rendered active authorization (git-ignored) |

---

## Self-Check — Are These Guidelines Working?

These guidelines are working if:
- Diffs contain fewer unnecessary changes
- Fewer rewrites due to overcomplication
- Clarifying questions come **before** implementation, not after mistakes
- Every Phase 3 question is answered before code is written
- No `shell=True`, no broken `AggregatedPayload` contracts, no skipped verification checks
- When research is inconclusive or the codebase review surfaces a surprise, it's named explicitly instead of papered over

---

*Only use this framework against targets you have explicit written authorization to test. Unauthorized scanning is illegal.*
