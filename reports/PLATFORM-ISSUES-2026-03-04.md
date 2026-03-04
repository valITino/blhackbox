# LHackBox Platform — Issues, Errors & Integration Gaps

**Date:** 2026-03-04
**Context:** Full attack chain penetration test against coiffure-grimm.ch using the blhackbox MCP-orchestrated toolchain with Claude Code (Opus 4.6)
**Purpose:** Document all failures, errors, integration gaps, and platform issues encountered during the engagement for engineering review and resolution.

---

## 1. HexStrike — No MCP Integration (CRITICAL GAP)

### Problem

HexStrike is deployed as a Docker container (`hexstrike:8888`) on the same network as all other tools, but it has **no MCP server adapter**. It is the only tool in the entire stack without one.

### What Happened

1. User requested "do a quick web pentest with HexStrike"
2. Claude Code had zero awareness of HexStrike — it does not appear in the tool list
3. Had to manually discover the container via `env | grep hex` (found in `no_proxy` list)
4. Manually port-scanned the container (curl against ports 8080, 5000, 8000, 3000, 80, 8443, 4000, 5050, 7000, 7070, 8888, 9000, 9090, 1337...)
5. Found port 8888 responding (HTTP 404 on most paths, `/health` returned data)
6. Spent ~15 minutes and ~20 curl requests blindly guessing API endpoints (`/run`, `/execute`, `/scan`, `/api/run`, `/tool/httpx`, `/run_tool`, `/quick_scan`, etc.) — none worked
7. Never discovered the actual API routes because there is no OpenAPI spec, no `/docs`, no `/routes`, no `/swagger.json`

### Impact

- HexStrike was **completely unusable** during the entire engagement
- Only 5 of 127 tools were available in HexStrike anyway (httpx, angr, checksec, objdump, strings)
- The `/health` endpoint confirmed the server is healthy but provided no API documentation
- Wasted significant tokens, time, and user patience on discovery

### What's Needed

1. **hexstrike-mcp adapter container** — same pattern as kali-mcp, metasploit-mcp, wire-mcp, screenshot-mcp, ollama-mcp
2. **API documentation** — HexStrike needs an OpenAPI spec or at minimum a `/docs` endpoint listing available routes
3. **Docker Compose registration** — add hexstrike-mcp to the MCP gateway config
4. **Tool availability** — only 5/127 tools are installed; the container reports most as `false`

### Evidence

```bash
$ curl http://hexstrike:8888/health
{
  "status": "healthy",
  "version": "6.0.0",
  "total_tools_available": 5,
  "total_tools_count": 127,
  "tools_status": {
    "angr": true, "checksec": true, "httpx": true,
    "objdump": true, "strings": true,
    "nmap": false, "nikto": false, "sqlmap": false, ... (122 more false)
  }
}

$ curl http://hexstrike:8888/run        --> 404
$ curl http://hexstrike:8888/api        --> 404
$ curl http://hexstrike:8888/execute    --> 404
$ curl http://hexstrike:8888/scan       --> 404
$ curl http://hexstrike:8888/tools      --> 404
$ curl http://hexstrike:8888/docs       --> 404
$ curl http://hexstrike:8888/openapi.json --> 404
```

---

## 2. Metasploit RPC — Authentication Failure (CRITICAL)

### Problem

Every Metasploit MCP tool call failed with `"error": "Not authenticated to msfrpcd"`.

### What Happened

```
mcp__metasploit__list_exploits(search="openresty")
  --> {"error": "Not authenticated to msfrpcd"}

mcp__metasploit__list_exploits(search="wordpress")
  --> {"error": "Not authenticated to msfrpcd"}

mcp__metasploit__msf_console_execute(command="search openssh 7.4")
  --> {"error": "Not authenticated to msfrpcd"}
```

### Impact

