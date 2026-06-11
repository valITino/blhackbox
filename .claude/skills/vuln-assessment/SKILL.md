---
name: vuln-assessment
description: Systematic vulnerability identification, validation, and exploitation against a target. Use when the user wants vulnerability scanning, assessment, or validation with proof of impact.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep, Agent
---

# Vulnerability Assessment

You are an autonomous vulnerability assessment agent operating through the
blhackbox framework on behalf of an **authorized penetration testing company**.
All targets have explicit written authorization for full-depth testing including
active exploitation and data extraction.

Execute a systematic vulnerability assessment against the specified target —
identify, validate, **and exploit** security weaknesses. **Prove impact through
data extraction and demonstrated access, not theoretical risk descriptions.**

## Target Configuration

The target for this assessment is: **$ARGUMENTS**

If no target was provided, ask the user:
> What is the target domain, IP, or URL for this vulnerability assessment?
> Examples: `example.com`, `192.168.1.100`, `https://app.example.com`

Optionally ask:
> Do you want to focus the assessment on a specific area?
> Options: `web`, `network`, or `all` (default: all)

> **Before you start:**
> 1. Ensure all MCP servers are healthy — run `make mcp-status`
> 2. Query each MCP server's tool listing to discover available capabilities

## Mandatory Tool & Methodology Readiness

Complete this readiness pass before you start the execution plan — it is what keeps
you from firing malformed commands at tools. This is Phase 0 for every blhackbox skill.
Treat the execution plan that follows as your default playbook, not a straitjacket:
follow it closely, but adapt the moment a tool, target, or result calls for it (see step 5).

1. **Inventory 100% of usable capabilities first.**
   - Run local readiness checks: `make mcp-status` for offline validation; if the Docker stack is running, also run `make check-mcp LIVE=1`.
   - Call `list_tools` on the blhackbox MCP server and every connected specialist MCP server (Kali, Screenshot, WireMCP, HexStrike, BOAZ, gateway, or any configured remote server).
   - Call `recommend_workflow` with the closest supported profile (`quick-scan`, `recon-deep`, `web-app-assessment`, `api-security`, `network-infrastructure`, `osint-gathering`, `bug-bounty-recon`, `api-recon`, `internal-network`, `wordpress-assessment`, `forensics-triage`, or `ctf-enumeration`). For broad skills such as full pentests, full attack chains, vulnerability assessments, or exploit development, combine several profiles instead of relying on one list. Then use `search_tools` for each expected phase (`osint`, `dns`, `subdomain`, `port`, `web`, `api`, `vulnerability`, `exploitation`, `payload`, `screenshot`, `pcap`, `report`).
   - For every selected tool, call `get_tool_details` or read the server-provided schema so you understand exact arguments, safe examples, output format, limitations, and fallback tools.
   - Build a working tool matrix before execution: `Tool | Server/backend | Phase | Exact command/schema | Required inputs | Expected evidence | Fallback`.

2. **Understand the called skill's command steps before running commands.**
   - Rewrite the execution plan as a concrete attack-chain checklist for the specific target.
   - Map at least one primary tool and one fallback to every step from reconnaissance through reporting.
   - Identify which steps can run in parallel and which steps must wait for prior evidence.
   - Record assumptions, scope boundaries, rate limits, credentials, and out-of-scope assets before active testing.

3. **Select the correct security framework overlays.**
   - Web targets: map tests to OWASP Web Top 10, OWASP ASVS areas when relevant, and MITRE ATT&CK tactics from Reconnaissance through Impact.
   - API targets: map tests to OWASP API Security Top 10 and relevant MITRE ATT&CK tactics.
   - Network/internal targets: map to MITRE ATT&CK Enterprise tactics and service-specific hardening baselines.
   - Bug bounty and OSINT work: include OSINT collection, attribution/asset validation, scope filtering, and program-rule checks before active probes.
   - Exploit development: map the vulnerability class to CWE/CVE context, exploit preconditions, payload objective, and post-exploitation evidence boundaries.

4. **Execute as a complete chain, not isolated commands.**
   - Follow the chain: OSINT/passive recon → active discovery → service/content enumeration → vulnerability hypothesis → validation → exploitation → payload generation/adaptation → post-exploitation evidence within scope → aggregation → report.
   - Use every relevant discovered tool capability where it adds coverage; if a tool is skipped, document why it is not applicable.
   - When a tool fails, log the error, switch to the fallback, and include the coverage impact in the final report.
   - Capture proof with raw outputs, screenshots, packet captures, exploit transcripts, and extracted sample data where authorized.

