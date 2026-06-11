# Deep Reconnaissance

You are an autonomous reconnaissance agent operating through the blhackbox
framework. Execute a comprehensive reconnaissance operation against the
specified target to map its complete attack surface.

## Configuration — Edit These Placeholders

```
# ┌──────────────────────────────────────────────────────────────────┐
# │  EDIT THE VALUE BELOW before running this template.             │
# │  Replace everything between the quotes with your actual value.  │
# └──────────────────────────────────────────────────────────────────┘

TARGET = "[TARGET]"
# ↑ Replace with your target domain, IP, or URL.
# Examples: "example.com", "192.168.1.0/24", "https://app.example.com"
```

> **Before you start:**
> 1. Confirm the `TARGET` placeholder above is set to your actual target
> 2. Ensure all MCP servers are healthy — run `make mcp-status`
> 3. Query each server's tool listing to discover available recon capabilities

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

Gather all available information about the target domain:

1. **Domain registration** — WHOIS lookups to gather registrar, nameservers, dates, and ownership data
2. **DNS enumeration** — Full DNS record enumeration (A, AAAA, MX, TXT, NS, SOA, SRV) and zone transfer checks
3. **DNS reconnaissance** — DNS record brute-forcing and additional record discovery
4. **OSINT harvesting** — Harvest emails, names, and subdomains from public sources
5. **AI-driven intelligence** — Intelligence analysis and OSINT agents for automated target profiling

### Step 2: Subdomain Enumeration

Discover all subdomains associated with the target:

1. **Passive subdomain discovery** — Enumerate subdomains through multiple passive sources
2. **Deep passive enumeration** — Run additional subdomain discovery tools for maximum coverage
3. Cross-reference results from AI OSINT output (Step 1)
4. Compile a deduplicated master list of all discovered subdomains

### Step 3: Network Mapping

Map the network infrastructure for the target and all discovered subdomains:

1. **Service detection** — Comprehensive port scanning with service and OS fingerprinting on the primary target
2. **Full port discovery** — High-speed full port range scanning
3. **Subdomain scanning** — Service detection on top discovered subdomains (up to 10)
4. **Auxiliary scanning** — Supplemental port and service scanning
5. **Exploit landscape** — Search for exploits matching discovered services (for attack surface awareness)
6. **Traffic capture** — Capture and analyze network traffic during active scanning
7. **Conversation analysis** — Identify all TCP/UDP conversations during reconnaissance
8. **AI-driven network scanning** — Network scan agent for comprehensive assessment

### Step 4: Technology Fingerprinting

Identify the technology stack for all web-facing services:

1. **Web technology identification** — Fingerprint web technologies on the target and discovered subdomains
2. **WAF/CDN detection** — Detect web application firewalls and CDN presence
3. **Metadata extraction** — Extract metadata from any downloadable files
4. **Web reconnaissance** — Web recon agents for automated web technology analysis

### Step 5: Data Aggregation (REQUIRED)

> **This step is mandatory.** You handle data aggregation directly — no
> external pipeline needed.

1. Call `get_payload_schema()` to retrieve the `AggregatedPayload` JSON schema (cache after first call)
2. Parse, deduplicate, and correlate all raw outputs into the schema yourself
3. Call `aggregate_results(payload=<your AggregatedPayload>)` to validate and persist
4. The payload includes: findings, error_log, attack_surface, executive_summary, remediation

### Step 6: Reconnaissance Report

Using the `AggregatedPayload`, produce a detailed recon report:

1. **Attack Surface Map** — all hosts, subdomains, open ports, services, technologies
2. **DNS & Domain Intelligence** — WHOIS, registrar, nameservers, DNS records
3. **Subdomain Inventory** — full list with IP resolution and service info
4. **Technology Stack** — frameworks, CMS, server software, CDN/WAF detection
5. **Network Traffic Insights** — conversation patterns and protocol distribution from captures
6. **Potential Entry Points** — services, login panels, APIs, admin interfaces, exploitable services
7. **Recommendations for Next Phase** — suggested targets for vulnerability assessment

---

## Reconnaissance Documentation (REQUIRED)

Document the entire recon operation thoroughly. At the end, write the following
files to `output/reports/` alongside the recon report. Use the target name and
current date in each filename.

### 1. Recon Log — `recon-log-[TARGET]-DDMMYYYY.md`

Chronological record of the reconnaissance operation:

- **Session metadata** — target, template used (`recon-deep`), session ID,
  start/end timestamps, total duration
- **Step-by-step execution log** — for every step (1 through 6):
  - Step name and stated objective
  - Each tool executed: tool name, parameters passed, execution status
    (success / failure / timeout / partial), key output summary
  - Data points discovered in this step (subdomains, IPs, services, etc.)
  - Decisions and rationale — why specific tools were chosen, why any
    enumeration paths were skipped
- **Tool execution summary table** — every tool called:
  `Tool | Step | Status | Duration | Notes`
- **Discovery statistics** — total subdomains found, total hosts, total ports,
  total services, total technologies identified
- **Coverage assessment** — what recon areas were covered, what was NOT covered
  and why (tool unavailable, target type not applicable, etc.)

### 2. Issues & Errors Log — `issues-log-[TARGET]-DDMMYYYY.md`

Record of every problem and anomaly encountered:

- **Tool failures** — tool name, error message, impact on recon coverage,
  workaround applied
- **Scan anomalies** — DNS resolution failures, timeouts, rate limiting,
  geo-restrictions, blocked requests
- **Warnings** — partial results, incomplete enumerations, truncated outputs
- **Skipped steps** — what was skipped and why (not applicable to target type,
  tool unavailable, prerequisite not met)
- **Data quality notes** — confidence levels, duplicate detection accuracy,
  areas where data may be incomplete

### 3. Discovery Index — `discovery-index-[TARGET]-DDMMYYYY.md`

A structured catalog of everything discovered:

- **Subdomain inventory** — every subdomain with IP, status (live/dead),
  discovery source (which tool found it)
- **DNS record inventory** — complete record listing by type, with raw values
- **Service inventory** — every host:port:service combination discovered
- **Technology inventory** — every technology identified, with version and
  detection source
- **OSINT findings** — emails, names, metadata extracted, organized by source

> **Write all three documentation files at recon end.** These files provide the
> foundation data for follow-up vulnerability assessment or pentest engagements.

---

## Guidelines

- Focus on reconnaissance only — do not attempt exploitation
- Run passive tools first, then active scanning
- Record every tool output for post-processing
- Log and continue on tool errors
