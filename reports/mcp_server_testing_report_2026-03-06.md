# MCP Server Tool Testing Report

**Date:** 2026-03-06
**Environment:** Kali Linux 6.18.5+kali-amd64, running as root

---

## 1. MCP Server: kali (9 tools)

### 1.1 list_available_tools

| Field  | Value |
|--------|-------|
| Status | PASS |
| Issues | None |
| Notes  | Returns 63 tools, all installed. Response is well-structured JSON. |

### 1.2 msf_status

| Field  | Value |
|--------|-------|
| Status | PASS |
| Issues | None |
| Notes  | Metasploit 6.4.112-dev, msfconsole/msfvenom installed, PostgreSQL DB connected. |

### 1.3 run_shell_command

| Field      | Value |
|------------|-------|
| Status     | PASS (with caveat) |
| Issues     | WARNING: Allowlist blocks basic shell commands. `echo` is not in the allowlist. Must wrap everything in `bash -c "..."` even for trivial commands. |
| Notes      | The tool description says "full pipe and redirect support" and notes state the allowlist is "a UX convenience guide, NOT a security boundary" -- but the behavior contradicts this since non-allowlisted first tokens are actively blocked. The user must always use `bash -c "..."` wrapper for shell builtins. This is a UX friction issue that the description acknowledges but could confuse automated agents. |
| Workaround | Use `bash -c "command"` for everything. |

### 1.4 run_kali_tool

| Field      | Value |
|------------|-------|
| Status     | PASS (with caveat) |
| Issues     | WARNING: Same allowlist restriction. Common system utilities like `whoami`, `id`, `cat`, `ls`, `ps` are not in the allowlist. Must use `tool=bash`, `args=-c "command"`. |
| Notes      | Works correctly when using bash as the tool wrapper. The hint in the error message is helpful. |
| Workaround | Use `tool="bash"` with `args='-c "desired_command"'`. |

### 1.5 msf_search

| Field   | Value |
|---------|-------|
| Status  | PASS (with parsing issue) |
| Issues  | BUG: Module result parsing is incorrect. The search for "eternalblue" returns 3 results, but entries #1 and #2 are malformed -- they show `\_` as the name and have garbled field mapping (e.g., "date": "Automatic", "rank": "Yes", "check": "MS17-010" -- these fields are misaligned). The parser is incorrectly splitting multi-line module entries (target sub-entries) as separate module results. |
| Details | The raw msfconsole output includes indented target lines under modules. The parser treats each line as a separate module entry, producing corrupted records with fields shifted into wrong columns. |

### 1.6 msf_module_info

| Field  | Value |
|--------|-------|
| Status | PASS |
| Issues | None |
| Notes  | Returns comprehensive module info including options, targets, references, and descriptions. Output is raw text embedded in JSON (not further structured), which is acceptable. |

### 1.7 msf_payload_generate

| Field  | Value |
|--------|-------|
| Status | PASS (with warning) |
| Issues | WARNING: No output_file specified = payload bytes discarded. When output_file is empty, only metadata is returned and payload content is lost. The stderr shows `[-] No platform was selected` and `[-] No arch selected` warnings -- these are msfvenom informational messages, not errors. |
| Notes  | Generated 74-byte payload successfully. Format and size metadata returned correctly. |

### 1.8 msf_run_module

| Field  | Value |
|--------|-------|
| Status | PASS |
| Issues | None |
| Notes  | Successfully ran auxiliary/scanner/portscan/tcp against localhost. Output, exit_code, and target all returned correctly. |

### 1.9 msf_console_execute

| Field  | Value |
|--------|-------|
| Status | PASS |
| Issues | None |
| Notes  | Returned Metasploit version correctly. Clean output, no errors. |

---

## 2. MCP Server: ollama-pipeline (1 tool)

### 2.1 process_scan_results

