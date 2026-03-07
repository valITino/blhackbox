# Network Infrastructure Assessment

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

---

## Execution Plan

### Step 1: Host Discovery & Port Scanning

1. **High-speed port sweep** — Full port range scanning at high speed
2. **Host discovery** — Ping sweep/host discovery (if scanning a range)
3. **Service detection** — Comprehensive service detection with OS fingerprinting
4. **Auxiliary port scanning** — Supplemental TCP and SYN-based port scanning
5. **Traffic capture** — Capture network traffic during scanning
6. **Interface discovery** — Identify available capture interfaces
7. **AI network scanning** — Network scan agent for comprehensive assessment

### Step 2: Service Enumeration

For each discovered host and port:

1. **Detailed version detection** — High-intensity service version detection
2. **Banner grabbing** — Collect service banners
3. **SMB enumeration** — SMB/Windows enumeration and OS discovery
4. **Service-specific scanning** — Targeted service scanners (SMB, SSH, FTP, SNMP versions)
5. **Protocol-specific scripts** — Service-specific detection scripts covering SSH, HTTP, SMB, DNS, FTP, and SMTP services

### Step 3: Network Traffic Analysis

1. **Conversation extraction** — Extract all TCP/UDP/IP conversations from captured traffic
2. **Protocol statistics** — Protocol hierarchy and endpoint statistics
3. **Credential extraction** — Find cleartext credentials in network traffic (FTP, Telnet, HTTP, SMTP)
4. **Stream inspection** — Reconstruct and inspect suspicious network streams

### Step 4: Vulnerability Scanning

1. **NSE vulnerability scripts** — Targeted vulnerability detection scripts
2. **Exploit search** — Find exploit modules matching discovered services and versions
3. **Auxiliary vulnerability scanners** — Service-specific vulnerability scanners
4. **AI vulnerability scanning** — Vulnerability scan and intelligence analysis agents

### Step 5: DNS & Network Intelligence

1. **Domain registration** — WHOIS lookups
2. **DNS enumeration** — Comprehensive DNS record enumeration
3. **DNS brute-forcing** — DNS record brute-forcing
4. **DNS reconnaissance** — DNS recon and zone transfer checks (if domain target)

### Step 6: Default Credential Testing

For discovered services (SSH, FTP, HTTP auth, databases):

1. **Credential brute-forcing** — Testing default/common credentials against discovered login services
2. **Parallel credential testing** — Parallel network login testing
3. **SMB credential testing** — SMB-specific credential testing
4. **SSH credential validation** — SSH login validation
5. Focus on: SSH, FTP, Telnet, HTTP-Basic, MySQL, PostgreSQL, MSSQL, Redis, MongoDB

**Important:** Use only default/common credential lists. Do not run exhaustive
brute force attacks without explicit authorization.

### Step 7: Data Aggregation (REQUIRED)

> **This step is mandatory.** You handle data aggregation directly — no
> external pipeline needed.

1. Call `get_payload_schema()` to retrieve the `AggregatedPayload` JSON schema (cache after first call)
2. Parse, deduplicate, and correlate all raw outputs into the schema yourself
3. Call `aggregate_results(payload=<your AggregatedPayload>)` to validate and persist
4. The payload includes: findings, error_log, attack_surface, executive_summary, remediation

### Step 8: Network Assessment Report

Using the `AggregatedPayload`, produce a detailed report.

> **Every finding MUST include a Proof of Concept.** A finding that only
> describes a vulnerability without demonstrating it is not valid.

For each finding, include a complete PoC:
- Numbered reproduction steps (independently reproducible)
- Exact command/payload used (copy-pasteable)
- Raw tool output or service response proving the finding
- Impact demonstration (what the attacker gained — shown, not described)
- Screenshot evidence (where applicable)

Findings without PoC must be downgraded to "info" severity.

Report sections:

1. **Executive Summary** — overall network security posture
2. **Host Inventory** — all discovered hosts with OS, ports, services, versions
3. **Network Topology** — discovered network structure and relationships
4. **Service Analysis** — exposed services, versions, known CVEs
5. **Network Traffic Analysis** — conversation analysis, protocol distribution, credential findings
6. **Vulnerability Findings** — all vulnerabilities by severity, with CVSS and full PoC
7. **Default Credentials** — discovered weak/default credentials with service, login pair, and proof
8. **DNS & Infrastructure** — DNS records, zone transfer results, WHOIS data
9. **Attack Chains** — paths from initial access to deeper compromise
10. **Remediation Roadmap** — prioritized by risk and effort
11. **Appendix** — raw host inventory, full port tables, scan metadata

---

## Guidelines

- Start with host discovery, then detailed scanning
- Use rate limiting appropriate to the authorized scope
- Test default credentials only — no exhaustive brute force without explicit approval
- Record every tool output for post-processing
- Pay special attention to exposed management interfaces
- **Every finding MUST have a PoC** — reproduction steps, exact payload, raw evidence, and impact proof
- Findings without PoC are not valid and must be downgraded to "info" severity
- Populate `poc_steps`, `poc_payload`, and `evidence` fields in every `VulnerabilityEntry`
