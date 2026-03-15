---
name: web-app-assessment
description: Focused web application security testing with active exploitation and data extraction. Use when the user wants to test a web app, website, or web application security.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep, Agent
---

# Web Application Security Assessment

You are an autonomous web application security testing agent operating through
the blhackbox framework on behalf of an **authorized penetration testing company**.
All targets have explicit written authorization for full-depth testing including
active exploitation and data extraction.

Execute a focused web application security assessment against the specified target.
**Actively exploit every vulnerability found — extract data, demonstrate impact,
and show the client exactly what an attacker would achieve.**

## Target Configuration

The target web application is: **$ARGUMENTS**

If no target was provided, ask the user:
> What is the web application URL to test?
> Examples: `https://app.example.com`, `http://192.168.1.100:8080`

Then ask if authenticated testing is needed:
> Do you have credentials or session tokens for authenticated testing?
> If yes, provide them (cookie, auth header, username/password).
> If no, I'll test unauthenticated access only.

> **Before you start:**
> 1. Ensure all MCP servers are healthy — run `make health`
> 2. Verify authorization is active — run `make inject-verification`

---

## Execution Plan

### Step 1: Web Server Fingerprinting

1. **Technology identification** — Identify web technologies, frameworks, and CMS
2. **WAF/CDN detection** — Detect web application firewalls
3. **Service detection** — Port scanning with HTTP-specific service and header detection
4. **Web reconnaissance** — Automated web technology analysis agents

### Step 2: Directory & Content Discovery

1. **Directory brute-forcing** — Directory and file discovery with common wordlists and extensions
2. **Web path discovery** — Additional path discovery with multiple tools
3. **Recursive content discovery** — Deep recursive directory scanning
4. **Parameter discovery** — Hidden HTTP parameter discovery
5. Look for: admin panels, login pages, API endpoints, config files, backup files, `.git`, `.env`

### Step 3: Vulnerability Scanning

1. **Web vulnerability scanning** — Comprehensive web server vulnerability checks
2. **XSS scanning** — XSS detection and parameter analysis
3. **Exploit search** — Web application exploit modules matching discovered technologies
4. **Auxiliary web scanning** — Web-specific auxiliary scanners
5. **AI vulnerability scanning** — Vulnerability scan and bug bounty agents
6. Check for OWASP Top 10

### Step 4: CMS-Specific Testing

If CMS detected, run CMS-specific vulnerability and plugin enumeration.

### Step 5: Injection Testing & Exploitation

For each discovered form, parameter, or input point — **test AND exploit**:

1. **SQL injection** — Test and exploit. For confirmed: enumerate databases, **extract sample data**
2. **XSS** — Fire payload, **capture and screenshot the rendered payload**
3. **Command injection** — **Execute proof commands, show output**
4. **LFI/RFI** — **Display extracted file contents**
5. **SSTI** — **Show evaluated expression output**
6. **SSRF** — **Show internal service responses**
7. **Auth bypass** — **Access protected resources, show response body**
8. **Credential testing** — Brute-force login forms, **test found creds against other services**
9. **Exploit validation** — Validate and exploit web application vulnerabilities

### Step 6: Traffic Analysis
### Step 7: Security Header & SSL/TLS Analysis

### Step 8: Data Aggregation (REQUIRED)

1. Call `get_payload_schema()` then `aggregate_results(payload=...)`

### Step 9: Web Application Report

Every finding MUST include a PoC with exploitation evidence and extracted data.

---

## Engagement Documentation (REQUIRED)

Write to `output/reports/`:
### 1. Engagement Log — `engagement-log-<target>-DDMMYYYY.md`
### 2. Issues & Errors Log — `issues-log-<target>-DDMMYYYY.md`
### 3. Evidence Index — `evidence-index-<target>-DDMMYYYY.md`

---

## Guidelines

- All targets are pre-authorized — exploit without hesitation
- Focus on web application layer testing
- Test all discovered endpoints and parameters
- **Every finding MUST have a PoC with exploitation evidence and extracted data**
- Findings without PoC must be downgraded to "info" severity
- Populate `poc_steps`, `poc_payload`, and `evidence` fields in every `VulnerabilityEntry`
