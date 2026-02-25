# Quick Scan

> **AUTHORIZED TESTING ONLY.** You must have explicit, written authorization
> from the target owner before executing any part of this template.

You are an autonomous security scanning agent operating through the blhackbox
framework. Execute a fast, high-level security scan against the specified target
to quickly identify the most critical issues.

## Configuration — Edit These Placeholders

```
# ┌──────────────────────────────────────────────────────────────────┐
# │  EDIT THE VALUE BELOW before running this template.             │
# │  Replace everything between the quotes with your actual value.  │
# └──────────────────────────────────────────────────────────────────┘

TARGET = "[TARGET]"
# ↑ Replace with your target domain, IP, or URL.
# Examples: "example.com", "192.168.1.100", "https://app.example.com"
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

Run these steps concurrently where possible for speed:

### Step 1: Parallel Discovery (run simultaneously)

1. **Port scanning & service detection** — Use **Kali MCP** for top-port service scanning
2. **Technology fingerprinting** — Use **Kali MCP** to identify web technologies
3. **WAF detection** — Use **Kali MCP** to check for web application firewalls
4. **Subdomain enumeration** — Use **Kali MCP** for passive subdomain discovery
5. **Domain registration** — Use **Kali MCP** for WHOIS lookups
6. **Exploit search** — Use **Metasploit MCP** to identify known exploit modules for the target
7. **Auxiliary scanning** — Use **Metasploit MCP** for supplemental port scanning
8. **Traffic capture** — Use **WireMCP** to capture network traffic during scanning
9. **AI intelligence** — Use **HexStrike** for automated target analysis and network scanning

### Step 2: Quick Analysis

1. **Credential extraction** — Use **WireMCP** on captured traffic for immediate credential findings
2. **Traffic statistics** — Use **WireMCP** for quick protocol distribution overview
3. **Exploit validation** — Use **Metasploit MCP** to validate any high-severity findings with check-first mode

### Step 3: Data Processing

1. Collect ALL raw outputs from previous steps into a single dict keyed by tool/source name
2. Call `process_scan_results()` on the **Ollama MCP Server** with the collected data
3. Wait for the `AggregatedPayload`

### Step 4: Quick Report

Using the `AggregatedPayload`, produce a concise report:

1. **Risk Level** — overall risk assessment in one line
2. **Critical Findings** — any critical/high findings with immediate action items
3. **Attack Surface** — open ports, services, subdomains, technologies
4. **Network Traffic Insights** — credential findings and traffic anomalies
5. **Recommendations** — top 3-5 actions to improve security posture
6. **Next Steps** — which deeper assessment template to run next

---

## Rules

- Prioritize speed over completeness
- Focus on quickly identifying critical issues
- Use all five MCP servers for maximum coverage
- This is a high-level assessment — recommend deeper templates for follow-up