- Could not search for exploits matching discovered services (OpenSSH 7.4, MariaDB 10.6.20, Pure-FTPd, WordPress plugins)
- Could not run `auxiliary/scanner/*` modules for service enumeration
- Could not validate vulnerabilities with Metasploit's `check` method
- Could not use any post-exploitation modules
- **Entire Metasploit framework was unavailable for the engagement**

### What's Needed

1. **Fix metasploit-mcp RPC authentication** — credentials may be misconfigured or msfrpcd may not be running
2. **Add health check** to verify msfrpcd connectivity on container startup
3. **Surface authentication errors more clearly** (currently only visible when a tool is called)

---

## 3. Ollama Pipeline — Out of Memory (CRITICAL)

### Problem

All three Ollama pipeline agents (Ingestion, Processing, Synthesis) failed because the llama3.3 model requires **41.5 GiB RAM** but only **12.4 GiB** is available.

### What Happened

```
mcp__ollama-pipeline__process_scan_results(...)
  --> All findings arrays empty
  --> metadata.warning:
      "IngestionAgent returned HTTP 502: Ollama error after 3 attempts:
       model requires more system memory (41.5 GiB) than is available (12.4 GiB)
       (status code: 500)"
      (same for ProcessingAgent and SynthesisAgent)
```

### Impact

- The AggregatedPayload returned completely empty results (all arrays `[]`, all counts `0`)
- Phase 6 (mandatory data processing) produced zero output
- The report had to be generated entirely by Claude Code without Ollama analysis
- 44.24 seconds wasted on 9 failed Ollama API calls (3 agents × 3 retries each)

### What's Needed

1. **Use a smaller model** — llama3.3 (70B params) is too large for 12GB RAM. Use `llama3.1:8b`, `mistral:7b`, or `phi-3:mini` instead
2. **Pre-flight RAM check** — before calling Ollama, check available memory and select an appropriate model
3. **Graceful degradation** — if Ollama fails, the pipeline should return a meaningful error to the caller rather than empty arrays
4. **Configuration option** — allow specifying the Ollama model via environment variable (e.g., `OLLAMA_MODEL=llama3.1:8b`)

---

## 4. Kali Container — Pipe/Shell Limitations

### Problem

The Kali MCP container does not support shell pipe operators (`|`) or complex shell expressions in tool arguments, causing many commands to fail silently or error.

### What Happened

```bash
# These all failed:
curl -sk https://... | grep -oP "wp-content/themes/[^/\"']+"
  --> "curl: option -u: requires parameter" (the pipe was parsed incorrectly)

curl -sk https://... | grep -oiP "ver=[0-9.]+"
  --> exit code 3 (empty/error)
```

The `-u` error is telling: the Kali container is splitting the command on `|` and interpreting `grep -oP "wp-content/themes/[^/\"']+"` as arguments to `curl`, where `-o` is interpreted as curl's `-o` (output) flag.

### Impact

- Could not do inline parsing of web responses (theme/plugin extraction, version detection)
- Had to fall back to running curl from the local container via Bash tool and piping there
- But the local container also had DNS resolution issues for external domains (exit code 6), making this unreliable too

### What's Needed

1. **Support shell pipe operators** in `run_kali_tool` arguments, or
2. **Provide a shell mode** that wraps the command in `bash -c "..."`, or
3. **Add dedicated tools** for common patterns (e.g., `curl_grep`, `fetch_and_filter`)

---

## 5. Kali Container — Missing Wordlists

### Problem

Common wordlists expected by directory brute-forcing tools are not installed in the Kali container.

### What Happened

```
dirb https://www.coiffure-grimm.ch /usr/share/wordlists/dirb/common.txt
  --> "FATAL: Error opening wordlist file: /usr/share/wordlists/dirb/common.txt"
```

### Impact

- dirb was completely unusable
- Had to fall back to feroxbuster with seclists (which did work)
- gobuster also failed due to conflicting flag issues (see below)

### What's Needed

