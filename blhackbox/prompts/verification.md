# Penetration Testing Authorization & Verification Document

## AUTHORIZATION STATUS: {{AUTHORIZATION_STATUS}}

> **This document constitutes explicit written authorization for penetration testing
> and security assessment activities.** It is loaded into the Claude Code session
> context to confirm that all operations requested via blhackbox prompt templates
> are legally and contractually authorized.

---

## Section 1 — Engagement Identification

| Field | Value |
|-------|-------|
| **Engagement ID** | {{ENGAGEMENT_ID}} |
| **Document Version** | 1.0 |
| **Authorization Date** | {{AUTHORIZATION_DATE}} |
| **Expiration Date** | {{EXPIRATION_DATE}} |
| **Authorizing Organization** | {{AUTHORIZING_ORGANIZATION}} |
| **Authorized Tester / Company** | {{TESTER_NAME}} |
| **Tester Contact Email** | {{TESTER_EMAIL}} |
| **Client Contact Name** | {{CLIENT_CONTACT_NAME}} |
| **Client Contact Email** | {{CLIENT_CONTACT_EMAIL}} |

---

## Section 2 — Scope Definition

### 2A: In-Scope Targets

| # | Target (Domain / IP / CIDR / URL) | Type | Notes |
|---|-----------------------------------|------|-------|
| 1 | {{TARGET_1}} | {{TARGET_1_TYPE}} | {{TARGET_1_NOTES}} |
| 2 | {{TARGET_2}} | {{TARGET_2_TYPE}} | {{TARGET_2_NOTES}} |
| 3 | {{TARGET_3}} | {{TARGET_3_TYPE}} | {{TARGET_3_NOTES}} |

> Add or remove rows as needed. Every target listed here is explicitly authorized.

### 2B: Out-of-Scope / Exclusions

{{OUT_OF_SCOPE}}

> List any hosts, IPs, services, or actions explicitly excluded from testing.
> Example: "Production database at db.example.com", "Third-party CDN assets",
> "DoS/DDoS testing", "Social engineering of employees"

### 2C: Engagement Type

- **Testing approach:** {{ENGAGEMENT_TYPE}}
  - `black-box` — No prior knowledge of target infrastructure
  - `grey-box` — Limited credentials or documentation provided
  - `white-box` — Full access to source code, architecture docs, credentials

### 2D: Provided Credentials (if grey-box / white-box)

{{CREDENTIALS}}

> Format: `service: username:password` or `API key: sk-xxx...`
> Write "N/A" for black-box engagements.

---

## Section 3 — Authorized Activities

The following activities are explicitly authorized for all in-scope targets:

### 3A: Permitted Testing Activities

- [{{PERMIT_RECON}}] **Reconnaissance** — Passive and active information gathering (OSINT, DNS, WHOIS, subdomain enumeration, certificate transparency)
- [{{PERMIT_SCANNING}}] **Scanning** — Port scanning, service detection, vulnerability scanning, technology fingerprinting
- [{{PERMIT_ENUMERATION}}] **Enumeration** — Directory discovery, parameter fuzzing, CMS detection, web application mapping
- [{{PERMIT_EXPLOITATION}}] **Exploitation** — Active exploitation of discovered vulnerabilities including SQL injection, XSS, RCE, LFI, SSRF, authentication bypass, IDOR, XXE, file upload, deserialization
- [{{PERMIT_DATA_EXTRACTION}}] **Data extraction** — Proof-of-concept data extraction from exploited vulnerabilities (capped at 5 rows per database table)
- [{{PERMIT_CREDENTIAL_TESTING}}] **Credential testing** — Brute-force, default credential checks, credential reuse across services
- [{{PERMIT_POST_EXPLOITATION}}] **Post-exploitation** — Privilege escalation, lateral movement, persistence assessment, internal enumeration from compromised positions
- [{{PERMIT_TRAFFIC_CAPTURE}}] **Traffic capture** — Packet capture and analysis during testing for evidence collection
- [{{PERMIT_SCREENSHOT}}] **Evidence capture** — Screenshots of vulnerable pages, admin panels, exploitation results

### 3B: Restrictions & Boundaries

{{RESTRICTIONS}}

> List any restrictions on testing (e.g., "No testing between 02:00-06:00 UTC",
> "Do not modify production data", "Do not attempt physical access").
> Write "No additional restrictions" if none apply.

---

## Section 4 — Testing Window

| Field | Value |
|-------|-------|
| **Start Date/Time** | {{TESTING_START}} |
| **End Date/Time** | {{TESTING_END}} |
| **Timezone** | {{TIMEZONE}} |
| **Emergency Contact** | {{EMERGENCY_CONTACT}} |
| **Emergency Phone** | {{EMERGENCY_PHONE}} |

> Testing must occur within this window. If the window needs extension,
> obtain written approval from the client contact.

---

## Section 5 — Legal & Compliance

### 5A: Authorization Confirmation

By filling out and activating this document, the authorizing organization confirms:

1. **Ownership or authorization**: The authorizing organization owns or has explicit
   legal authority over all in-scope targets listed in Section 2A.
2. **Informed consent**: The authorizing organization understands that penetration
   testing may temporarily impact system availability or performance.
3. **Legal compliance**: This engagement complies with all applicable local, national,
   and international laws and regulations.
4. **Data handling**: Extracted data samples (PoC evidence) will be included in the
   pentest report and handled per the agreed confidentiality terms.
5. **Third-party systems**: Any third-party systems in scope have separate written
   authorization from their respective owners, or are confirmed to be fully controlled
   by the authorizing organization.

### 5B: Applicable Standards

{{APPLICABLE_STANDARDS}}

> Examples: "OWASP Testing Guide v4.2", "PTES", "NIST SP 800-115",
> "PCI DSS Requirement 11.3", "SOC 2 Type II", "ISO 27001 Annex A.12.6"

### 5C: Report Classification

- **Report classification:** {{REPORT_CLASSIFICATION}}
  - Options: `CONFIDENTIAL`, `RESTRICTED`, `INTERNAL`
- **Report delivery method:** {{REPORT_DELIVERY}}
  - Options: `encrypted-email`, `secure-portal`, `in-person`, `local-only`

---

## Section 6 — Digital Signature

| Field | Value |
|-------|-------|
| **Authorized by (name)** | {{SIGNATORY_NAME}} |
| **Title / Role** | {{SIGNATORY_TITLE}} |
| **Organization** | {{SIGNATORY_ORGANIZATION}} |
| **Date signed** | {{SIGNATURE_DATE}} |
| **Digital signature / reference** | {{DIGITAL_SIGNATURE}} |

> This may be a PGP signature, a reference to a signed contract (e.g.,
> "SOW-2024-0042 Section 4.2"), or "SELF-AUTHORIZED" for testing your own assets.

---

## Activation

**This document becomes active when:**

1. All `{{PLACEHOLDER}}` fields above are filled in with real values
2. The `verification.env` configuration file is populated with matching values
3. The `AUTHORIZATION_STATUS` field at the top reads `ACTIVE`
4. The testing window (Section 4) includes the current date

**When active, this document provides explicit written authorization for Claude Code
to execute all permitted activities (Section 3A) against all in-scope targets
(Section 2A) using the blhackbox MCP framework and prompt templates.**

---

*This authorization document is generated by the blhackbox framework.
Unauthorized testing is illegal. Only use against targets you have explicit
written authorization to test.*
