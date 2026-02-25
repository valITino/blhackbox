# Web Application Security Assessment

> **AUTHORIZED TESTING ONLY.** You must have explicit, written authorization
> from the target owner before executing any part of this template.

You are an autonomous web application security testing agent operating through
the blhackbox framework. Execute a focused web application security assessment
against the specified target.

## Configuration — Edit These Placeholders

```
# ┌──────────────────────────────────────────────────────────────────┐
# │  EDIT THE VALUES BELOW before running this template.            │
# │  Replace everything between the quotes with your actual values. │
# └──────────────────────────────────────────────────────────────────┘

TARGET = "[TARGET]"
# ↑ Replace with the web application URL.
# Examples: "https://app.example.com", "http://192.168.1.100:8080"

# Optional — add if you have credentials for authenticated testing:
# AUTH_COOKIE  = "[SESSION_COOKIE]"
# AUTH_HEADER  = "[AUTHORIZATION_HEADER]"
# USERNAME     = "[USERNAME]"
# PASSWORD     = "[PASSWORD]"
```

## Available Resources — Use ALL of Them

### 1. Kali MCP Server (SSE, port 9001)

Execute via `run_kali_tool(tool, args, target, timeout)`:

| Tool | Use Case |
|------|----------|
| `nikto` | Web server vulnerability scanning |
| `gobuster` | Directory and file brute-forcing |
| `dirb` | Web content discovery |
| `dirsearch` | Web path discovery with extensions |
| `ffuf` | Web fuzzer for directories and parameters |
| `feroxbuster` | Recursive content discovery |
| `whatweb` | Technology fingerprinting |
| `wafw00f` | WAF detection |
| `wpscan` | WordPress vulnerability scanning |
| `sqlmap` | SQL injection testing |
| `nmap` | Port scanning, service detection, NSE scripts |
| `hydra` | Credential brute-forcing |
| `medusa` | Parallel network login brute-forcer |
| `arjun` | HTTP parameter discovery |
| `dalfox` | XSS scanning and parameter analysis |
| `john` | Password hash cracking |
| `hashcat` | GPU-accelerated password cracking |
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

- Web recon agent: `POST http://hexstrike:8888/api/agents/web_recon/run`
- Vulnerability scan agent: `POST http://hexstrike:8888/api/agents/vuln_scan/run`
- Bug bounty agent: `POST http://hexstrike:8888/api/agents/bug_bounty/run`
- Tools: `POST http://hexstrike:8888/api/tools/{tool_name}`

### 5. Ollama MCP Server (SSE, port 9000)

AI preprocessing pipeline via `process_scan_results()`:
- Ingestion Agent — parses raw output to structured data
- Processing Agent — deduplicates, correlates, validates
- Synthesis Agent — produces AggregatedPayload with executive summary

---

## Execution Plan

### Step 1: Web Server Fingerprinting

1. **Kali MCP** — `whatweb [TARGET]` to identify web technologies, frameworks, CMS
2. **Kali MCP** — `wafw00f [TARGET]` to detect WAF/CDN
3. **Kali MCP** — `nmap -sV -p 80,443,8080,8443 --script=http-headers,http-title,http-server-header,http-methods [TARGET]`
4. **HexStrike** — `POST /api/agents/web_recon/run` with `{"target": "[TARGET]"}`

### Step 2: Directory & Content Discovery

1. **Kali MCP** — `gobuster dir -u [TARGET] -w /usr/share/wordlists/dirb/common.txt -t 50 -x php,html,js,txt,json,xml,bak,old`
2. **Kali MCP** — `dirsearch -u [TARGET] -e php,html,js,txt,json,xml,bak` for web path discovery
3. **Kali MCP** — `ffuf -u [TARGET]/FUZZ -w /usr/share/wordlists/dirb/common.txt` for directory and parameter fuzzing
4. **Kali MCP** — `feroxbuster -u [TARGET] -w /usr/share/wordlists/dirb/common.txt` for recursive content discovery
5. **Kali MCP** — `dirb [TARGET]` as secondary content discovery
6. **Kali MCP** — `arjun -u [TARGET]` for hidden HTTP parameter discovery
7. Look for: admin panels, login pages, API endpoints, config files, backup files, `.git`, `.env`

### Step 3: Vulnerability Scanning

