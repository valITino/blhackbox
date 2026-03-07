# Vulnerability Assessment

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

---

## Execution Plan

### Step 1: Service Discovery

1. **Service detection** — Comprehensive port scanning with service and OS detection
2. **Technology fingerprinting** — Identify web technologies
3. **WAF detection** — Detect web application firewalls
4. **Auxiliary scanning** — Supplemental port scanning
5. **AI network scanning** — Network scan agent for comprehensive assessment

### Step 2: Automated Vulnerability Scanning

1. **NSE vulnerability scripts** — Targeted vulnerability detection scripts on discovered ports
2. **NSE exploit scripts** — Safe exploit-check scripts
3. **Web vulnerability scanning** — Comprehensive web server vulnerability checks
4. **Exploit search** — Find exploit modules matching discovered services and CVEs
5. **Auxiliary vulnerability scanners** — Service-specific vulnerability scanners
6. **Exploit validation** — Validate exploitability without executing payloads
7. **AI vulnerability scanning** — Vulnerability scan and intelligence analysis agents

### Step 3: Web Vulnerability Deep Dive

For each web service discovered:

1. **Directory discovery** — Directory and file brute-forcing with common wordlists and extensions
2. **Web path discovery** — Additional path discovery with multiple tools for coverage
3. **Parameter discovery** — Hidden HTTP parameter discovery and fuzzing
4. **SQL injection testing** — Automated SQL injection testing
5. **XSS scanning** — XSS detection and parameter analysis
6. **CMS scanning** — CMS-specific vulnerability scanning (if applicable)
7. **Web reconnaissance** — Web recon agents
8. Test for:
   - SQL injection (blind, error-based, time-based)
   - Cross-site scripting (reflected, stored)
   - Local/Remote file inclusion
   - Server-side request forgery (SSRF)
   - XML external entities (XXE)
   - Insecure direct object references (IDOR)

### Step 4: Network Traffic Analysis

1. **Packet capture** — Capture traffic during vulnerability scanning
2. **Credential extraction** — Find cleartext credentials in captured network traffic
3. **Protocol statistics** — Protocol hierarchy analysis
4. **Stream inspection** — Inspect suspicious network communications

### Step 5: Configuration & Hardening Checks

1. **Security headers** — HTTP security header analysis
2. Check for:
   - Missing security headers (CSP, HSTS, X-Frame-Options, etc.)
   - Exposed server version information
   - Default error pages revealing technology stack
   - Directory listing enabled
   - Debug modes enabled
   - CORS misconfiguration
   - Cookie security flags (Secure, HttpOnly, SameSite)

### Step 6: SSL/TLS Assessment

1. **SSL/TLS analysis** — Cipher suite enumeration and certificate inspection
2. Check for:
   - Expired or self-signed certificates
   - Weak cipher suites (RC4, DES, 3DES)
   - Outdated protocols (SSLv2, SSLv3, TLSv1.0, TLSv1.1)
   - Certificate chain issues
   - Missing HSTS header

### Step 7: Credential Testing

1. **Credential brute-forcing** — Testing default/common credentials against discovered login services
2. **Parallel credential testing** — Parallel network login testing
3. **SMB credential testing** — SMB-specific credential testing
4. Test only default/common credentials for discovered login services
5. Focus on: admin panels, SSH, FTP, database ports

### Step 8: Data Aggregation (REQUIRED)

> **This step is mandatory.** You handle data aggregation directly — no
> external pipeline needed.

1. Call `get_payload_schema()` to retrieve the `AggregatedPayload` JSON schema (cache after first call)
2. Parse, deduplicate, and correlate all raw outputs into the schema yourself
3. Call `aggregate_results(payload=<your AggregatedPayload>)` to validate and persist
4. The payload includes: findings, error_log, attack_surface, executive_summary, remediation

### Step 9: Vulnerability Report

Using the `AggregatedPayload`, produce a detailed report.

> **Every finding MUST include a Proof of Concept.** A finding that only
> describes a vulnerability without demonstrating it is not valid.

For each finding (critical through low), include:
- CVE/CWE identifiers and CVSS score
- Root cause description (not just the symptom)
- **PoC: Numbered reproduction steps** (independently reproducible)
- **PoC: Exact payload/command** (copy-pasteable)
- **PoC: Raw evidence output** (tool output or HTTP response proving exploitation)
- **PoC: Impact demonstration** (what the attacker gained — shown, not described)
- **PoC: Screenshot evidence** (where applicable)
- Remediation with specific technical steps

Findings without PoC must be downgraded to "info" severity.

Report sections:

1. **Executive Summary** — total vulnerabilities by severity, risk posture
2. **Methodology** — tools used, scanning approach, coverage
3. **Critical & High Findings** — each with full PoC (steps, payload, evidence, impact)
4. **Medium & Low Findings** — each with PoC (same structure, may be condensed)
5. **False Positive Analysis** — flagged items with rationale
6. **Network Traffic Analysis** — credential findings, traffic anomalies
7. **Configuration Weaknesses** — missing headers, weak SSL, information disclosure
8. **Attack Chains** — combined vulnerability paths
9. **Remediation Roadmap** — prioritized by severity, exploitability, and effort
10. **Appendix** — full service inventory, scan metadata

---

## Guidelines

- Identify and validate vulnerabilities — do not exploit them beyond safe checks
- Cross-reference findings across tools for confidence (multi-tool confirmation)
- Flag potential false positives where evidence is weak
- Record every tool output for post-processing
- Classify severity using CVSS where available
- Map findings to OWASP Top 10 and CWE categories
- **Every finding MUST have a PoC** — reproduction steps, exact payload, raw evidence, and impact proof
- Findings without PoC are not valid and must be downgraded to "info" severity
- Populate `poc_steps`, `poc_payload`, and `evidence` fields in every `VulnerabilityEntry`
