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

### 1. Kali MCP Server (SSE, port 9001)

Execute via `run_kali_tool(tool, args, target, timeout)`:

| Tool | Use Case |
|------|----------|
| `nmap` | Port scanning, service detection, NSE scripts |
| `masscan` | High-speed port scanning |
| `hydra` | Credential brute-forcing |
| `medusa` | Parallel network login brute-forcer |
| `dnsenum` | DNS enumeration and zone transfers |
| `dnsrecon` | DNS record brute-forcing |
| `fierce` | DNS reconnaissance |
| `whois` | Domain registration lookup |
| `crackmapexec` | Network infrastructure pentesting suite |
| `theharvester` | OSINT email and subdomain harvesting |
| `john` | Password hash cracking |
| `hashcat` | GPU-accelerated password cracking |
| `binwalk` | Firmware and binary analysis |
| `exiftool` | Metadata extraction |

### 2. Metasploit MCP Server (SSE, port 9002)

Full exploit lifecycle management via MSF RPC — 13+ dedicated tools:

| Tool | Use Case |
|------|----------|
| `list_exploits` | Search Metasploit exploit modules by keyword or CVE |
| `list_payloads` | Search payloads with platform/architecture filtering |
| `run_exploit` | Execute exploits with check-first option |
| `run_auxiliary_module` | Run auxiliary modules (scanners, fuzzers) |
| `run_post_module` | Post-exploitation against active sessions |
| `generate_payload` | Generate payloads (msfvenom equivalent) |
| `list_sessions` | View active shells/meterpreter sessions |
| `send_session_command` | Execute commands in active sessions |
| `terminate_session` | End active sessions |
| `start_listener` | Create multi/handler listeners |
| `stop_job` | Stop background jobs |
| `msf_console_execute` | Raw msfconsole command execution |

### 3. WireMCP Server (SSE, port 9003)

Network traffic capture and analysis via tshark — 7 tools:

| Tool | Use Case |
|------|----------|
| `capture_packets` | Live packet capture with BPF filters |
| `read_pcap` | Parse pcap files with display filters |
| `get_conversations` | Extract TCP/UDP/IP conversations |
| `get_statistics` | Protocol hierarchy and endpoint stats |
| `extract_credentials` | Find cleartext creds (HTTP, FTP, SMTP, Telnet) |
| `follow_stream` | Reconstruct TCP/UDP streams |
| `list_interfaces` | List available capture interfaces |

### 4. HexStrike REST API (HTTP, port 8888)

150+ tools and 12+ AI agents:

- Network scan agent: `POST http://hexstrike:8888/api/agents/network_scan/run`
- Vulnerability scan agent: `POST http://hexstrike:8888/api/agents/vuln_scan/run`
- Intelligence analysis: `POST http://hexstrike:8888/api/intelligence/analyze-target`
- Tools: `POST http://hexstrike:8888/api/tools/{tool_name}`

### 5. Ollama MCP Server (SSE, port 9000)

AI preprocessing pipeline via `process_scan_results()`:
- Ingestion Agent — parses raw output to structured data
- Processing Agent — deduplicates, correlates, validates
- Synthesis Agent — produces AggregatedPayload with executive summary

---

## Execution Plan

### Step 1: Host Discovery & Port Scanning

1. **Kali MCP** — `masscan [TARGET] -p1-65535 --rate=1000` for full port range at high speed
2. **Kali MCP** — `nmap -sn [TARGET]` for host discovery (if scanning a range)
3. **Kali MCP** — `nmap -sV -sC -O -T4 -p- [TARGET]` for comprehensive service detection
4. **Metasploit MCP** — `run_auxiliary_module` with `auxiliary/scanner/portscan/tcp` for supplemental port scanning
5. **Metasploit MCP** — `run_auxiliary_module` with `auxiliary/scanner/portscan/syn` for SYN-based scanning
6. **WireMCP** — `capture_packets` during scanning to capture network traffic for analysis
7. **WireMCP** — `list_interfaces` to identify available capture interfaces
8. **HexStrike** — `POST /api/agents/network_scan/run` with `{"target": "[TARGET]"}`

### Step 2: Service Enumeration

For each discovered host and port:

1. **Kali MCP** — `nmap -sV --version-intensity 5 -p [PORTS] [HOST]` for detailed version detection
2. **Kali MCP** — `nmap --script=banner -p [PORTS] [HOST]` for service banners
3. **Kali MCP** — `crackmapexec smb [HOST]` for SMB enumeration and OS discovery
4. **Metasploit MCP** — `run_auxiliary_module` with service-specific scanners:
   - `auxiliary/scanner/smb/smb_version` — SMB version detection
   - `auxiliary/scanner/ssh/ssh_version` — SSH version detection
   - `auxiliary/scanner/ftp/ftp_version` — FTP version detection
   - `auxiliary/scanner/snmp/snmp_enum` — SNMP enumeration
5. **Kali MCP** — Run service-specific NSE scripts:
   - SSH: `ssh-auth-methods`, `ssh-hostkey`
   - HTTP: `http-title`, `http-headers`, `http-methods`
   - SMB: `smb-os-discovery`, `smb-enum-shares`
   - DNS: `dns-zone-transfer`, `dns-recursion`
   - FTP: `ftp-anon`, `ftp-bounce`
   - SMTP: `smtp-commands`, `smtp-open-relay`

