"""Kali Linux MCP Server for blhackbox.

Adapted from community Kali MCP servers (k3nn3dy-ai/kali-mcp,
DurkDiggler/Kali-MCP-Server).  Provides MCP tool access to Kali
Linux security tools running inside a Docker container.

Each tool call returns structured output:
  { stdout, stderr, exit_code, tool_name, timestamp, target }
"""

from __future__ import annotations

import asyncio
import base64
import json
import logging
import os
import re
import shlex
import shutil
from datetime import UTC, datetime
from pathlib import Path

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

# Directory for storing screenshot evidence files
SCREENSHOTS_DIR = Path(os.environ.get("SCREENSHOTS_DIR", "/tmp/screenshots"))

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
async def take_screenshot(
    url: str,
    output_format: str = "png",
    width: int = 1280,
    height: int = 1024,
    delay: int = 3,
    timeout: int = 30,
    full_page: bool = False,
) -> str:
    """Capture a screenshot of a URL for PoC evidence in bug bounty reports.

    Uses cutycapt (Qt WebKit headless renderer) to capture web pages as images.
    Returns the screenshot as a base64-encoded string alongside metadata.

    Args:
        url: The URL to screenshot (must start with http:// or https://).
        output_format: Image format — "png" (default) or "jpeg".
        width: Viewport width in pixels (default 1280).
        height: Viewport height in pixels (default 1024).
        delay: Wait time in seconds after page load before capture (default 3).
        timeout: Maximum time in seconds for the entire capture (default 30).
        full_page: If true, capture the full scrollable page height.

    Returns:
        JSON string with screenshot_base64, file_path, metadata, or error.
    """
    timestamp = datetime.now(UTC).isoformat()

    # Validate URL
    if not re.match(r"^https?://", url):
        return json.dumps({
            "error": "URL must start with http:// or https://",
            "url": url,
            "timestamp": timestamp,
        })

    # Validate format
    fmt = output_format.lower()
    if fmt not in ("png", "jpeg"):
        return json.dumps({
            "error": f"Unsupported format '{output_format}'. Use 'png' or 'jpeg'.",
            "timestamp": timestamp,
        })

    # Check for cutycapt
    cutycapt_path = shutil.which("cutycapt")
    if not cutycapt_path:
        return json.dumps({
            "error": "cutycapt is not installed in this container",
            "timestamp": timestamp,
        })

    # Create output directory
    SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)

    # Generate safe filename from URL
    safe_name = re.sub(r"[^a-zA-Z0-9._-]", "_", url)[:100]
    ts_slug = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    ext = "jpg" if fmt == "jpeg" else "png"
    out_file = SCREENSHOTS_DIR / f"{safe_name}_{ts_slug}.{ext}"

    # Build cutycapt command
    cmd_parts = [
        "cutycapt",
        f"--url={url}",
        f"--out={out_file}",
        f"--out-format={fmt}",
        f"--min-width={width}",
        f"--min-height={height}",
        f"--delay={delay * 1000}",  # cutycapt uses milliseconds
        "--insecure",  # Allow self-signed certs (common in pentesting)
    ]

    if full_page:
        # cutycapt captures full page by default when min-height is large
        cmd_parts.append("--min-height=10000")

    logger.info("Taking screenshot: %s -> %s", url, out_file)

    try:
        # cutycapt requires a virtual display (Xvfb)
        xvfb_cmd = ["xvfb-run", "--auto-servernum", "--server-args=-screen 0 1920x1080x24"]
        proc = await asyncio.create_subprocess_exec(
            *xvfb_cmd, *cmd_parts,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout_bytes, stderr_bytes = await asyncio.wait_for(
            proc.communicate(), timeout=timeout
        )
        stderr = stderr_bytes.decode("utf-8", errors="replace")
        exit_code = proc.returncode or 0
    except TimeoutError:
        return json.dumps({
            "error": f"Screenshot timed out after {timeout}s",
            "url": url,
            "tool_name": "cutycapt",
            "timestamp": timestamp,
        })
    except Exception as exc:
        return json.dumps({
            "error": f"Screenshot capture failed: {exc}",
            "url": url,
            "tool_name": "cutycapt",
            "timestamp": timestamp,
        })

    if exit_code != 0 or not out_file.exists():
        return json.dumps({
            "error": f"cutycapt exited with code {exit_code}",
            "stderr": stderr[:500],
            "url": url,
            "tool_name": "cutycapt",
            "timestamp": timestamp,
        })

    # Read and base64-encode the screenshot
    file_bytes = out_file.read_bytes()
    file_size = len(file_bytes)
    b64_data = base64.b64encode(file_bytes).decode("ascii")

    return json.dumps({
        "screenshot_base64": b64_data,
        "file_path": str(out_file),
        "url": url,
        "format": fmt,
        "width": width,
        "height": height,
        "file_size_bytes": file_size,
        "tool_name": "cutycapt",
        "timestamp": timestamp,
    })


@mcp.tool()
def list_available_tools() -> str:
    """List all available Kali Linux security tools in this container."""
    tools = {}

    # Include screenshot tool alongside regular tools
    all_tool_names = sorted(ALLOWED_TOOLS | {"cutycapt"})
    for tool_name in all_tool_names:
        path = shutil.which(tool_name)
        entry: dict = {
            "installed": path is not None,
            "path": path or "not found",
        }
        if tool_name == "cutycapt":
            entry["category"] = "screenshot"
            entry["note"] = "Use take_screenshot() MCP tool for screenshots"
        tools[tool_name] = entry

    return json.dumps({"tools": tools}, indent=2)


if __name__ == "__main__":
    transport = os.environ.get("MCP_TRANSPORT", "sse")
    logger.info(
        "Starting Kali Linux MCP Server (%s on port %d, allowed tools: %s)",
        transport, MCP_PORT, ALLOWED_TOOLS,
    )
    mcp.run(transport=transport)