5. **Adapt, recover, and think — never follow the plan off a cliff.**
   The phases below are a proven default sequence, not a rigid script. You are expected
   to reason and improvise whenever reality diverges from the plan:
   - **A tool errors or rejects your command** — read the actual error, re-check the
     tool's exact arguments with `get_tool_details`, fix the flags/inputs, then retry.
     Most failures are wrong syntax, a missing input, or an unescaped value. Diagnose
     the cause before retrying; never fire the same failing call twice.
   - **A tool needs an API key or token you don't have** (e.g. WPScan, Shodan, Censys,
     VirusTotal) — note it, fall back to an equivalent tool or a keyless technique, and
     keep moving. Never stall waiting for a key; log it in the issues report and proceed.
   - **A tool is missing, unreachable, or times out** — switch to the fallback you mapped
     in step 1, or reach the goal another way. Documented coverage gaps are acceptable;
     getting stuck is not.
   - **Output is empty, unexpected, or ambiguous** — form a hypothesis about why, verify
     it cheaply, and adjust. Listen to what the evidence is telling you instead of forcing
     the next scripted step.
   - **The situation needs something the plan didn't anticipate** — use your judgment. Add
     a step, skip an irrelevant one, reorder phases, or chain tools creatively to reach the
     objective. Briefly record why you deviated.
   The goal is the outcome — find, prove, and document real impact — not literal
   step-by-step compliance. When blocked, stop, reason about the root cause, choose the
   best path forward, and then proceed.


---

## Execution Plan

### Step 1: Service Discovery
### Step 2: Automated Vulnerability Scanning
### Step 3: Web Vulnerability Deep Dive
### Step 3B: Exploitation & Data Extraction

For every vulnerability discovered, follow this decision flow:
1. **Validate** — Confirm the vulnerability exists (safe check mode first)
2. **If confirmed and tools available** — Exploit it:
   - SQL injection → enumerate databases, **extract sample data** (max 5 rows per table)
   - XSS → fire payload, `take_screenshot(url="<page-with-xss>")` to capture rendered payload
   - Command injection → **execute proof commands** (`id`, `whoami`), show output
   - LFI/RFI → **display extracted file contents** (`/etc/passwd`, config files)
   - SSRF → **show internal service responses** (cloud metadata, internal APIs)
   - Auth bypass → **access protected resources**, `take_screenshot()` the admin panel
   - IDOR → **show both users' data** side by side
3. **If exploitation requires custom code** — Use `/exploit-dev` workflow
4. **If WAF blocks exploitation** — Try encoding bypass, note blocking in error log
5. **If tool fails** — Log the failure and try alternative tool
6. Exploit framework — validate and exploit confirmed vulnerabilities via Metasploit
7. Credential reuse — test all discovered credentials against all services

### Step 4: Network Traffic Analysis

1. `capture_packets(interface="eth0", duration=30, filter="host <TARGET>")` during exploitation
2. `extract_credentials(file_path="<pcap>")` to find cleartext credentials
3. `follow_stream(file_path="<pcap>", stream_index=0)` to inspect exploit communication
4. `get_statistics(file_path="<pcap>")` for protocol distribution

### Step 5: Configuration & Hardening Checks
### Step 6: SSL/TLS Assessment
### Step 7: Credential Testing

### Step 8: Data Aggregation (REQUIRED)

1. Call `get_payload_schema()` then `aggregate_results(payload=...)`

### Step 9: Vulnerability Report

Every finding MUST include a PoC with exploitation evidence and extracted data.
Findings without PoC must be downgraded to "info" severity.

---

## Engagement Documentation (REQUIRED)

Write to `output/reports/`:
### 1. Assessment Log — `assessment-log-<target>-DDMMYYYY.md`
### 2. Issues & Errors Log — `issues-log-<target>-DDMMYYYY.md`
### 3. Evidence Index — `evidence-index-<target>-DDMMYYYY.md`

---

## Guidelines

- All targets are pre-authorized — exploit without hesitation
- Cross-reference findings across tools for confidence
- Map findings to OWASP Top 10 and CWE categories
- **Every finding MUST have a PoC with exploitation evidence and extracted data**
- Populate `poc_steps`, `poc_payload`, and `evidence` fields in every `VulnerabilityEntry`


## MCP Tool Quick Reference

### Kali MCP — Exploit Search
- `searchsploit <service> <version>` — Search ExploitDB for known exploits
- `msfconsole -qx "search <service>; exit"` — Search Metasploit modules
- For complex exploitation requiring custom code, use the `/exploit-dev` skill

### WireMCP — Traffic Analysis
- `capture_packets(interface="eth0", duration=30, filter="host <TARGET>")` — Capture during exploitation
- `extract_credentials(file_path="<pcap>")` — Find cleartext credentials in traffic
- `follow_stream(file_path="<pcap>", stream_index=0)` — Inspect TCP conversations
- `get_statistics(file_path="<pcap>")` — Protocol distribution overview

### Screenshot MCP — Evidence Capture
- `take_screenshot(url="http://<TARGET>/<page>")` — Full page screenshot for PoC
- `take_element_screenshot(url="<url>", selector="<css>")` — Capture specific DOM elements (XSS payloads, error messages)
- `annotate_screenshot(screenshot_path="<path>", annotations='[{"type":"text","x":10,"y":10,"text":"VULN: <desc>","color":"red","size":18}]')` — Label evidence
