# Vulnerability Assessment

> **AUTHORIZED TESTING ONLY.** You must have explicit, written authorization
> from the target owner before executing any part of this template.

You are an autonomous vulnerability assessment agent operating through the
blhackbox framework. Execute a systematic vulnerability assessment against the
specified target, identifying and validating security weaknesses.

## Configuration — Edit These Placeholders

```
# ┌──────────────────────────────────────────────────────────────────┐
# │  EDIT THE VALUES BELOW before running this template.            │
# │  Replace everything between the quotes with your actual values. │
# └──────────────────────────────────────────────────────────────────┘

TARGET = "[TARGET]"
# ↑ Replace with your target domain, IP, or URL.
# Examples: "example.com", "192.168.1.100", "https://app.example.com"

# Optional — narrow the assessment scope:
# FOCUS_AREA = "[FOCUS]"
# Options: "web", "network", "all" (default: "all")
```

## Available Resources — Use ALL of Them

### 1. Kali MCP Server (SSE, port 9001)

Execute via `run_kali_tool(tool, args, target, timeout)`:

| Tool | Use Case |
|------|----------|
| `nmap` | Port scanning, service detection, NSE vuln scripts |
| `nikto` | Web server vulnerability scanning |
| `sqlmap` | SQL injection testing |
| `wpscan` | WordPress vulnerability scanning |
| `hydra` | Credential brute-forcing |
| `medusa` | Parallel network login brute-forcer |
| `gobuster` | Directory and file brute-forcing |
| `dirsearch` | Web path discovery with extensions |
| `ffuf` | Web fuzzer for directories and parameters |
| `feroxbuster` | Recursive content discovery |
| `whatweb` | Technology fingerprinting |
| `wafw00f` | WAF detection |
| `arjun` | HTTP parameter discovery |
| `dalfox` | XSS scanning and parameter analysis |
| `dnsrecon` | DNS record brute-forcing |
| `john` | Password hash cracking |
| `hashcat` | GPU-accelerated password cracking |
| `crackmapexec` | Network infrastructure pentesting suite |
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

- Vulnerability scan agent: `POST http://hexstrike:8888/api/agents/vuln_scan/run`
- Network scan agent: `POST http://hexstrike:8888/api/agents/network_scan/run`
- Web recon agent: `POST http://hexstrike:8888/api/agents/web_recon/run`
- Intelligence analysis: `POST http://hexstrike:8888/api/intelligence/analyze-target`
- All tools: `POST http://hexstrike:8888/api/tools/{tool_name}`

### 5. Ollama MCP Server (SSE, port 9000)

AI preprocessing pipeline via `process_scan_results()`:
- Ingestion Agent — parses raw output to structured data
- Processing Agent — deduplicates, correlates, validates
- Synthesis Agent — produces AggregatedPayload with executive summary

---

## Execution Plan

### Step 1: Service Discovery

1. **Kali MCP** — `nmap -sV -sC -O -T4 [TARGET]` for service and OS detection
2. **Kali MCP** — `whatweb [TARGET]` for web technology identification
3. **Kali MCP** — `wafw00f [TARGET]` for WAF detection
4. **Metasploit MCP** — `run_auxiliary_module` with `auxiliary/scanner/portscan/tcp` for supplemental port scanning
5. **HexStrike** — `POST /api/agents/network_scan/run` with `{"target": "[TARGET]"}`

### Step 2: Automated Vulnerability Scanning

1. **Kali MCP** — `nmap --script=vuln -p [DISCOVERED_PORTS] [TARGET]`
2. **Kali MCP** — `nmap --script=exploit -p [DISCOVERED_PORTS] [TARGET]` (safe checks only)
3. **Kali MCP** — `nikto -h [TARGET]` for web vulnerabilities
4. **Metasploit MCP** — `list_exploits` to search for exploit modules matching discovered services and CVEs
5. **Metasploit MCP** — `run_auxiliary_module` with vulnerability-specific scanners (e.g., `auxiliary/scanner/smb/smb_ms17_010`, `auxiliary/scanner/http/http_vuln_cve_*`)
6. **Metasploit MCP** — `run_exploit` with `check_first=true` to validate exploitability without executing payloads
7. **HexStrike** — `POST /api/agents/vuln_scan/run` with `{"target": "[TARGET]"}`
8. **HexStrike** — `POST /api/intelligence/analyze-target` with `{"target": "[TARGET]", "analysis_type": "comprehensive"}`

### Step 3: Web Vulnerability Deep Dive

For each web service discovered:

