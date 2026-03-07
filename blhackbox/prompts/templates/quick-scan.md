# Quick Scan

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

---

## Execution Plan

Run these steps concurrently where possible for speed:

### Step 1: Parallel Discovery (run simultaneously)

1. **Port scanning & service detection** — Scan top ports with service fingerprinting
2. **Technology fingerprinting** — Identify web technologies, frameworks, and CMS
3. **WAF detection** — Check for web application firewalls
4. **Subdomain enumeration** — Discover subdomains through passive sources
5. **Domain registration** — WHOIS lookups for registrar and ownership data
6. **Exploit search** — Identify known exploit modules for discovered services
7. **Traffic capture** — Capture network traffic during scanning for analysis
8. **AI intelligence** — Automated target analysis and network scanning

### Step 2: Quick Analysis

1. **Credential extraction** — Analyze captured traffic for credential findings
2. **Traffic statistics** — Quick protocol distribution overview
3. **Exploit validation** — Validate any high-severity findings

### Step 3: Data Aggregation (REQUIRED)

> **This step is mandatory.** You handle data aggregation directly — no
> external pipeline needed.

1. Call `get_payload_schema()` to retrieve the `AggregatedPayload` JSON schema (cache after first call)
2. Parse, deduplicate, and correlate all raw outputs into the schema yourself
3. Call `aggregate_results(payload=<your AggregatedPayload>)` to validate and persist
4. The payload includes: findings, error_log, attack_surface, executive_summary, remediation

### Step 4: Quick Report

Using the `AggregatedPayload`, produce a concise report:

1. **Risk Level** — overall risk assessment in one line
2. **Critical Findings** — any critical/high findings with immediate action items and PoC evidence
3. **Attack Surface** — open ports, services, subdomains, technologies
4. **Network Traffic Insights** — credential findings and traffic anomalies
5. **Recommendations** — top 3-5 actions to improve security posture
6. **Next Steps** — which deeper assessment template to run next

> Even in a quick scan, any confirmed finding must include evidence (tool output,
> response data) proving it exists. Findings without evidence should be flagged
> as "requires validation" and noted in Next Steps.

---

## Guidelines

- Prioritize speed over completeness
- Focus on quickly identifying critical issues
- This is a high-level assessment — recommend deeper templates for follow-up
- Even in quick mode, include raw evidence for any confirmed finding
- Populate `evidence` field in every `VulnerabilityEntry` — findings without evidence should note "requires deeper validation"
