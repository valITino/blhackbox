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

### Step 5: Data Processing (REQUIRED)

> **This step is mandatory.** All raw outputs must be processed through the
> Ollama agents before generating the final report.

1. Collect ALL raw outputs from Steps 1-4 into a single dict keyed by tool/source name
2. Send all collected data through the **Ollama MCP preprocessing pipeline** (`process_scan_results()`)
3. Wait for the `AggregatedPayload` to return

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

## Guidelines

- Focus on reconnaissance only — do not attempt exploitation
- Run passive tools first, then active scanning
- Record every tool output for post-processing
- Log and continue on tool errors