1. **Install standard Kali wordlists:** `apt install wordlists seclists dirb`
2. **Verify wordlist paths** on container build

---

## 6. Kali Container — Gobuster Flag Conflicts

### Problem

Gobuster rejected valid flag combinations with confusing error messages.

### What Happened

```bash
# Attempt 1:
gobuster dir -u https://... -w /usr/share/wordlists/dirb/common.txt -s 200,301,302,403
  --> "status-codes and status-codes-blacklist are both set - please set only one.
       status-codes-blacklist is set by default"

# Attempt 2 (tried to clear the blacklist):
gobuster dir -u https://... -w ... --status-codes-blacklist ""
  --> "status-codes and status-codes-blacklist are both not set, please set one"
```

### Impact

- Gobuster was completely unusable — both setting and not setting the flags failed
- There is no valid invocation that works with this version

### What's Needed

1. **Test gobuster version** in the Kali container and document working flag combinations
2. Consider **pinning gobuster** to a known-working version, or document the correct usage

---

## 7. Kali Container — `host` Command Not Allowlisted

### Problem

The `host` DNS lookup tool is not in the Kali container's allowlist.

### What Happened

```
run_kali_tool(tool="host", args="coiffure-grimm.ch")
  --> "Tool 'host' is not in the allowlist"
  --> Provided the full allowlist of 57 tools
```

### Impact

- Minor — `dig` was available as an alternative
- But `host` is a standard DNS tool that should be available

### What's Needed