1. **Kali MCP** — `gobuster dir -u [TARGET] -w /usr/share/wordlists/dirb/common.txt -x php,html,txt,bak`
2. **Kali MCP** — `dirsearch -u [TARGET] -e php,html,js,txt,bak` for web path discovery
3. **Kali MCP** — `ffuf -u [TARGET]/FUZZ -w /usr/share/wordlists/dirb/common.txt` for fuzzing
4. **Kali MCP** — `feroxbuster -u [TARGET] -w /usr/share/wordlists/dirb/common.txt` for recursive discovery
5. **Kali MCP** — `arjun -u [TARGET]` for hidden HTTP parameter discovery
6. **Kali MCP** — `sqlmap -u [URL_WITH_PARAMS] --batch --level=3 --risk=2` for injection testing
7. **Kali MCP** — `dalfox url [TARGET]` for XSS scanning
8. **Kali MCP** — `wpscan --url [TARGET] --enumerate vp,vt,u` (if WordPress)
9. **HexStrike** — `POST /api/agents/web_recon/run` with `{"target": "[TARGET]"}`
10. Test for:
   - SQL injection (blind, error-based, time-based)
   - Cross-site scripting (reflected, stored)
   - Local/Remote file inclusion
   - Server-side request forgery (SSRF)
   - XML external entities (XXE)
   - Insecure direct object references (IDOR)

### Step 4: Network Traffic Analysis

1. **WireMCP** — `capture_packets` during vulnerability scanning to capture traffic patterns
2. **WireMCP** — `extract_credentials` to find cleartext credentials in captured network traffic
3. **WireMCP** — `get_statistics` for protocol hierarchy analysis
4. **WireMCP** — `follow_stream` to inspect suspicious network communications

### Step 5: Configuration & Hardening Checks

1. **Kali MCP** — `nmap --script=http-security-headers [TARGET]`
2. Check for:
   - Missing security headers (CSP, HSTS, X-Frame-Options, etc.)
   - Exposed server version information
   - Default error pages revealing technology stack
   - Directory listing enabled
   - Debug modes enabled
   - CORS misconfiguration
   - Cookie security flags (Secure, HttpOnly, SameSite)

### Step 6: SSL/TLS Assessment

1. **Kali MCP** — `nmap --script=ssl-enum-ciphers,ssl-cert -p 443 [TARGET]`
2. Check for:
   - Expired or self-signed certificates
   - Weak cipher suites (RC4, DES, 3DES)
   - Outdated protocols (SSLv2, SSLv3, TLSv1.0, TLSv1.1)
   - Certificate chain issues
   - Missing HSTS header

### Step 7: Credential Testing

1. **Kali MCP** — `hydra -L /usr/share/wordlists/metasploit/default_users.txt -P /usr/share/wordlists/metasploit/default_pass.txt [TARGET] [SERVICE]`
2. **Kali MCP** — `medusa -h [TARGET] -U /usr/share/wordlists/metasploit/default_users.txt -P /usr/share/wordlists/metasploit/default_pass.txt -M [SERVICE]` for parallel brute-forcing
3. **Kali MCP** — `crackmapexec smb [TARGET] -u users.txt -p passwords.txt` for SMB credential testing
4. Test only default/common credentials for discovered login services
5. Focus on: admin panels, SSH, FTP, database ports

### Step 8: Data Processing

1. Collect ALL raw outputs into a single dict:
   ```python
   raw_outputs = {
       "nmap_services": "...", "nmap_vuln": "...", "nmap_ssl": "...",
       "nikto": "...", "sqlmap": "...", "wpscan": "...",
       "gobuster": "...", "dirsearch": "...", "ffuf": "...",
       "feroxbuster": "...", "arjun": "...", "dalfox": "...",
       "whatweb": "...", "wafw00f": "...",
       "hydra": "...", "medusa": "...", "crackmapexec": "...",
       "metasploit_exploits": "...", "metasploit_auxiliary": "...",
       "metasploit_checks": "...",
       "wiremcp_captures": "...", "wiremcp_credentials": "...",
       "wiremcp_statistics": "...",
       "hexstrike_vuln": "...", "hexstrike_network": "...",
       "hexstrike_web_recon": "...", "hexstrike_intelligence": "..."
   }
   ```
2. Call `process_scan_results(raw_outputs, "[TARGET]", session_id)` on the **Ollama MCP Server**
3. Wait for the `AggregatedPayload`

### Step 9: Vulnerability Report

Using the `AggregatedPayload`, produce a detailed report:

1. **Executive Summary** — total vulnerabilities by severity, risk posture
2. **Methodology** — tools used, scanning approach, coverage
3. **Critical & High Findings** — each with CVE, CVSS, evidence, remediation, references (including Metasploit validation results)
4. **Medium & Low Findings** — grouped and summarized
5. **False Positive Analysis** — flagged items with rationale
6. **Network Traffic Analysis** — WireMCP credential findings, traffic anomalies
7. **Configuration Weaknesses** — missing headers, weak SSL, information disclosure
8. **Attack Chains** — combined vulnerability paths
9. **Remediation Roadmap** — prioritized by severity, exploitability, and effort
10. **Appendix** — full service inventory, scan metadata

---

## Rules

- Identify and validate vulnerabilities — do not exploit them beyond safe checks
- Cross-reference findings across tools for confidence (multi-tool confirmation)
- Flag potential false positives where evidence is weak
- Use ALL five systems (Kali MCP, Metasploit MCP, WireMCP, HexStrike API, Ollama pipeline)
- Record every tool output for post-processing
- Classify severity using CVSS where available
- Map findings to OWASP Top 10 and CWE categories