| Field            | Value |
|------------------|-------|
| Status           | PARTIAL PASS |
| Issues           | WARNING/BUG: SynthesisAgent failed. The metadata contains: `"warning": "SynthesisAgent failed: ; SynthesisAgent returned empty output"` |
| Details          | Ingestion stage: 200.34 seconds (slow but functional) |
|                  | Processing stage: 209.36 seconds (slow but functional) |
|                  | Synthesis stage: 1083.01 seconds (~18 minutes!) and FAILED with empty output |
|                  | Total duration: 1492.74 seconds (~25 minutes) for a trivial nmap scan |
| Performance Issue | The pipeline is extremely slow. 25 minutes to process a 258-byte nmap output is operationally problematic. |
| Functional Issue | The SynthesisAgent failure means executive_summary fields (headline, summary) are empty. The risk_level defaults to "info" and remediation array is empty. The pipeline partially works (ingestion and processing extracted hosts/services correctly) but the final synthesis stage fails silently. |
| Notes            | The error message `"SynthesisAgent failed: "` has an empty reason after the colon, suggesting the error wasn't properly captured or propagated. The Ollama model used is llama3.1:8b. |

---

## 3. MCP Server: screenshot (4 tools)

### 3.1 take_screenshot

| Field  | Value |
|--------|-------|
| Status | PASS |
| Issues | None |
| Notes  | Successfully captured https://example.com. Returns path, dimensions, file size, timestamp, and base64-encoded PNG. When targeting unreachable URLs (http://localhost), returns a clear error: `net::ERR_CONNECTION_REFUSED`. Error handling is correct. |

### 3.2 take_element_screenshot

| Field  | Value |
|--------|-------|
| Status | PASS |
| Issues | None |
| Notes  | Successfully captured the h1 element from example.com. Returns bounding box coordinates and base64 PNG. |

### 3.3 annotate_screenshot

| Field  | Value |
|--------|-------|
| Status | PASS |
| Issues | None |
| Notes  | Successfully applied 2 annotations (text + box) to existing screenshot. Output path auto-generated with `_annotated` suffix. |

### 3.4 list_screenshots

| Field  | Value |
|--------|-------|
| Status | PASS |
| Issues | None |
| Notes  | Returns empty array when no screenshots exist, returns list after screenshots are captured. |

---

## 4. MCP Server: wireshark (7 tools)

### 4.1 list_interfaces

| Field  | Value |
|--------|-------|
| Status | PASS |
| Issues | None |
| Notes  | Lists 15 interfaces including eth0, lo, any, and virtual interfaces. |

### 4.2 capture_packets

| Field  | Value |
|--------|-------|
| Status | PASS (with warning) |
| Issues | WARNING: stderr includes `Running as user "root" and group "root". This could be dangerous.` -- this is a tshark informational warning, not an actual error. |
| Notes  | Successfully captured 5 packets on loopback, saved to pcap file. IO statistics included. |

### 4.3 read_pcap

| Field  | Value |
|--------|-------|
| Status | PASS (with warning) |
| Issues | WARNING: `errors` field name is misleading since it only contains tshark's informational "running as root" warning. |
| Notes  | Successfully parsed pcap, shows packet details with proper formatting. |

### 4.4 get_statistics

| Field  | Value |
|--------|-------|
| Status | PASS |
| Issues | None |
| Notes  | Protocol hierarchy statistics returned correctly (eth -> ipv6/ip -> tcp). |

### 4.5 get_conversations

| Field  | Value |
|--------|-------|
| Status | PASS |
| Issues | None |
| Notes  | TCP conversations extracted correctly with frame counts, byte counts, and timing. |

### 4.6 extract_credentials

| Field  | Value |
|--------|-------|
| Status | PASS |
| Issues | None |
| Notes  | Correctly reports no credentials found in the test capture. |

### 4.7 follow_stream

| Field  | Value |
|--------|-------|
| Status | PASS |
| Issues | None |
| Notes  | Successfully followed TCP stream 0. Stream had no application data (only SYN/RST), which is correctly reflected. |

---

## Summary Table