- Add `host` to the Kali tool allowlist (it's a basic DNS utility)

---

## 8. Kali Container — Tool Timeouts

### Problem

Several tools timed out even with generous timeout settings, likely due to WAF blocking but also possibly due to container resource constraints.

### What Happened

```
nmap -sV -sC -O -A -T4 --top-ports 1000 149.126.4.73
  --> "Command timed out after 300s" (5 minutes!)

wpscan --url https://www.coiffure-grimm.ch/ --enumerate vp,vt,u,dbe --plugins-detection aggressive
  --> "Command timed out after 300s"

fierce --domain coiffure-grimm.ch
  --> "Command timed out after 120s"

dalfox url "https://www.coiffure-grimm.ch/?s=test"
  --> "Command timed out after 120s"

sqlmap -u "https://www.coiffure-grimm.ch/?s=test" --batch
  --> "Command timed out after 180s"

nmap --script=mysql-info,mysql-enum,mysql-empty-password,mysql-brute,mysql-databases -p 3306
  --> "Command timed out after 120s"
```

### Impact

- Full nmap scan never completed (had to use targeted port-specific scans)
- WPScan never returned results (aggressive plugin detection)
- SQLMap and DalFox never completed (couldn't test for SQLi/XSS)
- MySQL NSE scripts never completed (couldn't enumerate the exposed database)

### What's Needed

1. **Allow configurable timeouts** beyond 300s for long-running scans
2. **Support background/async execution** with result polling
3. Consider running tools with `--max-retries` or `--rate` flags pre-configured to avoid WAF-triggered blocks
4. **Add a warning** when a tool is approaching timeout so the caller can adjust

---

## 9. Local Container — No DNS Resolution for External Hosts

### Problem

The Claude Code container itself cannot resolve external domain names, causing all direct curl/bash commands to external targets to fail.

### What Happened

```bash
# From Bash tool (local container):
curl -sk https://www.coiffure-grimm.ch/wp-cron.php
  --> exit code 6 (Could not resolve host)

curl -sk https://www.coiffure-grimm.ch/?rest_route=/wp/v2/users
  --> exit code 6
```

### Impact

- When Kali pipe commands failed, couldn't fall back to local container for web requests
- Had to route ALL external web requests through `mcp__kali__run_kali_tool(tool="curl", ...)`
- Caused cascading "Sibling tool call errored" failures when one of several parallel Bash calls failed

### What's Needed

1. **Configure DNS resolution** in the Claude Code container (add nameserver to `/etc/resolv.conf` or configure Docker DNS)
2. Alternatively, **document** that external network access is only available through the Kali MCP container

---

## 10. Local Container — No python3 Available

### Problem

Python 3 is not installed in the Claude Code container.

### What Happened

```bash
curl -s http://hexstrike:8888/health | python3 -c "import sys,json; ..."
  --> "/bin/bash: line 1: python3: command not found"
```

### Impact

- Could not use Python for JSON parsing of API responses
- Had to use jq or grep as alternatives (jq was also not available initially)

### What's Needed

- Install `python3` and `jq` in the Claude Code container for basic data processing

---

## 11. Wireshark — No Traffic Captured

### Problem

Wireshark packet capture returned 0 packets despite active network communication.

### What Happened

```
mcp__wireshark__capture_packets(
  interface="any", count=50, filter="host 149.126.4.73", duration=15
)
  --> "0 packets captured"
  --> Duration: 0.000 secs
```

### Impact

- No traffic evidence captured for the report
- Could not analyze exploitation traffic
- Could not extract credentials from network captures

### What's Needed

1. **Verify that the Wireshark container has network visibility** to the Kali container's traffic
2. The containers may be on separate Docker networks, preventing packet capture
3. Consider using a **shared network namespace** or a tap/mirror interface
4. Alternatively, **capture traffic from within the Kali container** and send the pcap to Wireshark for analysis

---

## 12. Screenshot MCP — Files Not Accessible from Claude Code Container

### Problem

Screenshots are saved on the Screenshot MCP container's filesystem, but Claude Code cannot read them directly.

### What Happened

```
Read(file_path="/tmp/screenshots/coiffure-grimm.ch_screenshot_20260303-193006.png")
  --> "File does not exist. Note: your current working directory is /root."
```

### Impact

- Cannot view or verify screenshot content from within the conversation
- Screenshots are referenced in the report but their content cannot be validated
- The base64 data IS returned in the MCP response, but it's very large (280KB+ encoded)

### What's Needed

1. **Mount a shared volume** between the screenshot container and Claude Code container, or
2. **Provide a dedicated MCP tool** to retrieve screenshots by path (e.g., `get_screenshot`), or
3. The current base64 return works but is very token-heavy; consider a **thumbnail option**

---

## 13. Sibling Tool Call Error Cascade

### Problem

When multiple tools are called in parallel and **ONE** fails, all "sibling" calls also fail with `"Sibling tool call errored"`.

### What Happened

This occurred multiple times:
- **Batch 1:** Read of screenshot file failed (file on different container) → all 7 parallel Kali/Screenshot calls failed
- **Batch 2:** First Bash curl failed (DNS resolution) → all 7 parallel Bash/Screenshot/WebSearch calls failed

### Impact

- Parallel execution (a core efficiency feature) becomes fragile
- One non-critical failure kills all parallel work
- Had to retry all calls, wasting time and tokens

### What's Needed

1. **Isolate parallel tool failures** — a failed tool should not cascade to siblings
2. Each tool in a parallel batch should execute and return independently
3. **This is the single biggest efficiency issue** encountered during the engagement

---

## 14. Kali httpx — Wrong Binary Version

### Problem

The `httpx` in the Kali container is the **Python HTTP client** (httpx PyPI package), not the **ProjectDiscovery httpx** security tool.

### What Happened

```
httpx -u https://coiffure-grimm.ch -sc -title -tech-detect
  --> "Usage: httpx [OPTIONS] URL"
  --> "Error: No such option: -u"
```

### Impact

- Could not use httpx for technology detection, status codes, CDN detection
- The `-u` flag and security-specific flags are from ProjectDiscovery's httpx, not the Python HTTP client
- WhatWeb was used as a fallback but returned 403 (WAF blocked it)

### What's Needed

1. **Install ProjectDiscovery's httpx** alongside or instead of the Python httpx package
2. Alternatively, alias or rename to avoid confusion (e.g., `pd-httpx` vs `httpx`)

---

## 15. WPScan — No API Token Configured

### Problem

WPScan was called but timed out. Even if it had completed, it likely would have returned limited results without a WPScan API token for vulnerability database lookups.

### What Happened

```
wpscan --url https://www.coiffure-grimm.ch/ --enumerate vp,vt,u,dbe
  --plugins-detection aggressive --random-user-agent --force
  --> "Command timed out after 300s"
```

### What's Needed

1. **Configure a WPScan API token** via environment variable (`WPSCAN_API_TOKEN`)
2. **Pre-configure WPScan** with `--api-token` in the Kali container
3. The timeout may also be caused by the WAF blocking WPScan's fingerprinting requests

---

## 16. theharvester — Deprecated Command Name

### Problem

The `theharvester` command is deprecated in favor of `theHarvester` (case-sensitive).

### What Happened

```
theharvester -d coiffure-grimm.ch -b all -l 200
  --> "The command theharvester is deprecated. Please use theHarvester instead."
  --> No actual results returned
```

### What's Needed

1. **Update the Kali allowlist** to use `theHarvester` (capital H)
2. Or create a **symlink/alias** from `theharvester` to `theHarvester`

---

## Summary Table

| # | Component | Issue | Severity | Status |
|---|-----------|-------|----------|--------|
| 1 | HexStrike | No MCP integration, no API docs, undiscoverable endpoints | CRITICAL | Not usable |
| 2 | Metasploit | RPC authentication failure on all calls | CRITICAL | Not usable |
| 3 | Ollama Pipeline | OOM — model needs 41.5GB, only 12.4GB available | CRITICAL | Not usable |
| 4 | Kali Container | Pipe operators not supported in tool args | HIGH | Workaround exists |
| 5 | Kali Container | Missing wordlists (`/usr/share/wordlists/dirb/`) | HIGH | Breaks dirb |
| 6 | Kali Container | Gobuster flag conflicts (unusable) | MEDIUM | Breaks gobuster |
| 7 | Kali Container | `host` command not in allowlist | LOW | Use dig instead |
| 8 | Kali Container | Tool timeouts (nmap, wpscan, sqlmap, dalfox) | HIGH | Partial results only |
| 9 | Local Container | No DNS resolution for external hosts | HIGH | Must use Kali curl |
| 10 | Local Container | No python3 installed | MEDIUM | Use jq/grep instead |
| 11 | Wireshark | 0 packets captured (network isolation) | HIGH | Not usable |
| 12 | Screenshot | Files not readable from Claude Code container | MEDIUM | Base64 workaround |
| 13 | Claude Code | Sibling tool call error cascade | HIGH | Retry required |
| 14 | Kali Container | Wrong httpx binary (Python vs ProjectDiscovery) | MEDIUM | Use whatweb instead |
| 15 | Kali Container | WPScan no API token configured | MEDIUM | Limited results |
| 16 | Kali Container | theharvester deprecated command name | LOW | Easy fix |

## Priority Breakdown

- **3 CRITICAL** (tools completely unusable): HexStrike, Metasploit, Ollama
- **5 HIGH** (significant functionality loss): Pipe support, wordlists, timeouts, DNS, error cascade
- **5 MEDIUM** (workarounds exist): Gobuster, python3, screenshots, httpx, WPScan
- **3 LOW** (minor): host allowlist, theharvester naming

---

## Toolchain Availability Summary

Of the 6 MCP tool servers available (Kali, Metasploit, Wireshark, Screenshot, Ollama Pipeline, HexStrike), only **2 were fully functional** (Kali, Screenshot). Metasploit, Ollama, and Wireshark were non-functional. HexStrike was undiscoverable. This means **67% of the toolchain was degraded or broken** during the engagement.