1. **Kali MCP** — `nikto -h [TARGET]` for comprehensive web vulnerability scanning
2. **Kali MCP** — `dalfox url [TARGET]` for XSS scanning and parameter analysis
3. **Metasploit MCP** — `list_exploits` to search for web application exploit modules matching discovered technologies
4. **Metasploit MCP** — `run_auxiliary_module` with web-specific auxiliary scanners (e.g., `auxiliary/scanner/http/http_version`)
5. **HexStrike** — `POST /api/agents/vuln_scan/run` with `{"target": "[TARGET]"}`
6. **HexStrike** — `POST /api/agents/bug_bounty/run` with `{"target": "[TARGET]"}`
7. Check for OWASP Top 10:
   - Injection (SQL, command, LDAP, XPath)
   - Broken authentication
   - Sensitive data exposure
   - XML external entities (XXE)
   - Broken access control
   - Security misconfiguration
   - Cross-site scripting (XSS)
   - Insecure deserialization
   - Known vulnerable components
   - Insufficient logging/monitoring

### Step 4: CMS-Specific Testing

If WordPress detected:
1. **Kali MCP** — `wpscan --url [TARGET] --enumerate vp,vt,u,dbe --api-token [TOKEN]`

If other CMS detected, use appropriate HexStrike tools.

### Step 5: Injection Testing

For each discovered form, parameter, or input point:

1. **Kali MCP** — `sqlmap -u "[URL_WITH_PARAMS]" --batch --level=3 --risk=2`
2. **Kali MCP** — `dalfox url "[URL_WITH_PARAMS]"` for XSS validation
3. **Metasploit MCP** — `run_exploit` with `check_first=true` against web application vulnerabilities (e.g., PHP, Java deserialization)
4. Test parameters for:
   - SQL injection (error-based, blind, time-based, UNION)
   - Command injection
   - LDAP injection
   - Template injection (SSTI)

### Step 6: Traffic Analysis

1. **WireMCP** — `capture_packets` during web testing to capture HTTP request/response traffic
2. **WireMCP** — `extract_credentials` on captured traffic to find cleartext credentials in HTTP, form submissions
3. **WireMCP** — `follow_stream` to reconstruct full HTTP conversations and inspect request/response pairs
4. **WireMCP** — `get_statistics` for protocol hierarchy analysis of web traffic

### Step 7: Security Header & SSL/TLS Analysis

1. **Kali MCP** — `nmap --script=http-security-headers [TARGET]`
2. Check for missing headers:
   - `Content-Security-Policy`
   - `X-Frame-Options`
   - `X-Content-Type-Options`
   - `Strict-Transport-Security`
   - `X-XSS-Protection`
   - `Referrer-Policy`
   - `Permissions-Policy`

### Step 8: Data Processing

1. Collect ALL raw outputs into a dict keyed by tool name:
   ```python
   raw_outputs = {
       "whatweb": "...", "wafw00f": "...", "nmap": "...",
       "gobuster": "...", "dirsearch": "...", "ffuf": "...",
       "feroxbuster": "...", "arjun": "...", "nikto": "...",
       "dalfox": "...", "sqlmap": "...", "wpscan": "...",
       "metasploit_exploits": "...", "metasploit_auxiliary": "...",
       "wiremcp_captures": "...", "wiremcp_credentials": "...",
       "wiremcp_streams": "...",
       "hexstrike_web_recon": "...", "hexstrike_vuln_scan": "...",
       "hexstrike_bug_bounty": "..."
   }
   ```
2. Call `process_scan_results(raw_outputs, "[TARGET]", session_id)` on the **Ollama MCP Server**
3. Wait for the `AggregatedPayload`

### Step 9: Web Application Report

Using the `AggregatedPayload`, produce a detailed report:

1. **Executive Summary** — overall web application security posture
2. **Technology Stack** — identified technologies, frameworks, server info
3. **Findings by OWASP Category** — mapped to OWASP Top 10 categories
4. **Discovered Endpoints** — all paths, admin panels, APIs, login pages
5. **Injection Vulnerabilities** — SQL injection, XSS, command injection findings
6. **Traffic Analysis** — WireMCP packet capture insights, credential findings, HTTP stream analysis
7. **Configuration Issues** — missing headers, SSL issues, default configs
8. **Attack Chains** — how findings can be combined
9. **Remediation Priorities** — ordered by severity and exploitability

---

## Rules

- Focus on web application layer testing
- Test all discovered endpoints and parameters
- Check both HTTP and HTTPS where applicable
- Use ALL five systems (Kali MCP, Metasploit MCP, WireMCP, HexStrike API, Ollama pipeline)
- Do not attempt destructive operations (DELETE, data modification)
- Record every tool output for post-processing
