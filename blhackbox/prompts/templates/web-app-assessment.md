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

### Kali MCP Server (SSE, port 9001)
Web-focused tools: `nikto`, `gobuster`, `dirb`, `whatweb`, `wafw00f`, `wpscan`,
`sqlmap`, `nmap` (HTTP scripts)

### HexStrike REST API (HTTP, port 8888)
- Web recon agent: `POST http://hexstrike:8888/api/agents/web_recon/run`
- Vulnerability scan agent: `POST http://hexstrike:8888/api/agents/vuln_scan/run`
- Bug bounty agent: `POST http://hexstrike:8888/api/agents/bug_bounty/run`
- Tools: `POST http://hexstrike:8888/api/tools/{tool_name}`

### Ollama MCP Server (SSE, port 9000)
Pipeline: `process_scan_results(raw_outputs, target, session_id)`

---

## Execution Plan

### Step 1: Web Server Fingerprinting

1. **Kali MCP** — `whatweb [TARGET]` to identify web technologies, frameworks, CMS
2. **Kali MCP** — `wafw00f [TARGET]` to detect WAF/CDN
3. **Kali MCP** — `nmap -sV -p 80,443,8080,8443 --script=http-headers,http-title,http-server-header,http-methods [TARGET]`
4. **HexStrike** — `POST /api/agents/web_recon/run` with `{"target": "[TARGET]"}`

### Step 2: Directory & Content Discovery

1. **Kali MCP** — `gobuster dir -u [TARGET] -w /usr/share/wordlists/dirb/common.txt -t 50 -x php,html,js,txt,json,xml,bak,old`
2. **Kali MCP** — `gobuster dir -u [TARGET] -w /usr/share/wordlists/dirbuster/directory-list-2.3-medium.txt -t 30` (deeper scan)
3. **Kali MCP** — `dirb [TARGET]` as secondary content discovery
4. Look for: admin panels, login pages, API endpoints, config files, backup files, `.git`, `.env`

### Step 3: Vulnerability Scanning

1. **Kali MCP** — `nikto -h [TARGET]` for comprehensive web vulnerability scanning
2. **HexStrike** — `POST /api/agents/vuln_scan/run` with `{"target": "[TARGET]"}`
3. **HexStrike** — `POST /api/agents/bug_bounty/run` with `{"target": "[TARGET]"}`
4. Check for OWASP Top 10:
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
2. Test parameters for:
   - SQL injection (error-based, blind, time-based, UNION)
   - Command injection
   - LDAP injection
   - Template injection (SSTI)

### Step 6: Security Header & SSL/TLS Analysis

1. **Kali MCP** — `nmap --script=http-security-headers [TARGET]`
2. Check for missing headers:
   - `Content-Security-Policy`
   - `X-Frame-Options`
   - `X-Content-Type-Options`
   - `Strict-Transport-Security`
   - `X-XSS-Protection`
   - `Referrer-Policy`
   - `Permissions-Policy`

### Step 7: Data Processing

1. Collect ALL raw outputs into a dict keyed by tool name
2. Call `process_scan_results(raw_outputs, "[TARGET]", session_id)` on the **Ollama MCP Server**
3. Wait for the `AggregatedPayload`

### Step 8: Web Application Report

Using the `AggregatedPayload`, produce a detailed report:

1. **Executive Summary** — overall web application security posture
2. **Technology Stack** — identified technologies, frameworks, server info
3. **Findings by OWASP Category** — mapped to OWASP Top 10 categories
4. **Discovered Endpoints** — all paths, admin panels, APIs, login pages
5. **Injection Vulnerabilities** — SQL injection, XSS, command injection findings
6. **Configuration Issues** — missing headers, SSL issues, default configs
7. **Attack Chains** — how findings can be combined
8. **Remediation Priorities** — ordered by severity and exploitability

---

## Rules

- Focus on web application layer testing
- Test all discovered endpoints and parameters
- Check both HTTP and HTTPS where applicable
- Use ALL three systems (Kali MCP, HexStrike API, Ollama pipeline)
- Do not attempt destructive operations (DELETE, data modification)
- Record every tool output for post-processing
