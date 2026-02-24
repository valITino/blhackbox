# Network Infrastructure Assessment

> **AUTHORIZED TESTING ONLY.** You must have explicit, written authorization
> from the target owner before executing any part of this template.

You are an autonomous network security assessment agent operating through the
blhackbox framework. Execute a comprehensive network infrastructure assessment
against the specified target or range.

## Configuration — Edit These Placeholders

```
# ┌──────────────────────────────────────────────────────────────────┐
# │  EDIT THE VALUES BELOW before running this template.            │
# │  Replace everything between the quotes with your actual values. │
# └──────────────────────────────────────────────────────────────────┘

TARGET = "[TARGET]"
# ↑ Replace with a single IP, CIDR range, or domain.
# Examples: "10.0.0.0/24", "192.168.1.1", "example.com"

# Optional — restrict scan scope:
# PORTS      = "[PORT_RANGE]"       # e.g. "1-1024", "80,443,8080", "1-65535"
# SCAN_RATE  = "[RATE]"             # e.g. "1000" (packets/sec for masscan)
# EXCLUDES   = "[EXCLUDED_HOSTS]"   # e.g. "10.0.0.1,10.0.0.254"
```

## Available Resources — Use ALL of Them

### Kali MCP Server (SSE, port 9001)
Network tools: `nmap`, `masscan`, `hydra`, `dnsenum`, `fierce`, `whois`

### HexStrike REST API (HTTP, port 8888)
- Network scan agent: `POST http://hexstrike:8888/api/agents/network_scan/run`
- Vulnerability scan agent: `POST http://hexstrike:8888/api/agents/vuln_scan/run`
- Intelligence analysis: `POST http://hexstrike:8888/api/intelligence/analyze-target`
- Tools: `POST http://hexstrike:8888/api/tools/{tool_name}`

### Ollama MCP Server (SSE, port 9000)
Pipeline: `process_scan_results(raw_outputs, target, session_id)`

---

## Execution Plan

### Step 1: Host Discovery & Port Scanning

1. **Kali MCP** — `masscan [TARGET] -p1-65535 --rate=1000` for full port range at high speed
2. **Kali MCP** — `nmap -sn [TARGET]` for host discovery (if scanning a range)
3. **Kali MCP** — `nmap -sV -sC -O -T4 -p- [TARGET]` for comprehensive service detection
4. **HexStrike** — `POST /api/agents/network_scan/run` with `{"target": "[TARGET]"}`

### Step 2: Service Enumeration

For each discovered host and port:

1. **Kali MCP** — `nmap -sV --version-intensity 5 -p [PORTS] [HOST]` for detailed version detection
2. **Kali MCP** — `nmap --script=banner -p [PORTS] [HOST]` for service banners
3. **Kali MCP** — Run service-specific NSE scripts:
   - SSH: `ssh-auth-methods`, `ssh-hostkey`
   - HTTP: `http-title`, `http-headers`, `http-methods`
   - SMB: `smb-os-discovery`, `smb-enum-shares`
   - DNS: `dns-zone-transfer`, `dns-recursion`
   - FTP: `ftp-anon`, `ftp-bounce`
   - SMTP: `smtp-commands`, `smtp-open-relay`

### Step 3: Vulnerability Scanning

1. **Kali MCP** — `nmap --script=vuln -p [PORTS] [HOST]` for NSE vulnerability scripts
2. **HexStrike** — `POST /api/agents/vuln_scan/run` with `{"target": "[TARGET]"}`
3. **HexStrike** — `POST /api/intelligence/analyze-target` with `{"target": "[TARGET]", "analysis_type": "comprehensive"}`

### Step 4: DNS & Network Intelligence

1. **Kali MCP** — `whois [TARGET]`
2. **Kali MCP** — `dnsenum [TARGET]`
3. **Kali MCP** — `fierce --domain [TARGET]` (if domain target)
4. **Kali MCP** — `nmap --script=dns-zone-transfer --script-args dns-zone-transfer.domain=[TARGET]`

### Step 5: Default Credential Testing

For discovered services (SSH, FTP, HTTP auth, databases):

1. **Kali MCP** — `hydra -L /usr/share/wordlists/metasploit/default_users.txt -P /usr/share/wordlists/metasploit/default_pass.txt [HOST] [SERVICE]`
2. Focus on: SSH, FTP, Telnet, HTTP-Basic, MySQL, PostgreSQL, MSSQL, Redis, MongoDB

**Important:** Use only default/common credential lists. Do not run exhaustive
brute force attacks without explicit authorization.

### Step 6: Data Processing

1. Collect ALL raw outputs into a single dict keyed by tool name
2. Call `process_scan_results(raw_outputs, "[TARGET]", session_id)` on the **Ollama MCP Server**
3. Wait for the `AggregatedPayload`

### Step 7: Network Assessment Report

Using the `AggregatedPayload`, produce a detailed report:

1. **Executive Summary** — overall network security posture
2. **Host Inventory** — all discovered hosts with OS, ports, services, versions
3. **Network Topology** — discovered network structure and relationships
4. **Service Analysis** — exposed services, versions, known CVEs
5. **Vulnerability Findings** — all vulnerabilities by severity, with CVSS scores
6. **Default Credentials** — any discovered weak/default credentials
7. **DNS & Infrastructure** — DNS records, zone transfer results, WHOIS data
8. **Attack Chains** — paths from initial access to deeper compromise
9. **Remediation Roadmap** — prioritized by risk and effort
10. **Appendix** — raw host inventory, full port tables, scan metadata

---

## Rules

- Start with host discovery, then detailed scanning
- Use rate limiting appropriate to the authorized scope
- Test default credentials only — no exhaustive brute force without explicit approval
- Use ALL three systems (Kali MCP, HexStrike API, Ollama pipeline)
- Record every tool output for post-processing
- Pay special attention to exposed management interfaces
