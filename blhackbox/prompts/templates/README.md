# Prompt Templates for Autonomous Pentesting

These templates provide structured workflows for Claude Code to execute
autonomous penetration tests through the blhackbox framework. Each template
instructs Claude to use **all available resources**:

| Resource | Protocol | Port | Description |
|----------|----------|------|-------------|
| **Kali MCP Server** | SSE | 9001 | 15+ Kali Linux security tools (nmap, nikto, gobuster, etc.) |
| **HexStrike REST API** | HTTP | 8888 | 150+ tools and 12+ AI agents |
| **Ollama MCP Server** | SSE | 9000 | 3-agent preprocessing pipeline (Ingestion, Processing, Synthesis) |

## Available Templates

| Template | File | Description |
|----------|------|-------------|
| **Full Pentest** | `full-pentest.md` | Complete 5-phase end-to-end penetration test |
| **Full Attack Chain** | `full-attack-chain.md` | Complete attack chain: recon through exploitation with full reporting |
| **Quick Scan** | `quick-scan.md` | Fast high-level scan for critical issues |
| **Deep Recon** | `recon-deep.md` | Comprehensive reconnaissance and attack surface mapping |
| **Web App Assessment** | `web-app-assessment.md` | Focused web application security testing |
| **Network Infrastructure** | `network-infrastructure.md` | Network-focused infrastructure assessment |
| **OSINT Gathering** | `osint-gathering.md` | Passive open-source intelligence collection |
| **Vulnerability Assessment** | `vuln-assessment.md` | Systematic vulnerability identification and validation |
| **API Security** | `api-security.md` | API-specific security testing (OWASP API Top 10) |
| **Bug Bounty** | `bug-bounty.md` | Bug bounty hunting methodology with PoC-style reports |

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
| First time assessing a target | **Quick Scan** |
| Initial engagement, need attack surface map | **Deep Recon** |
| Full authorized penetration test | **Full Pentest** |
| Full pentest with exploitation and attack chains | **Full Attack Chain** |
| Testing a web application | **Web App Assessment** |
| Assessing network infrastructure | **Network Infrastructure** |
| Passive-only intelligence gathering | **OSINT Gathering** |
| Identifying vulnerabilities without exploitation | **Vulnerability Assessment** |
| Testing REST/GraphQL APIs specifically | **API Security** |
| Bug bounty program participation | **Bug Bounty** |

## Legal Notice

All templates include authorization disclaimers. You **must** have explicit,
written authorization from the target owner before executing any assessment.
Unauthorized access to computer systems is illegal.
