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
# Categories (57 tools):
#   Network/Recon: nmap, rustscan, masscan, netdiscover, arp-scan, traceroute, hping3
#   DNS:           subfinder, amass, fierce, dnsenum, dnsrecon, dig, whois, theharvester
#   Web:           nikto, gobuster, dirb, dirsearch, ffuf, feroxbuster, whatweb, wafw00f,
#                  wpscan, httpx, katana, arjun, paramspider, dalfox
#   Exploitation:  sqlmap, hydra, medusa, john, hashcat, crackmapexec, evil-winrm,
#                  smbclient, enum4linux-ng, responder, netexec
#   Wireless:      aircrack-ng, airodump-ng, aireplay-ng, wifite, bettercap
#   Forensics:     binwalk, foremost, exiftool, steghide, strings, hashid
#   Utilities:     curl, wget, netcat, socat, sshpass, proxychains4
ALLOWED_TOOLS = set(
    t.strip()
    for t in os.environ.get(
        "ALLOWED_TOOLS",
        # --- Network / Recon ---
        "nmap,rustscan,masscan,netdiscover,arp-scan,traceroute,hping3,"
        # --- DNS ---
        "subfinder,amass,fierce,dnsenum,dnsrecon,dig,whois,theharvester,"
        # --- Web Application ---
        "nikto,gobuster,dirb,dirsearch,ffuf,feroxbuster,whatweb,wafw00f,"
        "wpscan,httpx,katana,arjun,paramspider,dalfox,"
        # --- Exploitation / Brute-force ---
        "sqlmap,hydra,medusa,john,hashcat,crackmapexec,evil-winrm,"
        "smbclient,enum4linux-ng,responder,netexec,"
        # --- Wireless ---
        "aircrack-ng,airodump-ng,aireplay-ng,wifite,bettercap,"
        # --- Forensics / Binary ---
        "binwalk,foremost,exiftool,steghide,strings,hashid,"
        # --- Utilities ---
        "curl,wget,netcat,socat,sshpass,proxychains4",
    ).split(",")
    if t.strip()
)

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
    stdout, stderr, exit_code, tool_name, timestamp, and target."""
    tool_name = tool.strip()
    timestamp = datetime.now(UTC).isoformat()

    # Validate tool against allowlist
    if tool_name not in ALLOWED_TOOLS:
        return json.dumps({
            "error": f"Tool '{tool_name}' is not in the allowlist",
            "allowed": sorted(ALLOWED_TOOLS),
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
            "stderr": f"Command timed out after {timeout}s",
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
def list_available_tools() -> str:
    """List all available Kali Linux security tools in this container."""
    tools = {}
    for tool_name in sorted(ALLOWED_TOOLS):
        path = shutil.which(tool_name)
        tools[tool_name] = {
            "installed": path is not None,
            "path": path or "not found",
        }
    return json.dumps({"tools": tools}, indent=2)


if __name__ == "__main__":
    transport = os.environ.get("MCP_TRANSPORT", "sse")
    logger.info(
        "Starting Kali Linux MCP Server (%s on port %d, allowed tools: %s)",
        transport, MCP_PORT, ALLOWED_TOOLS,
    )
    mcp.run(transport=transport)
