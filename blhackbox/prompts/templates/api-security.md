# API Security Testing

> **AUTHORIZED TESTING ONLY.** You must have explicit, written authorization
> from the target owner before executing any part of this template.

You are an autonomous API security testing agent operating through the
blhackbox framework. Execute a focused API security assessment against
the specified target's API endpoints.

## Configuration — Edit These Placeholders

```
# ┌──────────────────────────────────────────────────────────────────┐
# │  EDIT THE VALUES BELOW before running this template.            │
# │  Replace everything between the quotes with your actual values. │
# └──────────────────────────────────────────────────────────────────┘

TARGET = "[TARGET_API_BASE_URL]"
# ↑ Replace with the API base URL.
# Examples: "https://api.example.com", "http://192.168.1.100:3000/api/v1"

# Optional — provide API documentation:
# API_DOCS_URL   = "[SWAGGER_OR_OPENAPI_URL]"
# e.g. "https://api.example.com/swagger.json"

# Optional — provide authentication:
# API_KEY        = "[API_KEY]"
# AUTH_TOKEN     = "[BEARER_TOKEN]"
# AUTH_HEADER    = "[CUSTOM_AUTH_HEADER]"
```

## Available Resources — Use ALL of Them

### Kali MCP Server (SSE, port 9001)
API-relevant tools: `nmap`, `nikto`, `gobuster`, `sqlmap`, `whatweb`, `wafw00f`

### HexStrike REST API (HTTP, port 8888)
- Web recon agent: `POST http://hexstrike:8888/api/agents/web_recon/run`
- Vulnerability scan agent: `POST http://hexstrike:8888/api/agents/vuln_scan/run`
- Bug bounty agent: `POST http://hexstrike:8888/api/agents/bug_bounty/run`
- Tools: `POST http://hexstrike:8888/api/tools/{tool_name}`

### Ollama MCP Server (SSE, port 9000)
Pipeline: `process_scan_results(raw_outputs, target, session_id)`

---

## Execution Plan

### Step 1: API Discovery & Fingerprinting

1. **Kali MCP** — `whatweb [TARGET]` to identify API framework and server
2. **Kali MCP** — `wafw00f [TARGET]` to detect API gateway/WAF
3. **Kali MCP** — `nmap -sV -p 80,443,8080,8443,3000,5000,8000 --script=http-title,http-headers [TARGET]`
4. **Kali MCP** — `gobuster dir -u [TARGET] -w /usr/share/wordlists/dirb/common.txt -x json,xml,yaml -t 30` to discover API paths
5. **HexStrike** — `POST /api/agents/web_recon/run` with `{"target": "[TARGET]"}`

Look for:
- API documentation endpoints (`/swagger`, `/api-docs`, `/openapi.json`, `/graphql`)
- Version prefixes (`/api/v1/`, `/api/v2/`)
- Health/status endpoints (`/health`, `/status`, `/ping`)
- Admin/management endpoints (`/admin`, `/manage`, `/internal`)

### Step 2: API Endpoint Enumeration

1. **Kali MCP** — `gobuster dir -u [TARGET]/api -w /usr/share/wordlists/dirb/common.txt -t 30`
2. **Kali MCP** — `gobuster dir -u [TARGET]/api/v1 -w /usr/share/wordlists/dirb/common.txt -t 30`
3. Scan for common API patterns:
   - REST: `/users`, `/accounts`, `/orders`, `/products`, `/files`, `/uploads`
   - Auth: `/login`, `/register`, `/token`, `/oauth`, `/auth`
   - Admin: `/admin`, `/dashboard`, `/config`, `/settings`
   - GraphQL: `/graphql`, `/gql`

### Step 3: Authentication & Authorization Testing

1. Test authentication mechanisms:
   - Missing authentication on sensitive endpoints
   - Weak token validation (JWT none algorithm, expired tokens)
   - API key exposure in responses or headers
2. Test authorization:
   - Horizontal privilege escalation (IDOR — access other users' data)
   - Vertical privilege escalation (access admin functions as regular user)
   - Missing function-level access controls

### Step 4: Injection Testing

1. **Kali MCP** — `sqlmap -u "[API_ENDPOINT]" --batch --level=3 --risk=2 --headers="Content-Type: application/json"`
2. **HexStrike** — `POST /api/agents/vuln_scan/run` with `{"target": "[TARGET]"}`
3. Test for:
   - SQL injection in query parameters, JSON body fields, headers
   - NoSQL injection (MongoDB operators in JSON body)
   - Command injection in file processing or system call endpoints
   - LDAP injection in authentication endpoints
   - Server-side template injection (SSTI)

### Step 5: API-Specific Vulnerability Testing

1. **Kali MCP** — `nikto -h [TARGET]` for web-level vulnerabilities
2. **HexStrike** — `POST /api/agents/bug_bounty/run` with `{"target": "[TARGET]"}`
3. Test for OWASP API Security Top 10:
   - **API1** — Broken Object Level Authorization (BOLA/IDOR)
   - **API2** — Broken Authentication
   - **API3** — Broken Object Property Level Authorization
   - **API4** — Unrestricted Resource Consumption (rate limiting)
   - **API5** — Broken Function Level Authorization
   - **API6** — Unrestricted Access to Sensitive Business Flows
   - **API7** — Server Side Request Forgery (SSRF)
   - **API8** — Security Misconfiguration
   - **API9** — Improper Inventory Management (shadow APIs)
   - **API10** — Unsafe Consumption of APIs

### Step 6: Data Exposure & Security Headers

1. **Kali MCP** — `nmap --script=http-security-headers [TARGET]`
2. Check for:
   - Sensitive data in API responses (passwords, tokens, PII)
   - Verbose error messages exposing internals
   - Missing CORS restrictions or overly permissive CORS
   - Missing rate limiting (test with rapid requests)
   - Information disclosure in headers (server version, framework)
   - Missing security headers (CSP, HSTS, X-Content-Type-Options)

### Step 7: Data Processing

1. Collect ALL raw outputs:
   ```python
   raw_outputs = {
       "whatweb": "...", "wafw00f": "...", "nmap": "...",
       "gobuster_api": "...", "nikto": "...", "sqlmap": "...",
       "hexstrike_web_recon": "...", "hexstrike_vuln_scan": "...",
       "hexstrike_bug_bounty": "..."
   }
   ```
2. Call `process_scan_results(raw_outputs, "[TARGET]", session_id)` on the **Ollama MCP Server**
3. Wait for the `AggregatedPayload`

### Step 8: API Security Report

Using the `AggregatedPayload`, produce a detailed report:

1. **Executive Summary** — API security posture overview
2. **API Inventory** — all discovered endpoints with methods and response codes
3. **Authentication Assessment** — auth mechanism analysis and weaknesses
4. **Authorization Issues** — BOLA, IDOR, privilege escalation findings
5. **Injection Vulnerabilities** — SQL, NoSQL, command injection findings
6. **OWASP API Top 10 Mapping** — findings mapped to API-specific risks
7. **Data Exposure** — sensitive data leaks, verbose errors, missing protections
8. **Configuration Issues** — CORS, rate limiting, security headers
9. **Attack Chains** — combined API vulnerability paths
10. **Remediation Priorities** — ordered by severity and exploitability

---

## Rules

- Focus on API-specific security concerns
- Test all discovered endpoints and HTTP methods
- Check both authenticated and unauthenticated access
- Use ALL three systems (Kali MCP, HexStrike API, Ollama pipeline)
- Record every tool output for post-processing
- Map findings to OWASP API Security Top 10
- Do not modify or delete data through the API
