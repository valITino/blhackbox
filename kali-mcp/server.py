"""Kali Linux MCP Server for blhackbox.

Adapted from community Kali MCP servers (k3nn3dy-ai/kali-mcp,
DurkDiggler/Kali-MCP-Server).  Provides MCP tool access to Kali
Linux security tools running inside a Docker container.

Each tool call returns structured output:
  { stdout, stderr, exit_code, tool_name, timestamp, target }
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import shlex
import shutil
from datetime import UTC, datetime

from mcp.server.fastmcp import FastMCP

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("kali-mcp")

# Full Kali Linux tool allowlist — expanded to cover the complete security
# toolchain available in a kali-rolling container.
#
# Categories (60 tools):
#   Network/Recon: nmap, rustscan, masscan, netdiscover, arp-scan, traceroute, hping3
#   DNS:           subfinder, amass, fierce, dnsenum, dnsrecon, dig, whois,
#                  theharvester, theHarvester, host
#   Web:           nikto, gobuster, dirb, dirsearch, ffuf, feroxbuster, whatweb, wafw00f,
#                  wpscan, httpx, katana, arjun, paramspider, dalfox
#   Exploitation:  sqlmap, hydra, medusa, john, hashcat, crackmapexec, evil-winrm,
#                  smbclient, enum4linux-ng, responder, netexec
#   Wireless:      aircrack-ng, airodump-ng, aireplay-ng, wifite, bettercap
#   Forensics:     binwalk, foremost, exiftool, steghide, strings, hashid
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
        # --- Wireless ---
        "aircrack-ng,airodump-ng,aireplay-ng,wifite,bettercap,"
        # --- Forensics / Binary ---
        "binwalk,foremost,exiftool,steghide,strings,hashid,"
        # --- Utilities ---
        "curl,wget,netcat,socat,sshpass,proxychains4,bash",
    ).split(",")
    if t.strip()
)

# Maximum timeout callers can request (seconds).  Default: 600s (10 min).
MAX_TIMEOUT = int(os.environ.get("KALI_MAX_TIMEOUT", "600"))

MCP_PORT = int(os.environ.get("MCP_PORT", "9001"))

mcp = FastMCP("kali-mcp", host="0.0.0.0", port=MCP_PORT)


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

    Args:
        command: Full shell command string (e.g. 'curl -sk https://... | grep pattern').
        target: Target identifier for logging/reporting.
        timeout: Execution timeout in seconds (default 300, max from KALI_MAX_TIMEOUT).
    """
    timestamp = datetime.now(UTC).isoformat()
    timeout = min(timeout, MAX_TIMEOUT)

    # Basic validation: check that the primary command(s) are allowlisted
    # by extracting the first token of each pipe segment.
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
    """List all available Kali Linux security tools in this container."""
    tools = {}
    for tool_name in sorted(ALLOWED_TOOLS):
        path = shutil.which(tool_name)
        tools[tool_name] = {
            "installed": path is not None,
            "path": path or "not found",
        }
    return json.dumps({"tools": tools, "max_timeout": MAX_TIMEOUT}, indent=2)


if __name__ == "__main__":
    transport = os.environ.get("MCP_TRANSPORT", "sse")
    logger.info(
        "Starting Kali Linux MCP Server (%s on port %d, allowed tools: %s)",
        transport, MCP_PORT, ALLOWED_TOOLS,
    )
    mcp.run(transport=transport)
