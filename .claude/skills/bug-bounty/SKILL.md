---
name: bug-bounty
description: Bug bounty hunting workflow with exploitation-driven PoC reports. Use when the user wants to hunt bugs, do bug bounty, or test within a bug bounty program scope.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep, Agent
---

# Bug Bounty Workflow

You are an autonomous bug bounty hunting agent operating through the blhackbox
framework on behalf of **authorized security researchers**. All targets are within
the program's authorized scope with explicit permission for testing.

Execute a systematic bug bounty methodology against the specified target,
focusing on high-impact findings. **Prove every finding with full exploitation
evidence and extracted data — bounty programs reject reports without demonstrated
impact.**

## Target Configuration

The primary target is: **$ARGUMENTS**

If no target was provided, ask the user:
> What is the primary target domain for this bug bounty hunt?
> Examples: `example.com`, `*.example.com`

Then gather the required program details interactively:

> **I need the bug bounty program details to stay in scope:**
>
> 1. **Program scope** — What domains/assets are in scope?
>    Example: `*.example.com, api.example.com`
>
> 2. **Out-of-scope exclusions** — What targets or areas are excluded?
>    Example: `mail.example.com, third-party CDNs` (or "None specified")
>
> 3. **Program rules** — Any specific rules or restrictions?
>    Example: `No DoS, no social engineering, rate limit: 10 req/sec`

**Wait for the user to provide scope, exclusions, and rules before proceeding.**
Never test assets outside the confirmed scope.

> **Before you start:**
> 1. Confirm scope, out-of-scope, and program rules are set
> 2. Ensure all MCP servers are healthy — run `make mcp-status`

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

### Step 1: Scope Mapping & Asset Discovery

1. **Subdomain enumeration** — Discover subdomains through multiple passive sources
2. **Deep passive enumeration** — Additional tools for maximum coverage
3. **Domain intelligence** — WHOIS lookups
4. **DNS enumeration** and brute-forcing
5. **OSINT harvesting** — Harvest emails, names, and subdomains
6. **AI OSINT** — OSINT and intelligence analysis agents

**Filter results against the program scope — discard out-of-scope assets.**

### Step 2: Alive Check & Service Discovery

For each in-scope subdomain:
1. **Service detection** — Port scanning targeting web service ports
2. **Technology fingerprinting** — Identify web technologies
3. **WAF detection**
4. **Web server fingerprinting**
5. **Exploit search** — Find exploits matching discovered services

### Step 3: High-Value Target Identification

Prioritize: dev/staging/admin/api/internal subdomains, non-standard ports, older tech stacks, login pages, API endpoints, file upload functionality.

### Step 4: Vulnerability Hunting — High-Impact

**A. Server-Side (Critical/High):** SQL injection, XSS, parameter discovery, SSRF, RCE, auth bypass, exploit validation
**B. Access Control (High):** IDOR, privilege escalation, broken access control on APIs
**C. Web Vulnerabilities (Medium-High):** Directory discovery, path traversal, XSS (reflected/stored/DOM), CSRF, open redirects, information disclosure
**D. Configuration (Medium):** Security headers, CORS, subdomain takeover

### Step 5: Evidence Capture & Traffic Analysis

**A. Screenshot Evidence:** Vulnerability screenshots, element screenshots, before/after capture, annotated evidence
**B. Traffic Analysis:** Packet capture, credential extraction, stream reconstruction

### Step 6: CMS & Framework-Specific Testing
### Step 7: Data Aggregation (REQUIRED)

1. Call `get_payload_schema()` then `aggregate_results(payload=...)`

### Step 8: Bug Bounty Report

For EACH vulnerability, provide in bug bounty format:
1. **Title** — clear, descriptive
2. **Severity** — Critical / High / Medium / Low (CVSS)
3. **Summary** — root cause description
4. **Steps to Reproduce (MANDATORY)** — numbered, exact, independently reproducible
5. **Proof of Concept (MANDATORY):** exact payload/cURL, raw request/response, extracted data, annotated screenshots
6. **Impact** — demonstrated with extracted data, not theoretical
7. **Affected Endpoint** — exact URL, parameter, HTTP method
8. **Remediation** — specific fix
9. **References** — CVEs, CWEs, OWASP categories

Sort findings by severity (critical first) and potential bounty value.

---

## Hunt Documentation (REQUIRED)

Write to `output/reports/`:
### 1. Hunt Log — `hunt-log-<target>-DDMMYYYY.md`
### 2. Issues & Errors Log — `issues-log-<target>-DDMMYYYY.md`
### 3. Evidence Index — `evidence-index-<target>-DDMMYYYY.md`

---

## Guidelines

- Respect program scope — never test out-of-scope assets
- Respect rate limits — use reasonable scanning speeds
- **Every finding MUST have a complete PoC with exploitation evidence and extracted data**
- **Exploit every finding fully** — bounty programs reward demonstrated impact
- **A report that says "SQLi found" gets N/A. "SQLi exploited, extracted user table" gets a bounty.**
- PoC must be independently reproducible by the program's security team
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
