---
name: recon-deep
description: Comprehensive reconnaissance and attack surface mapping against a target. Use when the user wants deep recon or attack surface discovery without exploitation.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep, Agent
---

# Deep Reconnaissance

You are an autonomous reconnaissance agent operating through the blhackbox
framework. Execute a comprehensive reconnaissance operation against the
specified target to map its complete attack surface.

## Target Configuration

The target for this reconnaissance is: **$ARGUMENTS**

If no target was provided, ask the user:
> What is the target domain, IP, or CIDR range for reconnaissance?
> Examples: `example.com`, `192.168.1.0/24`, `https://app.example.com`

> **Before you start:**
> 1. Ensure all MCP servers are healthy — run `make mcp-status`
> 2. Query each server's tool listing to discover available recon capabilities

## OpSec Discipline (Mandatory)

Run this engagement under operational-security discipline — your own tooling leaves
fingerprints, and so does the browser the Screenshot MCP drives. Manage that
footprint before and during the test; never tamper with the target's logs or evidence.

**Preflight (before the readiness pass below):** invoke `/opsec-check` — or run
`.claude/opsec-audit.sh` — to inventory what this session leaks: egress IP/exit point,
per-tool default User-Agents, JA3/TLS signature, DNS resolver, host timezone/locale,
and the screenshot browser's fingerprint + favicon-cache ("supercookie") exposure.
Resolve every HIGH finding before you touch the target.

**During execution (enforce continuously):** before each outbound action, ask whether
it leaks attribution or contaminates the engagement. If so, fix it first —

- route through the configured SOCKS/VPN/Tor egress, never the raw host IP;
- send a deliberate, non-default User-Agent on web/API tools;
- randomize scan timing instead of using tool defaults;
- drive the screenshot browser in an ephemeral profile and clear its favicon cache
  between targets so a planted supercookie can't correlate your sessions;
- keep per-engagement state isolated — never reuse a browser profile or output dir
  across targets.

Call out any OpSec break and correct it before continuing. This is footprint hygiene,
not target-log tampering. These techniques are for authorized scope — confirm
authorization once at session start, then proceed.

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

### Step 1: Domain Intelligence

1. **Domain registration** — WHOIS lookups to gather registrar, nameservers, dates, and ownership data
2. **DNS enumeration** — Full DNS record enumeration (A, AAAA, MX, TXT, NS, SOA, SRV) and zone transfer checks
3. **DNS reconnaissance** — DNS record brute-forcing and additional record discovery
4. **OSINT harvesting** — Harvest emails, names, and subdomains from public sources
5. **AI-driven intelligence** — Intelligence analysis and OSINT agents for automated target profiling

### Step 2: Subdomain Enumeration

1. **Passive subdomain discovery** — Enumerate subdomains through multiple passive sources
2. **Deep passive enumeration** — Run additional subdomain discovery tools for maximum coverage
3. Cross-reference results from AI OSINT output (Step 1)
4. Compile a deduplicated master list of all discovered subdomains

### Step 3: Network Mapping

1. **Service detection** — Comprehensive port scanning with service and OS fingerprinting
2. **Full port discovery** — High-speed full port range scanning
3. **Subdomain scanning** — Service detection on top discovered subdomains (up to 10)
4. **Auxiliary scanning** — Supplemental port and service scanning
5. **Exploit landscape** — Search for exploits matching discovered services
6. **Traffic capture** — Capture and analyze network traffic during active scanning
7. **Conversation analysis** — Identify all TCP/UDP conversations during reconnaissance
8. **AI-driven network scanning** — Network scan agent for comprehensive assessment

### Step 4: Technology Fingerprinting

1. **Web technology identification** — Fingerprint web technologies on the target and discovered subdomains
2. **WAF/CDN detection** — Detect web application firewalls and CDN presence
3. **Metadata extraction** — Extract metadata from any downloadable files
4. **Web reconnaissance** — Web recon agents for automated web technology analysis

### Step 5: Data Aggregation (REQUIRED)

> **This step is mandatory.**

1. Call `get_payload_schema()` to retrieve the `AggregatedPayload` JSON schema
2. Parse, deduplicate, and correlate all raw outputs into the schema yourself
3. Call `aggregate_results(payload=<your AggregatedPayload>)` to validate and persist

### Step 6: Reconnaissance Report

Using the `AggregatedPayload`, produce a detailed recon report:

1. **Attack Surface Map** — all hosts, subdomains, open ports, services, technologies
2. **DNS & Domain Intelligence** — WHOIS, registrar, nameservers, DNS records
3. **Subdomain Inventory** — full list with IP resolution and service info
4. **Technology Stack** — frameworks, CMS, server software, CDN/WAF detection
5. **Network Traffic Insights** — conversation patterns and protocol distribution
6. **Potential Entry Points** — services, login panels, APIs, admin interfaces
7. **Recommendations for Next Phase** — suggested targets for vulnerability assessment

---

## Reconnaissance Documentation (REQUIRED)

Write the following files to `output/reports/` alongside the recon report.

### 1. Recon Log — `recon-log-<target>-DDMMYYYY.md`
### 2. Issues & Errors Log — `issues-log-<target>-DDMMYYYY.md`
### 3. Discovery Index — `discovery-index-<target>-DDMMYYYY.md`

> **Write all three documentation files at recon end.**

---

## Guidelines

- Focus on reconnaissance only — do not attempt exploitation
- Run passive tools first, then active scanning
- Record every tool output for post-processing
- Log and continue on tool errors

## MCP Tool Quick Reference

### Kali MCP — Passive Reconnaissance
- `subfinder -d <domain>` — Subdomain discovery via passive sources
- `amass enum -passive -d <domain>` — Comprehensive passive subdomain enumeration
- `dig <domain> ANY` — DNS record enumeration
- `whois <domain>` — Domain registration data
- `theharvester -d <domain> -b all` — OSINT email/subdomain harvesting

### WireMCP — DNS Traffic Analysis (if passive DNS capture available)
- `capture_packets(interface="eth0", duration=30, filter="port 53")` — Capture DNS queries during enumeration
- `get_statistics(file_path="<pcap>")` — Protocol distribution showing DNS patterns
- `follow_stream(file_path="<pcap>", stream_index=0)` — Inspect DNS conversations

> **Note:** This is a reconnaissance-only skill. No exploitation, no screenshots. For exploitation, use `/full-pentest` or `/exploit-dev`.
