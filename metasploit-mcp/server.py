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

Connection: Connects to msfrpcd via HTTPS using **MessagePack** binary
protocol (Content-Type: binary/message-pack).  msfrpcd does NOT speak
JSON — it uses msgpack exclusively for request/response encoding.

Reference implementation: pymetasploit3 (Coalfire-Research/pymetasploit3)

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
import msgpack
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

# msfrpcd msgpack headers — msfrpcd ONLY understands binary/message-pack,
# NOT application/json.  Sending JSON causes silent auth failures.
_MSGPACK_HEADERS = {"Content-type": "binary/message-pack"}


# ---------------------------------------------------------------------------
# MSFRPC Client — msgpack binary protocol wrapper
# ---------------------------------------------------------------------------

class MSFRPCClient:
    """Metasploit RPC client using msgpack binary protocol.

    msfrpcd uses MessagePack encoding (Content-Type: binary/message-pack),
    NOT JSON.  All requests are msgpack-encoded arrays:
      - auth.login: ["auth.login", username, password]
      - authenticated: ["method.name", token, *args]

    Reference: pymetasploit3 (Coalfire-Research/pymetasploit3)
    """

    # Number of login retries — msfrpcd may need 30-90s to start.
    LOGIN_RETRIES = int(os.environ.get("MSFRPC_LOGIN_RETRIES", "15"))
    LOGIN_RETRY_DELAY = int(os.environ.get("MSFRPC_LOGIN_RETRY_DELAY", "6"))

    # Cooldown (seconds) after all login retries are exhausted. Prevents
    # every tool call from re-running the full 90s retry loop when msfrpcd
    # is genuinely down.
    LOGIN_COOLDOWN = int(os.environ.get("MSFRPC_LOGIN_COOLDOWN", "30"))

    def __init__(self) -> None:
        scheme = "https" if MSFRPC_SSL else "http"
        self.url = f"{scheme}://{MSFRPC_HOST}:{MSFRPC_PORT}/api/"
        self.token: str | None = None
        self._client = httpx.AsyncClient(
            verify=False,  # msfrpcd uses self-signed certs
            timeout=EXEC_TIMEOUT,
        )
        # Timestamp of last failed login cycle — used for cooldown
        self._last_login_failure: float = 0.0

    async def login(self) -> bool:
        """Authenticate to msfrpcd using msgpack binary protocol.

        msfrpcd can take 30-90 seconds to fully start. This method retries
        the login attempt with a delay between attempts.

        After all retries are exhausted, a cooldown period prevents
        subsequent tool calls from immediately re-running the full retry
        cycle (which would cause ~90s latency per failed call).
        """
        # Cooldown: if we recently exhausted all retries, don't retry again
        # immediately. This prevents every tool call from blocking for 90s
        # when msfrpcd is genuinely down.
        now = time.monotonic()
        if self._last_login_failure > 0:
            elapsed = now - self._last_login_failure
            if elapsed < self.LOGIN_COOLDOWN:
                logger.info(
                    "Login cooldown active (%.0fs remaining). "
                    "Skipping retry cycle — last failure was %.0fs ago.",
                    self.LOGIN_COOLDOWN - elapsed, elapsed,
                )
                return False

        for attempt in range(1, self.LOGIN_RETRIES + 1):
            try:
                payload = msgpack.packb(["auth.login", MSFRPC_USER, MSFRPC_PASS])
                resp = await self._client.post(
                    self.url,
                    content=payload,
                    headers=_MSGPACK_HEADERS,
                )
                data = msgpack.unpackb(resp.content, raw=False)
                if data.get("result") == "success":
                    self.token = data["token"]
                    self._last_login_failure = 0.0  # Reset cooldown on success
                    logger.info(
                        "Authenticated to msfrpcd at %s (attempt %d/%d)",
                        self.url, attempt, self.LOGIN_RETRIES,
                    )
                    return True
                logger.warning(
                    "MSFRPC auth rejected (attempt %d/%d): %s",
                    attempt, self.LOGIN_RETRIES, data,
                )
            except (httpx.ConnectError, httpx.ConnectTimeout) as exc:
                logger.info(
                    "msfrpcd not ready (attempt %d/%d): %s",
                    attempt, self.LOGIN_RETRIES, type(exc).__name__,
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
            "All %d msfrpcd login attempts failed at %s. "
            "Verify msfrpcd is running and credentials are correct.",
            self.LOGIN_RETRIES, self.url,
        )
        self._last_login_failure = time.monotonic()
        return False

    async def call(self, method: str, *args: Any) -> dict[str, Any]:
        """Call an MSFRPC method using msgpack encoding.

        Re-authenticates once on token expiry (default 300s timeout).
        """
        if not self.token:
            if not await self.login():
                return {
                    "error": (
                        "Not authenticated to msfrpcd. "
                        "Ensure msfrpcd is running and credentials are correct "
                        f"(user={MSFRPC_USER}, ssl={MSFRPC_SSL}, "
                        f"host={MSFRPC_HOST}:{MSFRPC_PORT})."
                    ),
                }
        try:
            payload = msgpack.packb([method, self.token, *args])
            resp = await self._client.post(
                self.url,
                content=payload,
                headers=_MSGPACK_HEADERS,
            )
            data = msgpack.unpackb(resp.content, raw=False)

            # Handle expired/invalid token — re-authenticate once and retry
            error_msg = str(data.get("error_message", ""))
            if data.get("error") is True and (
                "Invalid Authentication" in error_msg
                or "Token" in error_msg
            ):
                logger.warning("MSFRPC token expired, re-authenticating...")
                self.token = None
                if await self.login():
                    payload = msgpack.packb([method, self.token, *args])
                    resp = await self._client.post(
                        self.url,
                        content=payload,
                        headers=_MSGPACK_HEADERS,
                    )
                    return msgpack.unpackb(resp.content, raw=False)
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
    await asyncio.sleep(min(timeout, 5))
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
        await asyncio.sleep(1)

    # Destroy console
    await _rpc.call("console.destroy", console_id)

    return _json({
        "command": command,
        "output": "".join(output_parts),
    })


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    transport = os.environ.get("MCP_TRANSPORT", "sse")
    logger.info(
        "Starting Metasploit MCP Server (%s on port %d, msfrpcd at %s:%d, ssl=%s)",
        transport, MCP_PORT, MSFRPC_HOST, MSFRPC_PORT, MSFRPC_SSL,
    )
    mcp.run(transport=transport)
