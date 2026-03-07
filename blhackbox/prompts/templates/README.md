# Prompt Templates for Autonomous Pentesting

These templates provide structured workflows for autonomous penetration tests
through the blhackbox framework. Each template describes **what** needs to be
done in each phase — the MCP host decides **which** tools and servers to use.

All templates are designed for **authorized penetration testing engagements**
where active exploitation, data extraction, and impact demonstration are expected.
Every template mandates PoC-driven reporting with exploitation evidence and
extracted data — not just vulnerability detection.

All raw outputs must be structured into an `AggregatedPayload` by the MCP host
before the final report is generated.

## Available Templates

| Template | File | Description |
|----------|------|-------------|
| **Full Pentest** | `full-pentest.md` | Complete end-to-end penetration test with full exploitation and data extraction |
| **Full Attack Chain** | `full-attack-chain.md` | Recon through exploitation with attack chain reporting and extracted data inventory |
| **Quick Scan** | `quick-scan.md` | Fast scan — exploit critical/high findings on the spot |
| **Deep Recon** | `recon-deep.md` | Comprehensive reconnaissance and attack surface mapping |
| **Web App Assessment** | `web-app-assessment.md` | Web application testing with active exploitation and data extraction |
| **Network Infrastructure** | `network-infrastructure.md` | Network assessment with service exploitation and credential reuse testing |
| **OSINT Gathering** | `osint-gathering.md` | Passive open-source intelligence collection |
| **Vulnerability Assessment** | `vuln-assessment.md` | Vulnerability identification, validation, and exploitation with impact proof |
| **API Security** | `api-security.md` | API security testing with active exploitation (OWASP API Top 10) |
| **Bug Bounty** | `bug-bounty.md` | Bug bounty hunting with exploitation-driven PoC reports |

## Usage

### In Claude Code (Docker)

Copy the template content and replace `[TARGET]` with your actual target:

```
Use the full-pentest template against example.com
```

Or paste the template directly and fill in the target.

### Programmatic Access

Templates are available at:
```
blhackbox/prompts/templates/*.md
```

Load them via the `blhackbox.prompts` module or read them directly from disk.

## Choosing a Template

| Scenario | Template |
|----------|----------|
| First time assessing a target | **Quick Scan** — fast triage, exploits critical findings on the spot |
| Initial engagement, need attack surface map | **Deep Recon** — comprehensive recon before full engagement |
| Full authorized penetration test | **Full Pentest** — complete exploitation with data extraction |
| Full pentest with attack chain focus | **Full Attack Chain** — chains findings for maximum demonstrated impact |
| Testing a web application | **Web App Assessment** — OWASP Top 10 with active exploitation |
| Assessing network infrastructure | **Network Infrastructure** — service exploitation + credential reuse |
| Passive-only intelligence gathering | **OSINT Gathering** — no active probing |
| Systematic vulnerability validation | **Vulnerability Assessment** — find, validate, and exploit |
| Testing REST/GraphQL APIs specifically | **API Security** — OWASP API Top 10 with active exploitation |
| Bug bounty program participation | **Bug Bounty** — exploitation-driven PoC reporting |

## Legal Notice

All templates are intended for authorized testing only. You **must** have
explicit, written authorization from the target owner before executing any
assessment. Unauthorized access to computer systems is illegal.
