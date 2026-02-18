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
import shutil
from datetime import UTC, datetime
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("kali-mcp")

# Tool allowlist from environment
ALLOWED_TOOLS = set(
    t.strip()
    for t in os.environ.get(
        "ALLOWED_TOOLS",
        "nmap,nikto,gobuster,dirb,whatweb,wafw00f,masscan,hydra,sqlmap,wpscan,"
        "subfinder,amass,fierce,dnsenum,whois",
    ).split(",")
    if t.strip()
)

_server = Server("kali-mcp")

# ---------------------------------------------------------------------------
# Tool definitions
# ---------------------------------------------------------------------------

_TOOLS: list[Tool] = [
    Tool(
        name="run_kali_tool",
        description=(
            "Execute a Kali Linux security tool. Returns structured output with "
            "stdout, stderr, exit_code, tool_name, timestamp, and target."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "tool": {
                    "type": "string",
                    "description": f"Tool name. Allowed: {', '.join(sorted(ALLOWED_TOOLS))}",
                },
                "args": {
                    "type": "string",
                    "description": "Command-line arguments for the tool (e.g. '-sV -p 1-1000 target.com')",
                },
                "target": {
                    "type": "string",
                    "description": "Target being scanned (for metadata only)",
                },
                "timeout": {
                    "type": "integer",
                    "description": "Timeout in seconds (default: 300)",
                    "default": 300,
                },
            },
            "required": ["tool", "args"],
        },
    ),
    Tool(
        name="list_available_tools",
        description="List all available Kali Linux security tools in this container.",
        inputSchema={"type": "object", "properties": {}},
    ),
]


@_server.list_tools()
async def handle_list_tools() -> list[Tool]:
    return _TOOLS


@_server.call_tool()
async def handle_call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    try:
        if name == "run_kali_tool":
            result = await _run_tool(arguments)
        elif name == "list_available_tools":
            result = _list_tools()
        else:
            result = json.dumps({"error": f"Unknown tool: {name}"})
        return [TextContent(type="text", text=result)]
    except Exception as exc:
        logger.exception("Kali MCP tool %s failed", name)
        return [TextContent(type="text", text=f"Error: {exc}")]


async def _run_tool(args: dict[str, Any]) -> str:
    """Execute a Kali tool with allowlist validation."""
    tool_name = args["tool"].strip()
    tool_args = args.get("args", "")
    target = args.get("target", "unknown")
    timeout = args.get("timeout", 300)

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

    # Build and execute command
    cmd = f"{tool_name} {tool_args}"
    logger.info("Executing: %s (timeout: %ds)", cmd, timeout)

    timestamp = datetime.now(UTC).isoformat()

    try:
        proc = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout_bytes, stderr_bytes = await asyncio.wait_for(
            proc.communicate(), timeout=timeout
        )
        stdout = stdout_bytes.decode("utf-8", errors="replace")
        stderr = stderr_bytes.decode("utf-8", errors="replace")
        exit_code = proc.returncode or 0
    except asyncio.TimeoutError:
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


def _list_tools() -> str:
    """List all available tools with their install status."""
    tools = {}
    for tool_name in sorted(ALLOWED_TOOLS):
        path = shutil.which(tool_name)
        tools[tool_name] = {
            "installed": path is not None,
            "path": path or "not found",
        }
    return json.dumps({"tools": tools}, indent=2)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

async def run_server() -> None:
    """Start the Kali MCP server on stdio."""
    logger.info("Starting Kali Linux MCP Server (allowed tools: %s)", ALLOWED_TOOLS)
    async with stdio_server() as (read_stream, write_stream):
        await _server.run(
            read_stream,
            write_stream,
            _server.create_initialization_options(),
        )


if __name__ == "__main__":
    asyncio.run(run_server())