| MCP Server      | Tool                   | Status       | Severity                                              |
|-----------------|------------------------|--------------|-------------------------------------------------------|
| kali            | list_available_tools   | PASS         | -                                                     |
| kali            | msf_status             | PASS         | -                                                     |
| kali            | run_shell_command      | PASS w/caveat| LOW - UX friction with allowlist                      |
| kali            | run_kali_tool          | PASS w/caveat| LOW - Same allowlist issue                            |
| kali            | msf_search             | PASS w/bug   | MEDIUM - Result parsing misaligns multi-line entries   |
| kali            | msf_module_info        | PASS         | -                                                     |
| kali            | msf_payload_generate   | PASS         | -                                                     |
| kali            | msf_run_module         | PASS         | -                                                     |
| kali            | msf_console_execute    | PASS         | -                                                     |
| ollama-pipeline | process_scan_results   | PARTIAL PASS | HIGH - SynthesisAgent fails; ~25min; empty error      |
| screenshot      | take_screenshot        | PASS         | -                                                     |
| screenshot      | take_element_screenshot| PASS         | -                                                     |
| screenshot      | annotate_screenshot    | PASS         | -                                                     |
| screenshot      | list_screenshots       | PASS         | -                                                     |
| wireshark       | list_interfaces        | PASS         | -                                                     |
| wireshark       | capture_packets        | PASS w/warn  | INFO - Root user warning in output                    |
| wireshark       | read_pcap              | PASS w/warn  | INFO - errors field contains non-error warnings       |
| wireshark       | get_statistics         | PASS         | -                                                     |
| wireshark       | get_conversations      | PASS         | -                                                     |
| wireshark       | extract_credentials    | PASS         | -                                                     |
| wireshark       | follow_stream          | PASS         | -                                                     |

---

## Issues Requiring Attention (Prioritized)

### HIGH Priority

1. **ollama-pipeline -> process_scan_results**: SynthesisAgent fails silently with empty error message. Takes ~25 minutes for trivial input. The executive_summary and remediation sections are empty due to this failure. The stage timing shows synthesis alone took 18 minutes before failing.

### MEDIUM Priority

2. **kali -> msf_search**: Result parser incorrectly handles multi-line msfconsole output. Target sub-entries (indented lines with `\_`) are parsed as separate modules, causing field misalignment (e.g., name: `\_`, rank: "Yes" in wrong columns).

### LOW Priority

3. **kali -> run_shell_command / run_kali_tool**: Allowlist actively blocks common shell commands (`echo`, `whoami`, `cat`, `ls`, etc.). While `bash -c` workaround exists and is documented, this creates unnecessary friction for AI agents. Consider adding common shell builtins to the allowlist or making the allowlist a soft suggestion rather than a hard block.

### INFO (Cosmetic)

4. **wireshark -> read_pcap**: The `errors` field name is misleading when it only contains tshark's informational "running as root" warning. Consider renaming to `warnings` or `stderr`, or filtering out known informational messages.

---

## Fixes Applied

All four issues above have been addressed in this commit:

1. **HIGH** - `base_agent_server.py`: Empty Ollama responses now raise HTTP 502 with descriptive error instead of silently returning `{}`. `ollama_mcp_server.py`: Error messages now capture exception type when string representation is empty; empty output warnings include timing and model info.

2. **MEDIUM** - `kali-mcp/server.py`: `_parse_msf_table()` now skips indented continuation lines (target sub-entries starting with `\_`) and validates that data rows have a numeric index in column 0 when the header starts with `#`.

3. **LOW** - `kali-mcp/server.py`: Added 27 common shell builtins and system utilities to `ALLOWED_TOOLS` (`echo`, `cat`, `ls`, `whoami`, `id`, `ps`, `grep`, `awk`, `sed`, `head`, `tail`, `wc`, `sort`, `uniq`, `find`, `mkdir`, `cp`, `mv`, `chmod`, `touch`, `tee`, `cut`, `env`, `date`, `uname`, `hostname`, `python3`, `pip`).

4. **INFO** - `wire-mcp/server.py`: Renamed misleading `errors` field to `stderr` in `read_pcap` response to accurately reflect the field's contents.
