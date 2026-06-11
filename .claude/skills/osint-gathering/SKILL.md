---
name: osint-gathering
description: Passive open-source intelligence collection against a target domain. Use when the user wants OSINT, passive recon, or intelligence gathering without active scanning.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep, Agent
---

# OSINT & Intelligence Gathering

You are an autonomous OSINT and intelligence gathering agent operating through
the blhackbox framework. Execute a comprehensive open-source intelligence
operation against the specified target using only passive techniques.

## Target Configuration

The target for this OSINT operation is: **$ARGUMENTS**

If no target was provided, ask the user:
> What is the target domain for OSINT gathering?
> Examples: `example.com`, `target-org.io`
> Note: This operation uses PASSIVE techniques only — no active scanning.

> **Before you start:**
> 1. Ensure all MCP servers are healthy — run `make mcp-status`
> 2. Note: This uses **passive techniques only** — no packets sent to target

## Mandatory Tool & Methodology Readiness

Do **not** start the skill's execution plan until this readiness pass is complete.
This is Phase 0 for every blhackbox skill.

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


---

## Execution Plan

### Step 1: Domain & Registrar Intelligence

1. **Domain registration** — WHOIS lookups for registrar, registration dates, registrant organization, nameserver infrastructure
2. **OSINT harvesting** — Harvest emails, names, and subdomains from public sources
3. **Metadata extraction** — Extract metadata from any publicly available documents
4. **AI-driven intelligence** — Intelligence analysis and OSINT agents

### Step 2: DNS Intelligence

1. **DNS enumeration** — Full DNS record enumeration (A, AAAA, MX, TXT, NS, SOA, SRV)
2. **DNS brute-forcing** — DNS record brute-forcing and additional record discovery
3. **DNS reconnaissance** — DNS recon and zone transfer checks
4. **Auxiliary DNS enumeration** — Supplemental DNS enumeration
5. Look for zone transfer opportunities (informational only)

### Step 3: Subdomain Discovery

1. **Passive subdomain enumeration** — Multiple passive sources
2. **Deep passive enumeration** — Additional discovery tools for maximum coverage
3. Compile, deduplicate, and categorize subdomains by purpose

### Step 4: Infrastructure Mapping

From the gathered data, map:
1. IP address ranges and hosting providers
2. Email infrastructure (from MX records)
3. CDN and WAF presence
4. Cloud provider identification (AWS, Azure, GCP patterns)
5. Third-party service integrations (from DNS TXT records)

### Step 5: Traffic Sample Analysis (if available)

If any packet captures or traffic samples are available:
1. **Pcap parsing** — Parse existing traffic captures
2. **Conversation analysis** — Identify communication patterns
3. **Protocol statistics** — Protocol distribution and endpoint analysis
4. **Credential extraction** — Find credentials in traffic samples

### Step 6: Exploit Landscape Research

1. **Exploit search** — Search for known exploits targeting discovered technologies
2. Document the target's potential risk exposure

### Step 7: Data Aggregation (REQUIRED)

1. Call `get_payload_schema()` to retrieve the `AggregatedPayload` JSON schema
2. Parse, deduplicate, and correlate all raw outputs into the schema
3. Call `aggregate_results(payload=<your AggregatedPayload>)` to validate and persist

### Step 8: OSINT Report

Using the `AggregatedPayload`, produce a detailed intelligence report:

1. **Executive Summary** — overall intelligence assessment
2. **Domain Profile** — registrar, dates, status, ownership chain
3. **DNS Infrastructure** — complete record inventory with analysis
4. **Subdomain Map** — all discovered subdomains categorized by function
5. **Infrastructure Footprint** — hosting, cloud, CDN, email providers
6. **Technology Indicators** — technologies revealed through passive analysis
7. **Exploit Landscape** — known exploits and risk exposure
8. **Potential Attack Surface** — entry points identified through OSINT alone
9. **Risk Indicators** — expired domains, dangling DNS, subdomain takeover candidates
10. **Recommendations** — areas requiring further active assessment

---

## OSINT Documentation (REQUIRED)

Write the following files to `output/reports/`:

### 1. Collection Log — `collection-log-<target>-DDMMYYYY.md`
### 2. Issues & Errors Log — `issues-log-<target>-DDMMYYYY.md`
### 3. Intelligence Index — `intelligence-index-<target>-DDMMYYYY.md`

---

## Guidelines

- **PASSIVE ONLY** — do not send probe packets to the target
- No port scanning, no web crawling, no active connections
- Use only publicly available information sources
- Record every tool output for post-processing
- Flag potential subdomain takeover opportunities

## MCP Tool Quick Reference

### Kali MCP — Passive OSINT Tools
- `subfinder -d <domain>` — Passive subdomain enumeration
- `amass enum -passive -d <domain>` — Comprehensive passive enumeration
- `whois <domain>` — Domain registration and ownership
- `dig <domain> ANY` / `dig <domain> AXFR` — DNS records and zone transfer attempts
- `theharvester -d <domain> -b all` — Email, subdomain, and name harvesting
- `fierce --domain <domain>` — DNS reconnaissance

> **Note:** This is a passive-only skill. No active scanning, no exploitation, no screenshots. For active testing, use `/full-pentest`, `/vuln-assessment`, or `/exploit-dev`.