### Step 3: Network Traffic Analysis

1. **WireMCP** — `get_conversations` to extract all TCP/UDP/IP conversations from captured traffic
2. **WireMCP** — `get_statistics` for protocol hierarchy and endpoint statistics
3. **WireMCP** — `extract_credentials` to find cleartext credentials in network traffic (FTP, Telnet, HTTP, SMTP)
4. **WireMCP** — `follow_stream` to reconstruct and inspect suspicious network streams

### Step 4: Vulnerability Scanning

1. **Kali MCP** — `nmap --script=vuln -p [PORTS] [HOST]` for NSE vulnerability scripts
2. **Metasploit MCP** — `list_exploits` to search for exploit modules matching discovered services and versions
3. **Metasploit MCP** — `run_auxiliary_module` for vulnerability-specific scanners (e.g., `auxiliary/scanner/smb/smb_ms17_010`)
4. **HexStrike** — `POST /api/agents/vuln_scan/run` with `{"target": "[TARGET]"}`
5. **HexStrike** — `POST /api/intelligence/analyze-target` with `{"target": "[TARGET]", "analysis_type": "comprehensive"}`

### Step 5: DNS & Network Intelligence

1. **Kali MCP** — `whois [TARGET]`
2. **Kali MCP** — `dnsenum [TARGET]`
3. **Kali MCP** — `dnsrecon -d [TARGET]` for DNS record brute-forcing
4. **Kali MCP** — `fierce --domain [TARGET]` (if domain target)
5. **Kali MCP** — `nmap --script=dns-zone-transfer --script-args dns-zone-transfer.domain=[TARGET]`

### Step 6: Default Credential Testing

For discovered services (SSH, FTP, HTTP auth, databases):

1. **Kali MCP** — `hydra -L /usr/share/wordlists/metasploit/default_users.txt -P /usr/share/wordlists/metasploit/default_pass.txt [HOST] [SERVICE]`
2. **Kali MCP** — `medusa -h [HOST] -U /usr/share/wordlists/metasploit/default_users.txt -P /usr/share/wordlists/metasploit/default_pass.txt -M [SERVICE]` for parallel brute-forcing
3. **Kali MCP** — `crackmapexec smb [HOST] -u users.txt -p passwords.txt` for SMB credential testing
4. **Metasploit MCP** — `run_auxiliary_module` with `auxiliary/scanner/ssh/ssh_login` for SSH credential validation
5. Focus on: SSH, FTP, Telnet, HTTP-Basic, MySQL, PostgreSQL, MSSQL, Redis, MongoDB

**Important:** Use only default/common credential lists. Do not run exhaustive
brute force attacks without explicit authorization.

### Step 7: Data Processing

1. Collect ALL raw outputs into a single dict keyed by tool name:
   ```python
   raw_outputs = {
       "masscan": "...", "nmap_discovery": "...", "nmap_services": "...",
       "crackmapexec": "...", "nmap_vuln": "...",
       "dnsenum": "...", "dnsrecon": "...", "fierce": "...", "whois": "...",
       "hydra": "...", "medusa": "...",
       "metasploit_portscan": "...", "metasploit_service_scanners": "...",
       "metasploit_exploits": "...", "metasploit_vuln_scanners": "...",
       "wiremcp_captures": "...", "wiremcp_conversations": "...",
       "wiremcp_credentials": "...", "wiremcp_statistics": "...",
       "hexstrike_network": "...", "hexstrike_vuln": "...",
       "hexstrike_intelligence": "..."
   }
   ```
2. Call `process_scan_results(raw_outputs, "[TARGET]", session_id)` on the **Ollama MCP Server**
3. Wait for the `AggregatedPayload`

### Step 8: Network Assessment Report

Using the `AggregatedPayload`, produce a detailed report:

1. **Executive Summary** — overall network security posture
2. **Host Inventory** — all discovered hosts with OS, ports, services, versions
3. **Network Topology** — discovered network structure and relationships
4. **Service Analysis** — exposed services, versions, known CVEs
5. **Network Traffic Analysis** — WireMCP conversation analysis, protocol distribution, credential findings
6. **Vulnerability Findings** — all vulnerabilities by severity, with CVSS scores, including Metasploit-confirmed findings
7. **Default Credentials** — any discovered weak/default credentials
8. **DNS & Infrastructure** — DNS records, zone transfer results, WHOIS data
9. **Attack Chains** — paths from initial access to deeper compromise
10. **Remediation Roadmap** — prioritized by risk and effort
11. **Appendix** — raw host inventory, full port tables, scan metadata

---

## Rules

- Start with host discovery, then detailed scanning
- Use rate limiting appropriate to the authorized scope
- Test default credentials only — no exhaustive brute force without explicit approval
- Use ALL five systems (Kali MCP, Metasploit MCP, WireMCP, HexStrike API, Ollama pipeline)
- Record every tool output for post-processing
- Pay special attention to exposed management interfaces
