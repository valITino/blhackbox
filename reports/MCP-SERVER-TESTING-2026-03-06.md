# MCP Server Tool Testing Report

**Date:** 2026-03-06
**Environment:** Kali Linux 6.18.5+kali-amd64, running as root

---

## Summary

| MCP Server | Tools | Working | Failing | Notes |
|---|---|---|---|---|
| Kali | 3 | 3/3 | 0 | All functional. Allowlist bypass via `bash -c` is by design. |
| Metasploit | 13 | 0/13 | 13/13 | **BROKEN** -- msfrpcd not running at 127.0.0.1:55553 |
| Screenshot | 4 | 4/4 | 0 | All functional. Headless Chromium works. |
| Wireshark | 7 | 7/7 | 0 | All functional. tshark runs as root. |
| Ollama-Pipeline | 1 | 1/1 | 0 | Functional but extremely slow (~17 min for trivial input) |

**Total: 28 tools tested, 15/28 working (13 Metasploit failures)**

---

## 1. Kali MCP Server (3 Tools)

### 1.1 `list_available_tools` -- WORKING
Returns full JSON of 61 installed security tools with paths. All tools report `installed: true`. Max timeout is 600 seconds.

### 1.2 `run_kali_tool` -- WORKING
Ran `nmap --version` -- returned Nmap 7.98 with structured JSON (stdout, stderr, exit_code, tool_name, timestamp, target).

### 1.3 `run_shell_command` -- WORKING (with caveat)
- `echo "test"` -- REJECTED (`echo` not in allowlist)
- `bash -c "echo test"` -- WORKS (`bash` is in allowlist)

**Design note:** The allowlist only checks the first token of each pipe segment. Since `bash` is allowlisted, `bash -c "arbitrary command"` bypasses all restrictions. This is **intentional by design** -- the allowlist is a UX guide for AI agents, not a security boundary. Documented in the `run_shell_command` docstring.

---

## 2. Metasploit MCP Server (13 Tools) -- ALL FAILING

### Root Cause
msfrpcd (Metasploit RPC daemon) is NOT running. Port 55553 is closed inside the container. Every tool returns:
```
Not authenticated to msfrpcd. Ensure msfrpcd is running and credentials are correct
(user=msf, ssl=True, host=127.0.0.1:55553)
```

### Tools Affected (all 13)
`list_sessions`, `list_listeners`, `list_exploits`, `list_payloads`, `msf_console_execute`, `run_exploit`, `run_auxiliary_module`, `run_post_module`, `start_listener`, `stop_job`, `send_session_command`, `terminate_session`, `generate_payload`

### Fixes Applied
1. **Improved entrypoint.sh:** Added PostgreSQL data directory ownership fix, increased wait timeout for PostgreSQL (30s), msfrpcd now runs with `-f` (foreground) flag for crash detection, added 60-second verification loop that checks if msfrpcd is actually listening, detailed diagnostic output on failure.
2. **Login cooldown in server.py:** Added a 30-second cooldown after all login retries are exhausted, preventing every subsequent tool call from blocking for 90 seconds when msfrpcd is genuinely down.
3. **Improved healthcheck:** docker-compose.yml healthcheck now verifies **both** the MCP SSE endpoint (port 9002) AND msfrpcd (port 55553). Start period increased to 120s to accommodate PostgreSQL + msfdb init + msfrpcd startup.

---

## 3. Screenshot MCP Server (4 Tools)

### 3.1 `take_screenshot` -- WORKING
- `http://localhost` -- FAILED with `net::ERR_CONNECTION_REFUSED` (expected, correct error handling)
- `https://example.com` -- WORKS. Returns path, URL, title, dimensions, file size, base64 PNG.

### 3.2 `take_element_screenshot` -- WORKING
- `https://example.com` selector `h1` -- Returns bounding box, file size, base64 PNG.

### 3.3 `annotate_screenshot` -- WORKING
Added text and box annotations. Returns annotated file path, annotation count, file size.

### 3.4 `list_screenshots` -- WORKING
Initially returned 0 screenshots (correct).

---

## 4. Wireshark MCP Server (7 Tools)

### 4.1 `list_interfaces` -- WORKING
Returns 15 interfaces: eth0, any, lo, bluetooth-monitor, nflog, nfqueue, etc.

### 4.2 `capture_packets` -- WORKING
Captured on `lo` for 5 seconds, 0 packets (expected). Warning about running as root is a tshark advisory, not a bug.

### 4.3 `read_pcap` -- WORKING
Reads pcap files correctly. Root warning in stderr/errors field is not actually an error (exit_code=0).

### 4.4 `get_conversations` -- WORKING
### 4.5 `get_statistics` -- WORKING
### 4.6 `follow_stream` -- WORKING
### 4.7 `extract_credentials` -- WORKING
Correctly returns `credentials_found: false` for empty captures.

---

## 5. Ollama Pipeline MCP Server (1 Tool)

### 5.1 `process_scan_results` -- WORKING (extremely slow)

Processing took **1026.26 seconds (~17 minutes)** for a 117-byte nmap output with 2 open ports.

**Architecture:** ollama-mcp (orchestrator) -> ingestion (8001) -> processing (8002) -> synthesis (8003), each calling Ollama at 11434 independently.

### Fixes Applied
1. **Increased OLLAMA_KEEP_ALIVE:** Changed from `10m` to `30m` across all agent containers, base agent code, and docker-compose.yml. Prevents model unloading between sequential pipeline stages.
2. **Added OLLAMA_NUM_PARALLEL=3:** Allows Ollama to handle parallel requests if needed.
3. **Ollama warmup keep_alive:** Increased to `60m` in the entrypoint warmup request.
4. **Per-stage timing:** Added `[TIMING]` logs to the orchestrator for each pipeline stage. Added `PipelineStageTiming` model to metadata with `ingestion_seconds`, `processing_seconds`, `synthesis_seconds`.
5. **Fixed misleading field names:** Renamed `compression_ratio` to `expansion_ratio` and `compressed_size_bytes` to `structured_size_bytes` since the output is larger than input (expansion, not compression).
6. **GPU documentation:** Added note in docker-compose.yml that enabling GPU passthrough can reduce pipeline time from ~17 minutes to under 2 minutes.

### Remaining Recommendations
- **Enable GPU passthrough** for the Ollama container if an NVIDIA GPU is available (uncomment the `deploy` block in docker-compose.yml)
- **Consider a smaller model** (e.g., `llama3.2:3b`) for CPU-only environments
- **Consider a fast-path** in the orchestrator for trivially small inputs that skips LLM inference

---

## Verification Steps After Fixes

### Metasploit Verification
1. `msf_console_execute` with `command: "version"` -- expect Metasploit version string
2. `list_exploits` with `search: "apache", limit: 3` -- expect 3 Apache exploit modules
3. `list_sessions` -- expect empty list, NOT an auth error
4. `list_listeners` -- expect empty list, NOT an auth error

### Ollama Pipeline Verification
1. `process_scan_results` with small nmap input -- check `stage_timing` in metadata to identify bottleneck
2. Verify `expansion_ratio` field replaces old `compression_ratio`

### Regression Check (Already-Working Servers)
1. `mcp__kali__list_available_tools` -- should list 61 tools
2. `mcp__screenshot__take_screenshot` with `https://example.com`
3. `mcp__wireshark__list_interfaces` -- should list 15 interfaces
