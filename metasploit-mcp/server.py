"""Metasploit MCP Server for blhackbox.

Provides MCP tool access to the Metasploit Framework via the MSF RPC API
(msfrpcd).  Inspired by GH05TCREW/MetasploitMCP (Apache 2.0, 379+ stars)
and LYFTIUM-INC/msfconsole-mcp (48 tools, 95% MSF coverage).

Exposes 13 core tools for exploit lifecycle management:
  - list_exploits, list_payloads, run_exploit, run_auxiliary_module
  - run_post_module, generate_payload
  - list_sessions, send_session_command, terminate_session
  - list_listeners, start_listener, stop_job
  - msf_console_execute (raw msfconsole command execution)

Connection: Connects to msfrpcd via HTTP (MSFRPC_HOST:MSFRPC_PORT).
Transport: FastMCP SSE on port 9002.

NOTE: Requires a running msfrpcd instance. The Docker container bundles
Metasploit Framework and starts msfrpcd automatically on startup.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from typing import Any

import httpx
from mcp.server.fastmcp import FastMCP

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("metasploit-mcp")

# --- Configuration ---
MSFRPC_HOST = os.environ.get("MSFRPC_HOST", "127.0.0.1")
MSFRPC_PORT = int(os.environ.get("MSFRPC_PORT", "55553"))
MSFRPC_USER = os.environ.get("MSFRPC_USER", "msf")
MSFRPC_PASS = os.environ.get("MSFRPC_PASS", "msf")
MSFRPC_SSL = os.environ.get("MSFRPC_SSL", "true").lower() == "true"
MCP_PORT = int(os.environ.get("MCP_PORT", "9002"))

# Execution timeout for exploit/module runs
EXEC_TIMEOUT = int(os.environ.get("EXEC_TIMEOUT", "300"))

mcp = FastMCP("metasploit-mcp", host="0.0.0.0", port=MCP_PORT)


# ---------------------------------------------------------------------------
# MSFRPC Client — lightweight HTTP JSON-RPC wrapper
# ---------------------------------------------------------------------------

class MSFRPCClient:
    """Minimal Metasploit RPC client using msgpack-free JSON-RPC."""

    # Number of login retries — msfrpcd may need up to 90 s to start.
    LOGIN_RETRIES = int(os.environ.get("MSFRPC_LOGIN_RETRIES", "10"))
    LOGIN_RETRY_DELAY = int(os.environ.get("MSFRPC_LOGIN_RETRY_DELAY", "6"))

    def __init__(self) -> None:
        scheme = "https" if MSFRPC_SSL else "http"
        self.url = f"{scheme}://{MSFRPC_HOST}:{MSFRPC_PORT}/api/"
        self.token: str | None = None
        self._client = httpx.AsyncClient(verify=False, timeout=EXEC_TIMEOUT)

    async def login(self) -> bool:
        """Authenticate to msfrpcd with retry logic for slow startup.

        msfrpcd can take 30-90 seconds to fully start. This method retries
        the login attempt with a delay between attempts to avoid immediate
        'Not authenticated' failures on first tool call.
        """
        for attempt in range(1, self.LOGIN_RETRIES + 1):
            try:
                resp = await self._client.post(
                    self.url,
                    json=["auth.login", MSFRPC_USER, MSFRPC_PASS],
                )
                data = resp.json()
                if data.get("result") == "success":
                    self.token = data["token"]
                    logger.info(
                        "Authenticated to msfrpcd at %s (attempt %d/%d)",
                        self.url, attempt, self.LOGIN_RETRIES,
                    )
                    return True
                logger.warning(
                    "MSFRPC auth failed (attempt %d/%d): %s",
                    attempt, self.LOGIN_RETRIES, data,
                )
            except Exception as exc:
                logger.warning(
                    "MSFRPC connection failed (attempt %d/%d): %s",
                    attempt, self.LOGIN_RETRIES, exc,
                )

            if attempt < self.LOGIN_RETRIES:
                logger.info(
                    "Retrying msfrpcd login in %ds...", self.LOGIN_RETRY_DELAY,
                )
                await asyncio.sleep(self.LOGIN_RETRY_DELAY)

        logger.error(
            "All %d msfrpcd login attempts failed at %s",
            self.LOGIN_RETRIES, self.url,
        )
        return False

    async def call(self, method: str, *args: Any) -> dict[str, Any]:
        """Call an MSFRPC method.  Re-authenticates once on auth failure."""
        if not self.token:
            if not await self.login():
                return {
                    "error": (
                        "Not authenticated to msfrpcd. "
                        "Check that msfrpcd is running and credentials are correct "
                        "(MSFRPC_USER/MSFRPC_PASS)."
                    ),
                }
        try:
            payload = [method, self.token, *args]
            resp = await self._client.post(self.url, json=payload)
            data = resp.json()
            # Handle expired token — re-authenticate once and retry
            if data.get("error") is True and "Invalid Authentication" in str(
                data.get("error_message", ""),
            ):
                logger.warning("MSFRPC token expired, re-authenticating...")
                self.token = None
                if await self.login():
                    payload = [method, self.token, *args]
                    resp = await self._client.post(self.url, json=payload)
                    return resp.json()
                return {"error": "Re-authentication to msfrpcd failed"}
            return data
        except Exception as exc:
            logger.error("MSFRPC call %s failed: %s", method, exc)
            return {"error": str(exc)}

    async def close(self) -> None:
        await self._client.aclose()


_rpc = MSFRPCClient()


def _json(data: Any) -> str:
    """Serialize to JSON, handling non-serializable types."""
    return json.dumps(data, indent=2, default=str)


# ---------------------------------------------------------------------------
# MCP Tools — Exploit Discovery
# ---------------------------------------------------------------------------

@mcp.tool()
async def list_exploits(search: str = "", limit: int = 50) -> str:
    """Search and list available Metasploit exploit modules.

    Args:
        search: Search term to filter exploits (e.g. 'apache', 'smb', 'CVE-2021').
        limit: Maximum number of results to return (default 50).
    """
    result = await _rpc.call("module.search", search, "exploit")
    if "error" in result:
        return _json(result)
    modules = result.get("modules", result.get("result", []))
    if isinstance(modules, list):
        modules = modules[:limit]
    return _json({"exploits": modules, "count": len(modules)})


@mcp.tool()
async def list_payloads(
    search: str = "",
    platform: str = "",
    arch: str = "",
    limit: int = 50,
) -> str:
    """Search and list available Metasploit payload modules.

    Args:
        search: Search term (e.g. 'meterpreter', 'reverse_tcp').
        platform: Filter by platform (e.g. 'windows', 'linux').
        arch: Filter by architecture (e.g. 'x86', 'x64').
        limit: Maximum number of results (default 50).
    """
    query = search
    if platform:
        query += f" platform:{platform}"
    if arch:
        query += f" arch:{arch}"
    result = await _rpc.call("module.search", query.strip(), "payload")
    if "error" in result:
        return _json(result)
    modules = result.get("modules", result.get("result", []))
    if isinstance(modules, list):
        modules = modules[:limit]
    return _json({"payloads": modules, "count": len(modules)})


# ---------------------------------------------------------------------------
# MCP Tools — Exploit Execution
# ---------------------------------------------------------------------------

@mcp.tool()
async def run_exploit(
    module: str,
    options: dict[str, str],
    payload: str = "",
    check_first: bool = True,
) -> str:
    """Configure and execute a Metasploit exploit against a target.

    Args:
        module: Full module path (e.g. 'exploit/multi/http/apache_mod_cgi_bash_env_exec').
        options: Dict of module options (e.g. {"RHOSTS": "10.0.0.1", "RPORT": "443"}).
        payload: Payload module path (e.g. 'payload/linux/x86/meterpreter/reverse_tcp').
        check_first: If True, run the check method before exploiting (default True).
    """
    # Optionally check vulnerability first
    if check_first:
        check_result = await _rpc.call("module.check", "exploit", module, options)
        if "error" not in check_result:
            vuln_status = check_result.get("result", "unknown")
            if "not vulnerable" in str(vuln_status).lower():
                return _json({
                    "status": "not_vulnerable",
                    "check_result": vuln_status,
                    "module": module,
                })

    # Set payload if provided
    if payload:
        options["PAYLOAD"] = payload

    result = await _rpc.call("module.execute", "exploit", module, options)
    return _json({"module": module, "result": result})


@mcp.tool()
async def run_auxiliary_module(
    module: str,
    options: dict[str, str],
) -> str:
    """Run a Metasploit auxiliary module (scanners, fuzzers, etc.).

    Args:
        module: Full module path (e.g. 'auxiliary/scanner/smb/smb_version').
        options: Dict of module options (e.g. {"RHOSTS": "10.0.0.0/24"}).
    """
    result = await _rpc.call("module.execute", "auxiliary", module, options)
    return _json({"module": module, "result": result})


@mcp.tool()
async def run_post_module(
    module: str,
    session_id: int,
    options: dict[str, str] | None = None,
) -> str:
    """Execute a post-exploitation module against an existing session.

    Args:
        module: Full module path (e.g. 'post/multi/gather/env').
        session_id: Active session ID to run the module against.
        options: Additional module options (optional).
    """
    opts = options or {}
    opts["SESSION"] = str(session_id)
    result = await _rpc.call("module.execute", "post", module, opts)
    return _json({"module": module, "session_id": session_id, "result": result})


@mcp.tool()
async def generate_payload(
    payload: str,
    options: dict[str, str],
    format: str = "raw",
) -> str:
    """Generate a payload using Metasploit (msfvenom equivalent via RPC).

    Args:
        payload: Payload module path (e.g. 'payload/windows/meterpreter/reverse_tcp').
        options: Payload options (e.g. {"LHOST": "10.0.0.1", "LPORT": "4444"}).
        format: Output format (raw, exe, elf, python, ruby, c, etc.).
    """
    result = await _rpc.call("module.payload_generate", payload, options, format)
    if "error" in result:
        return _json(result)
    # Payload data may be binary; return metadata
    payload_data = result.get("payload", "")
    return _json({
        "payload": payload,
        "format": format,
        "size_bytes": len(payload_data) if isinstance(payload_data, str | bytes) else 0,
        "status": "generated",
    })


# ---------------------------------------------------------------------------
# MCP Tools — Session Management
# ---------------------------------------------------------------------------

@mcp.tool()
async def list_sessions() -> str:
    """List all active Metasploit sessions (shells, meterpreter, etc.)."""
    result = await _rpc.call("session.list")
    if "error" in result:
        return _json(result)
    sessions = result if isinstance(result, dict) else {}
    # Filter out the token key if present
    sessions.pop("result", None)
    return _json({"sessions": sessions, "count": len(sessions)})


@mcp.tool()
async def send_session_command(
    session_id: int,
    command: str,
    timeout: int = 30,
) -> str:
    """Execute a command in an active Metasploit session.

    Args:
        session_id: The session ID to interact with.
        command: Command to execute in the session.
        timeout: Seconds to wait for output (default 30).
    """
    # Write command
    write_result = await _rpc.call("session.shell_write", str(session_id), command + "\n")
    if "error" in write_result:
        return _json(write_result)

    # Wait and read output
    time.sleep(min(timeout, 5))
    read_result = await _rpc.call("session.shell_read", str(session_id))
    return _json({
        "session_id": session_id,
        "command": command,
        "output": read_result.get("data", ""),
    })


@mcp.tool()
async def terminate_session(session_id: int) -> str:
    """Terminate an active Metasploit session.

    Args:
        session_id: The session ID to terminate.
    """
    result = await _rpc.call("session.stop", str(session_id))
    return _json({"session_id": session_id, "result": result})


# ---------------------------------------------------------------------------
# MCP Tools — Listener / Handler Management
# ---------------------------------------------------------------------------

@mcp.tool()
async def list_listeners() -> str:
    """List all active Metasploit handlers (background jobs)."""
    result = await _rpc.call("job.list")
    if "error" in result:
        return _json(result)
    return _json({"jobs": result, "count": len(result)})


@mcp.tool()
async def start_listener(
    payload: str,
    lhost: str,
    lport: int,
    options: dict[str, str] | None = None,
) -> str:
    """Start a new multi/handler listener to receive reverse connections.

    Args:
        payload: Payload to listen for (e.g. 'payload/windows/meterpreter/reverse_tcp').
        lhost: Local host IP to listen on.
        lport: Local port to listen on.
        options: Additional handler options (optional).
    """
    opts = options or {}
    opts.update({
        "PAYLOAD": payload,
        "LHOST": lhost,
        "LPORT": str(lport),
    })
    result = await _rpc.call(
        "module.execute", "exploit", "exploit/multi/handler", opts,
    )
    listener = {"payload": payload, "lhost": lhost, "lport": lport}
    return _json({"listener": listener, "result": result})


@mcp.tool()
async def stop_job(job_id: int) -> str:
    """Stop a running Metasploit background job.

    Args:
        job_id: The job ID to terminate.
    """
    result = await _rpc.call("job.stop", str(job_id))
    return _json({"job_id": job_id, "result": result})


# ---------------------------------------------------------------------------
# MCP Tools — Console (raw msfconsole)
# ---------------------------------------------------------------------------

@mcp.tool()
async def msf_console_execute(command: str, timeout: int = 30) -> str:
    """Execute a raw msfconsole command and return the output.

    This is a general-purpose escape hatch for any Metasploit functionality
    not covered by the dedicated tools above.

    Args:
        command: The msfconsole command to execute (e.g. 'db_nmap -sV 10.0.0.1').
        timeout: Seconds to wait for output (default 30).
    """
    # Create a console
    console = await _rpc.call("console.create")
    if "error" in console:
        return _json(console)
    console_id = console.get("id", "0")

    # Write command
    await _rpc.call("console.write", console_id, command + "\n")

    # Poll for output
    output_parts: list[str] = []
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        read = await _rpc.call("console.read", console_id)
        data = read.get("data", "")
        if data:
            output_parts.append(data)
        busy = read.get("busy", False)
        if not busy and output_parts:
            break
        await _async_sleep(1)

    # Destroy console
    await _rpc.call("console.destroy", console_id)

    return _json({
        "command": command,
        "output": "".join(output_parts),
    })


async def _async_sleep(seconds: float) -> None:
    """Async-compatible sleep."""
    import asyncio
    await asyncio.sleep(seconds)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    transport = os.environ.get("MCP_TRANSPORT", "sse")
    logger.info(
        "Starting Metasploit MCP Server (%s on port %d, msfrpcd at %s:%d)",
        transport, MCP_PORT, MSFRPC_HOST, MSFRPC_PORT,
    )
    mcp.run(transport=transport)
