"""Kali Linux MCP Server for blhackbox.

Adapted from community Kali MCP servers (k3nn3dy-ai/kali-mcp,
DurkDiggler/Kali-MCP-Server).  Provides MCP tool access to Kali
Linux security tools running inside a Docker container.

Includes integrated Metasploit tools via msfconsole CLI (no msfrpcd
dependency).  Metasploit tools use `msfconsole -qx` for one-shot
command execution and `msfvenom` for payload generation.

Each tool call returns structured output:
  { stdout, stderr, exit_code, tool_name, timestamp, target }
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import shlex
import shutil
from datetime import UTC, datetime
from typing import Any

from mcp.server.fastmcp import FastMCP

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("kali-mcp")

# Full Kali Linux tool allowlist — expanded to cover the complete security
# toolchain available in a kali-rolling container.
#
# Categories (70+ tools):
#   Network/Recon: nmap, rustscan, masscan, netdiscover, arp-scan, traceroute, hping3
#   DNS:           subfinder, amass, fierce, dnsenum, dnsrecon, dig, whois,
#                  theharvester, theHarvester, host
#   Web:           nikto, gobuster, dirb, dirsearch, ffuf, feroxbuster, whatweb, wafw00f,
#                  wpscan, httpx, katana, arjun, paramspider, dalfox
#   Exploitation:  sqlmap, hydra, medusa, john, hashcat, crackmapexec, evil-winrm,
#                  smbclient, enum4linux-ng, responder, netexec,
#                  msfconsole, msfvenom, msfdb
#   Wireless:      aircrack-ng, airodump-ng, aireplay-ng, wifite, bettercap
#   Forensics:     binwalk, foremost, exiftool, steghide, strings, hashid
#   Shell/System:  echo, cat, ls, whoami, id, ps, grep, awk, sed, head, tail,
#                  wc, sort, uniq, find, mkdir, cp, mv, chmod, touch, tee, cut,
#                  env, date, uname, hostname, python3, pip
#   Utilities:     curl, wget, netcat, socat, sshpass, proxychains4, bash
ALLOWED_TOOLS = set(
    t.strip()
    for t in os.environ.get(
        "ALLOWED_TOOLS",
        # --- Network / Recon ---
        "nmap,rustscan,masscan,netdiscover,arp-scan,traceroute,hping3,"
        # --- DNS ---
        "subfinder,amass,fierce,dnsenum,dnsrecon,dig,whois,"
        "theharvester,theHarvester,host,"
        # --- Web Application ---
        "nikto,gobuster,dirb,dirsearch,ffuf,feroxbuster,whatweb,wafw00f,"
        "wpscan,httpx,httpx-toolkit,katana,arjun,paramspider,dalfox,"
        # --- Exploitation / Brute-force ---
        "sqlmap,hydra,medusa,john,hashcat,crackmapexec,evil-winrm,"
        "smbclient,enum4linux-ng,responder,netexec,"
        # --- Metasploit Framework ---
        "msfconsole,msfvenom,msfdb,"
        # --- Wireless ---
        "aircrack-ng,airodump-ng,aireplay-ng,wifite,bettercap,"
        # --- Forensics / Binary ---
        "binwalk,foremost,exiftool,steghide,strings,hashid,"
        # --- Shell builtins & common system utilities ---
        "echo,cat,ls,whoami,id,ps,grep,awk,sed,head,tail,wc,"
        "sort,uniq,find,mkdir,cp,mv,chmod,touch,tee,cut,"
        "env,date,uname,hostname,python3,pip,"
        # --- Utilities ---
        "curl,wget,netcat,socat,sshpass,proxychains4,bash",
    ).split(",")
    if t.strip()
)

# Maximum timeout callers can request (seconds).  Default: 600s (10 min).
MAX_TIMEOUT = int(os.environ.get("KALI_MAX_TIMEOUT", "600"))

# Metasploit console timeout — msfconsole cold-starts in 10-30s,
# so commands need a generous timeout.
MSF_TIMEOUT = int(os.environ.get("MSF_TIMEOUT", "300"))

MCP_PORT = int(os.environ.get("MCP_PORT", "9001"))

mcp = FastMCP("kali-mcp", host="0.0.0.0", port=MCP_PORT)


# ---------------------------------------------------------------------------
# Helper: run a subprocess and return structured result
# ---------------------------------------------------------------------------

async def _run_command(
    cmd: list[str],
    *,
    tool_name: str,
    target: str = "unknown",
    timeout: int = 300,
    shell: bool = False,
    shell_cmd: str = "",
) -> dict[str, Any]:
    """Execute a command and return structured result dict."""
    timestamp = datetime.now(UTC).isoformat()
    timeout = min(timeout, MAX_TIMEOUT)

    try:
        if shell:
            proc = await asyncio.create_subprocess_exec(
                "bash", "-c", shell_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
        else:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
        stdout_bytes, stderr_bytes = await asyncio.wait_for(
            proc.communicate(), timeout=timeout
        )
        stdout = stdout_bytes.decode("utf-8", errors="replace")
        stderr = stderr_bytes.decode("utf-8", errors="replace")
        exit_code = proc.returncode or 0
    except TimeoutError:
        return {
            "stdout": "",
            "stderr": f"Command timed out after {timeout}s. Max allowed: {MAX_TIMEOUT}s.",
            "exit_code": -1,
            "tool_name": tool_name,
            "timestamp": timestamp,
            "target": target,
        }
    except Exception as exc:
        return {
            "stdout": "",
            "stderr": str(exc),
            "exit_code": -1,
            "tool_name": tool_name,
            "timestamp": timestamp,
            "target": target,
        }

    return {
        "stdout": stdout,
        "stderr": stderr,
        "exit_code": exit_code,
        "tool_name": tool_name,
        "timestamp": timestamp,
        "target": target,
    }


# ---------------------------------------------------------------------------
# MCP Tools — Generic Kali tool execution
# ---------------------------------------------------------------------------

@mcp.tool()
async def run_kali_tool(
    tool: str,
    args: str,
    target: str = "unknown",
    timeout: int = 300,
) -> str:
    """Execute a Kali Linux security tool. Returns structured JSON with
    stdout, stderr, exit_code, tool_name, timestamp, and target.

    For commands that require shell features (pipes, redirects, etc.),
    use tool='bash' with args='-c "your full command here"'.
    """
    tool_name = tool.strip()
    timestamp = datetime.now(UTC).isoformat()

    # Clamp timeout to configured maximum
    timeout = min(timeout, MAX_TIMEOUT)

    # Validate tool against allowlist
    if tool_name not in ALLOWED_TOOLS:
        return json.dumps({
            "error": f"Tool '{tool_name}' is not in the allowlist",
            "allowed": sorted(ALLOWED_TOOLS),
            "hint": (
                "For shell commands with pipes, use tool='bash' with "
                "args='-c \"command1 | command2\"'"
            ),
        })

    # Verify tool is installed
    if not shutil.which(tool_name):
        return json.dumps({
            "error": f"Tool '{tool_name}' is not installed in this container",
        })

    # Build command — use shlex.split to prevent shell injection
    try:
        cmd_parts = [tool_name] + shlex.split(args)
    except ValueError as exc:
        return json.dumps({
            "error": f"Invalid arguments (failed to parse): {exc}",
            "tool_name": tool_name,
        })

    logger.info("Executing: %s (timeout: %ds)", cmd_parts, timeout)

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd_parts,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout_bytes, stderr_bytes = await asyncio.wait_for(
            proc.communicate(), timeout=timeout
        )
        stdout = stdout_bytes.decode("utf-8", errors="replace")
        stderr = stderr_bytes.decode("utf-8", errors="replace")
        exit_code = proc.returncode or 0
    except TimeoutError:
        return json.dumps({
            "stdout": "",
            "stderr": f"Command timed out after {timeout}s. Max allowed: {MAX_TIMEOUT}s.",
            "exit_code": -1,
            "tool_name": tool_name,
            "timestamp": timestamp,
            "target": target,
        })
    except Exception as exc:
        return json.dumps({
            "stdout": "",
            "stderr": str(exc),
            "exit_code": -1,
            "tool_name": tool_name,
            "timestamp": timestamp,
            "target": target,
        })

    return json.dumps({
        "stdout": stdout,
        "stderr": stderr,
        "exit_code": exit_code,
        "tool_name": tool_name,
        "timestamp": timestamp,
        "target": target,
    })


@mcp.tool()
async def run_shell_command(
    command: str,
    target: str = "unknown",
    timeout: int = 300,
) -> str:
    """Execute a shell command with full pipe and redirect support.

    This wraps the command in 'bash -c' so shell features like pipes (|),
    redirects (>), subshells ($(...)), and command chaining (&&, ||) all work.

    Only tools from the allowlist may appear in the command. The first
    token of each piped segment is validated against the allowlist.

    NOTE: The allowlist is a UX convenience guide, NOT a security boundary.
    Since 'bash' is in the allowlist, any command can be run via
    ``bash -c "arbitrary command"``.  This is intentional — the allowlist
    helps AI agents discover and prefer the correct tool names, while
    ``bash -c`` provides an escape hatch for shell builtins (echo, cat,
    etc.) and complex pipelines.  Do not rely on this as an isolation
    mechanism.

    Args:
        command: Full shell command string (e.g. 'curl -sk https://... | grep pattern').
        target: Target identifier for logging/reporting.
        timeout: Execution timeout in seconds (default 300, max from KALI_MAX_TIMEOUT).
    """
    timestamp = datetime.now(UTC).isoformat()
    timeout = min(timeout, MAX_TIMEOUT)

    # UX validation: check that the primary command(s) are allowlisted
    # by extracting the first token of each pipe segment.
    # NOTE: This is advisory, not a security boundary — see docstring.
    segments = command.split("|")
    for segment in segments:
        segment = segment.strip()
        if not segment:
            continue
        # Handle command chaining (&&, ||, ;)
        for chain_op in ("&&", "||", ";"):
            segment = segment.split(chain_op)[0].strip()
        first_token = segment.split()[0] if segment.split() else ""
        if first_token and first_token not in ALLOWED_TOOLS:
            return json.dumps({
                "error": f"Command '{first_token}' is not in the allowlist",
                "allowed": sorted(ALLOWED_TOOLS),
            })

    logger.info("Executing shell: bash -c '%s' (timeout: %ds)", command, timeout)

    try:
        proc = await asyncio.create_subprocess_exec(
            "bash", "-c", command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout_bytes, stderr_bytes = await asyncio.wait_for(
            proc.communicate(), timeout=timeout
        )
        stdout = stdout_bytes.decode("utf-8", errors="replace")
        stderr = stderr_bytes.decode("utf-8", errors="replace")
        exit_code = proc.returncode or 0
    except TimeoutError:
        return json.dumps({
            "stdout": "",
            "stderr": f"Command timed out after {timeout}s. Max allowed: {MAX_TIMEOUT}s.",
            "exit_code": -1,
            "command": command,
            "timestamp": timestamp,
            "target": target,
        })
    except Exception as exc:
        return json.dumps({
            "stdout": "",
            "stderr": str(exc),
            "exit_code": -1,
            "command": command,
            "timestamp": timestamp,
            "target": target,
        })

    return json.dumps({
        "stdout": stdout,
        "stderr": stderr,
        "exit_code": exit_code,
        "command": command,
        "timestamp": timestamp,
        "target": target,
    })


@mcp.tool()
def list_available_tools() -> str:
    """List all available Kali Linux security tools in this container,
    including Metasploit Framework tools (msfconsole, msfvenom)."""
    tools = {}
    for tool_name in sorted(ALLOWED_TOOLS):
        path = shutil.which(tool_name)
        tools[tool_name] = {
            "installed": path is not None,
            "path": path or "not found",
        }
    return json.dumps({"tools": tools, "max_timeout": MAX_TIMEOUT}, indent=2)


# ---------------------------------------------------------------------------
# MCP Tools — Metasploit Framework (via msfconsole CLI)
# ---------------------------------------------------------------------------
# These tools replace the separate metasploit-mcp server.  Instead of
# requiring msfrpcd (RPC daemon + PostgreSQL + msgpack protocol), they
# use `msfconsole -qx "command"` for direct CLI execution.
#
# Trade-offs:
#   + No daemon dependency — works if msfconsole is installed
#   + Simpler architecture — one MCP server instead of two
#   + No msgpack/httpx/SSL complexity
#   - msfconsole cold-starts in ~10-30s (Ruby + DB init)
#   - Use resource files (.rc) for multi-step workflows
# ---------------------------------------------------------------------------


def _msf_installed() -> bool:
    """Check if msfconsole is available."""
    return shutil.which("msfconsole") is not None


def _msfvenom_installed() -> bool:
    """Check if msfvenom is available."""
    return shutil.which("msfvenom") is not None


def _not_installed_error(tool: str) -> str:
    """Return a structured error when Metasploit is not installed."""
    return json.dumps({
        "error": True,
        "tool": tool,
        "reason": "metasploit_not_installed",
        "message": (
            "Metasploit Framework is not installed. "
            "Install with: apt-get install -y metasploit-framework"
        ),
        "hint": (
            "In Docker, the kali-mcp container includes metasploit-framework. "
            "Run: docker compose up kali-mcp"
        ),
    })


def _parse_msf_table(output: str) -> list[dict[str, str]]:
    """Parse msfconsole tabular output into a list of dicts.

    Handles both the standard header-separated table format and
    the search results format used by `search`.
    """
    rows: list[dict[str, str]] = []
    lines = output.strip().splitlines()

    # Find header line (contains column names separated by spaces)
    header_idx = -1
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("#") or stripped.startswith("Name"):
            header_idx = i
            break
        # Search results header: "  #  Name  ..."
        if re.match(r"\s*#\s+Name\s+", stripped):
            header_idx = i
            break

    if header_idx < 0:
        return rows

    # Parse header columns
    header = lines[header_idx]
    # Skip separator line (--- or ===)
    data_start = header_idx + 1
    if data_start < len(lines) and re.match(r"^[\s\-=]+$", lines[data_start]):
        data_start += 1

    # Extract column names from header
    cols = header.split()

    for line in lines[data_start:]:
        stripped = line.strip()
        if not stripped or re.match(r"^[\s\-=]+$", stripped):
            continue
        # Skip indented continuation lines (target sub-entries) that
        # msfconsole emits under multi-target modules.  These start with
        # whitespace + backslash (\_) or have significantly more leading
        # whitespace than a normal data row, and would corrupt the parse.
        if line.startswith("   ") and (
            stripped.startswith("\\_") or stripped.startswith("\\\\")
        ):
            continue
        parts = stripped.split(None, len(cols) - 1)
        # Sanity check: a valid row should have a numeric index in column 0
        # when the header starts with '#'.  Skip rows that don't match.
        if cols and cols[0] == "#" and parts:
            try:
                int(parts[0])
            except ValueError:
                continue
        row = {}
        for j, col in enumerate(cols):
            row[col.lower()] = parts[j] if j < len(parts) else ""
        rows.append(row)

    return rows


@mcp.tool()
async def msf_search(
    search: str,
    module_type: str = "",
    limit: int = 50,
) -> str:
    """Search Metasploit modules (exploits, auxiliary, post, payloads, etc.).

    Uses 'msfconsole -qx "search ..."' to find modules matching the query.
    First invocation may take 10-30s due to msfconsole cold start.

    Args:
        search: Search term (e.g. 'apache', 'CVE-2021', 'smb', 'eternalblue').
        module_type: Optional filter: 'exploit', 'auxiliary', 'post', 'payload', 'encoder'.
        limit: Maximum number of results to return (default 50).
    """
    if not _msf_installed():
        return _not_installed_error("msf_search")

    query = search
    if module_type:
        query = f"type:{module_type} {search}"

    cmd = f'msfconsole -qx "search {query}; exit"'
    logger.info("Metasploit search: %s", cmd)

    result = await _run_command(
        [], shell=True, shell_cmd=cmd,
        tool_name="msf_search", timeout=MSF_TIMEOUT,
    )

    # Parse search results into structured data
    modules = _parse_msf_table(result.get("stdout", ""))
    if limit and len(modules) > limit:
        modules = modules[:limit]

    return json.dumps({
        "tool": "msf_search",
        "query": search,
        "module_type": module_type or "all",
        "modules": modules,
        "count": len(modules),
        "raw_output": result.get("stdout", "")[:2000] if not modules else "",
        "exit_code": result.get("exit_code", -1),
    }, indent=2)


@mcp.tool()
async def msf_module_info(
    module_name: str,
) -> str:
    """Get detailed information about a Metasploit module.

    Returns module description, options (required/optional), targets,
    references (CVEs), and authors.

    Args:
        module_name: Full module path (e.g. 'exploit/multi/http/apache_mod_cgi_bash_env_exec').
    """
    if not _msf_installed():
        return _not_installed_error("msf_module_info")

    # Use 'info' command and 'show options' for full details
    cmd = f'msfconsole -qx "use {module_name}; info; show options; exit"'
    logger.info("Metasploit module info: %s", cmd)

    result = await _run_command(
        [], shell=True, shell_cmd=cmd,
        tool_name="msf_module_info", timeout=MSF_TIMEOUT,
    )

    return json.dumps({
        "tool": "msf_module_info",
        "module": module_name,
        "output": result.get("stdout", ""),
        "exit_code": result.get("exit_code", -1),
    }, indent=2)


@mcp.tool()
async def msf_run_module(
    module_name: str,
    options: dict[str, str],
    payload: str = "",
    action: str = "run",
    target: str = "unknown",
    timeout: int = 300,
) -> str:
    """Execute a Metasploit module (exploit, auxiliary, or post).

    Builds and runs an msfconsole resource script with the specified
    module, options, and payload.  Supports exploit, auxiliary, and
    post modules.

    Args:
        module_name: Full module path (e.g. 'exploit/multi/handler', 'auxiliary/scanner/smb/smb_version').
        options: Dict of module options (e.g. {"RHOSTS": "10.0.0.1", "RPORT": "443"}).
        payload: Optional payload module (e.g. 'windows/meterpreter/reverse_tcp').
        action: 'run', 'check', or 'exploit' (default 'run').
        target: Target identifier for logging.
        timeout: Execution timeout in seconds (default 300).
    """
    if not _msf_installed():
        return _not_installed_error("msf_run_module")

    # Build msfconsole command string
    parts = [f"use {module_name}"]
    if payload:
        parts.append(f"set PAYLOAD {payload}")
    for key, value in options.items():
        parts.append(f"set {key} {value}")
    parts.append(action)
    parts.append("exit")

    msf_cmd = "; ".join(parts)
    cmd = f'msfconsole -qx "{msf_cmd}"'
    logger.info("Metasploit run: %s (target: %s)", cmd, target)

    result = await _run_command(
        [], shell=True, shell_cmd=cmd,
        tool_name="msf_run_module", target=target, timeout=timeout,
    )

    return json.dumps({
        "tool": "msf_run_module",
        "module": module_name,
        "payload": payload,
        "options": options,
        "action": action,
        "output": result.get("stdout", ""),
        "stderr": result.get("stderr", ""),
        "exit_code": result.get("exit_code", -1),
        "target": target,
    }, indent=2)


@mcp.tool()
async def msf_payload_generate(
    payload: str,
    options: dict[str, str],
    format: str = "raw",
    output_file: str = "",
) -> str:
    """Generate a payload using msfvenom.

    Equivalent to running msfvenom on the command line.  Supports all
    output formats (raw, exe, elf, python, ruby, c, etc.).

    Args:
        payload: Payload module (e.g. 'windows/meterpreter/reverse_tcp', 'linux/x64/shell_reverse_tcp').
        options: Payload options (e.g. {"LHOST": "10.0.0.1", "LPORT": "4444"}).
        format: Output format (raw, exe, elf, python, ruby, c, etc.).
        output_file: Optional output file path. If empty, payload bytes are discarded and only metadata is returned.
    """
    if not _msfvenom_installed():
        return _not_installed_error("msf_payload_generate")

    # Build msfvenom command
    cmd_parts = ["msfvenom", "-p", payload, "-f", format]
    for key, value in options.items():
        cmd_parts.append(f"{key}={value}")
    if output_file:
        cmd_parts.extend(["-o", output_file])

    logger.info("msfvenom: %s", cmd_parts)

    result = await _run_command(
        cmd_parts,
        tool_name="msf_payload_generate",
        timeout=MSF_TIMEOUT,
    )

    output_info: dict[str, Any] = {
        "tool": "msf_payload_generate",
        "payload": payload,
        "format": format,
        "options": options,
        "exit_code": result.get("exit_code", -1),
        "stderr": result.get("stderr", ""),
    }

    if output_file:
        output_info["output_file"] = output_file
        output_info["status"] = "generated" if result.get("exit_code") == 0 else "failed"
    else:
        stdout = result.get("stdout", "")
        output_info["size_bytes"] = len(stdout.encode("utf-8", errors="replace"))
        output_info["status"] = "generated" if result.get("exit_code") == 0 else "failed"

    return json.dumps(output_info, indent=2)


@mcp.tool()
async def msf_console_execute(
    command: str,
    timeout: int = 120,
) -> str:
    """Execute a raw msfconsole command and return the output.

    This is a general-purpose escape hatch for any Metasploit
    functionality not covered by the dedicated msf_* tools.
    Useful for: db_nmap, sessions -l, jobs, route, etc.

    First invocation may take 10-30s due to msfconsole cold start.

    Args:
        command: The msfconsole command to execute (e.g. 'db_nmap -sV 10.0.0.1', 'sessions -l').
        timeout: Seconds to wait for output (default 120).
    """
    if not _msf_installed():
        return _not_installed_error("msf_console_execute")

    cmd = f'msfconsole -qx "{command}; exit"'
    logger.info("Metasploit console: %s", cmd)

    result = await _run_command(
        [], shell=True, shell_cmd=cmd,
        tool_name="msf_console_execute", timeout=timeout,
    )

    return json.dumps({
        "tool": "msf_console_execute",
        "command": command,
        "output": result.get("stdout", ""),
        "stderr": result.get("stderr", ""),
        "exit_code": result.get("exit_code", -1),
    }, indent=2)


@mcp.tool()
async def msf_status() -> str:
    """Check Metasploit Framework installation status.

    Reports whether msfconsole and msfvenom are installed,
    the Metasploit version, and database connectivity status.
    Use this tool FIRST to diagnose Metasploit issues.
    """
    status: dict[str, Any] = {
        "tool": "msf_status",
        "msfconsole_installed": _msf_installed(),
        "msfconsole_path": shutil.which("msfconsole") or "not found",
        "msfvenom_installed": _msfvenom_installed(),
        "msfvenom_path": shutil.which("msfvenom") or "not found",
    }

    if not _msf_installed():
        status["status"] = "not_installed"
        status["message"] = (
            "Metasploit Framework is not installed. "
            "Install with: apt-get install -y metasploit-framework"
        )
        return json.dumps(status, indent=2)

    # Get version
    try:
        proc = await asyncio.create_subprocess_exec(
            "msfconsole", "--version",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=15)
        status["version"] = stdout.decode("utf-8", errors="replace").strip()
    except Exception:
        status["version"] = "unknown"

    # Check database status
    try:
        proc = await asyncio.create_subprocess_exec(
            "msfconsole", "-qx", "db_status; exit",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=60)
        db_output = stdout.decode("utf-8", errors="replace").strip()
        status["database"] = db_output
        status["database_connected"] = "connected" in db_output.lower()
    except Exception as exc:
        status["database"] = f"check failed: {exc}"
        status["database_connected"] = False

    status["status"] = "ready"
    return json.dumps(status, indent=2)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    transport = os.environ.get("MCP_TRANSPORT", "sse")
    logger.info(
        "Starting Kali Linux MCP Server (%s on port %d, allowed tools: %d, msf: %s)",
        transport, MCP_PORT, len(ALLOWED_TOOLS),
        "installed" if _msf_installed() else "not installed",
    )
    mcp.run(transport=transport)
