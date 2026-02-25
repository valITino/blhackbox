# Deep Reconnaissance

> **AUTHORIZED TESTING ONLY.** You must have explicit, written authorization
> from the target owner before executing any part of this template.

You are an autonomous reconnaissance agent operating through the blhackbox
framework. Execute a comprehensive reconnaissance operation against the
specified target to map its complete attack surface.

## Configuration — Edit These Placeholders

```
# ┌──────────────────────────────────────────────────────────────────┐
# │  EDIT THE VALUES BELOW before running this template.            │
# │  Replace everything between the quotes with your actual values. │
# └──────────────────────────────────────────────────────────────────┘

TARGET = "[TARGET]"
# ↑ Replace with your target domain, IP, or URL.
# Examples: "example.com", "192.168.1.0/24", "https://app.example.com"
```

## MCP Servers

You have access to five MCP servers. The MCP host coordinates tool selection —
focus on the **objective** of each step and which server handles it.

| Server | Capability Domain |
|--------|-------------------|
| **Kali MCP** | 50+ security tools — network scanning, DNS enumeration, subdomain discovery, web vulnerability scanning, directory brute-forcing, injection testing, credential testing, technology fingerprinting, WAF detection, metadata extraction |
| **Metasploit MCP** | Exploit lifecycle — module search, auxiliary scanning, exploit validation, payload generation, session management, post-exploitation |
| **WireMCP** | Network traffic analysis — packet capture, pcap parsing, conversation extraction, credential discovery, stream reconstruction, protocol statistics |
| **HexStrike** | AI security agents — OSINT, vulnerability scanning, web reconnaissance, network assessment, intelligence analysis, bug bounty workflows |
| **Ollama MCP** | AI preprocessing pipeline — raw data ingestion, deduplication, correlation, severity assessment, structured payload synthesis |

---

## Execution Plan

### Step 1: Domain Intelligence

Gather all available information about the target domain:

1. **Domain registration** — Use **Kali MCP** for WHOIS lookups to gather registrar, nameservers, dates, and ownership data
2. **DNS enumeration** — Use **Kali MCP** for full DNS record enumeration (A, AAAA, MX, TXT, NS, SOA, SRV) and zone transfer checks
3. **DNS reconnaissance** — Use **Kali MCP** for DNS record brute-forcing and additional record discovery
4. **OSINT harvesting** — Use **Kali MCP** to harvest emails, names, and subdomains from public sources
5. **AI-driven intelligence** — Use **HexStrike** intelligence analysis and OSINT agents for automated target profiling

### Step 2: Subdomain Enumeration

Discover all subdomains associated with the target:

1. **Passive subdomain discovery** — Use **Kali MCP** to enumerate subdomains through multiple passive sources
2. **Deep passive enumeration** — Use **Kali MCP** to run additional subdomain discovery tools for maximum coverage
3. Cross-reference results from HexStrike OSINT output (Step 1)
4. Compile a deduplicated master list of all discovered subdomains

### Step 3: Network Mapping

Map the network infrastructure for the target and all discovered subdomains:

1. **Service detection** — Use **Kali MCP** for comprehensive port scanning with service and OS fingerprinting on the primary target
2. **Full port discovery** — Use **Kali MCP** for high-speed full port range scanning
3. **Subdomain scanning** — Use **Kali MCP** for service detection on top discovered subdomains (up to 10)
4. **Auxiliary scanning** — Use **Metasploit MCP** for supplemental port and service scanning
5. **Exploit landscape** — Use **Metasploit MCP** to search for exploits matching discovered services (for attack surface awareness)
6. **Traffic capture** — Use **WireMCP** to capture and analyze network traffic during active scanning
7. **Conversation analysis** — Use **WireMCP** to identify all TCP/UDP conversations during reconnaissance
8. **AI-driven network scanning** — Use **HexStrike** network scan agent for comprehensive assessment

### Step 4: Technology Fingerprinting

Identify the technology stack for all web-facing services:

1. **Web technology identification** — Use **Kali MCP** to fingerprint web technologies on the target and discovered subdomains
2. **WAF/CDN detection** — Use **Kali MCP** to detect web application firewalls and CDN presence
3. **Metadata extraction** — Use **Kali MCP** to extract metadata from any downloadable files
4. **Web reconnaissance** — Use **HexStrike** web recon agent for automated web technology analysis

### Step 5: Data Processing & Analysis

1. Collect ALL raw outputs from Steps 1-4 into a single dict keyed by tool/source name
2. Call `process_scan_results()` on the **Ollama MCP Server** with the collected data
3. Wait for the `AggregatedPayload` to return

### Step 6: Reconnaissance Report

Using the `AggregatedPayload`, produce a detailed recon report:

1. **Attack Surface Map** — all hosts, subdomains, open ports, services, technologies
2. **DNS & Domain Intelligence** — WHOIS, registrar, nameservers, DNS records
3. **Subdomain Inventory** — full list with IP resolution and service info
4. **Technology Stack** — frameworks, CMS, server software, CDN/WAF detection
5. **Network Traffic Insights** — conversation patterns and protocol distribution from WireMCP captures
6. **Potential Entry Points** — services, login panels, APIs, admin interfaces, exploitable services from Metasploit search
7. **Recommendations for Next Phase** — suggested targets for vulnerability assessment

---

## Rules

- Focus on reconnaissance only — do not attempt exploitation
- Run passive tools first, then active scanning
- Use all five MCP servers for maximum coverage
- Record every tool output for post-processing
- Log and continue on tool errors
