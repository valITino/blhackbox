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
from contextlib import asynccontextmanager
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

    # Startup retries — more aggressive than tool-call retries since we
    # know msfrpcd needs 30-90s. Runs in background so MCP server stays
    # responsive.
    STARTUP_RETRIES = int(os.environ.get("MSFRPC_STARTUP_RETRIES", "30"))
    STARTUP_RETRY_DELAY = int(os.environ.get("MSFRPC_STARTUP_RETRY_DELAY", "5"))

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

    async def _try_single_login(self) -> bool | None:
        """Attempt a single login to msfrpcd.

        Returns True on success, False on auth rejection, None on
        connection failure (msfrpcd not ready yet).
        """
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
                self._last_login_failure = 0.0
                return True
            logger.warning("MSFRPC auth rejected: %s", data)
            return False
        except (httpx.ConnectError, httpx.ConnectTimeout) as exc:
            logger.debug("msfrpcd not ready: %s", type(exc).__name__)
            return None
        except Exception as exc:
            logger.warning("MSFRPC connection failed: %s", exc)
            return None

    async def login(self, retries: int | None = None,
                    delay: int | None = None,
                    respect_cooldown: bool = True) -> bool:
        """Authenticate to msfrpcd using msgpack binary protocol.

        msfrpcd can take 30-90 seconds to fully start. This method retries
        the login attempt with a delay between attempts.

        After all retries are exhausted, a cooldown period prevents
        subsequent tool calls from immediately re-running the full retry
        cycle (which would cause ~90s latency per failed call).

        Args:
            retries: Override number of retries (default: LOGIN_RETRIES).
            delay: Override delay between retries (default: LOGIN_RETRY_DELAY).
            respect_cooldown: If False, skip cooldown check (for diagnostics).
        """
        max_retries = retries if retries is not None else self.LOGIN_RETRIES
        retry_delay = delay if delay is not None else self.LOGIN_RETRY_DELAY

        # Cooldown: if we recently exhausted all retries, don't retry again
        # immediately. This prevents every tool call from blocking for 90s
        # when msfrpcd is genuinely down.
        if respect_cooldown:
            now = time.monotonic()
            if self._last_login_failure > 0:
                elapsed = now - self._last_login_failure
                if elapsed < self.LOGIN_COOLDOWN:
                    remaining = self.LOGIN_COOLDOWN - elapsed
                    logger.info(
                        "Login cooldown active (%.0fs remaining). "
                        "Skipping retry cycle — last failure was %.0fs ago.",
                        remaining, elapsed,
                    )
                    return False

        for attempt in range(1, max_retries + 1):
            result = await self._try_single_login()
            if result is True:
                logger.info(
                    "Authenticated to msfrpcd at %s (attempt %d/%d)",
                    self.url, attempt, max_retries,
                )
                return True
            if result is False:
                # Auth explicitly rejected (wrong creds) — don't keep retrying
                logger.error(
                    "msfrpcd rejected credentials (user=%s). "
                    "Check MSFRPC_USER/MSFRPC_PASS.",
                    MSFRPC_USER,
                )
                self._last_login_failure = time.monotonic()
                return False

            # result is None → connection failed, msfrpcd not ready
            if attempt < max_retries:
                logger.info(
                    "msfrpcd not ready (attempt %d/%d), retrying in %ds...",
                    attempt, max_retries, retry_delay,
                )
                await asyncio.sleep(retry_delay)

        logger.error(
            "All %d msfrpcd login attempts failed at %s. "
            "Verify msfrpcd is running and credentials are correct.",
            max_retries, self.url,
        )
        self._last_login_failure = time.monotonic()
        return False

    async def startup_login(self) -> None:
        """Background startup authentication.

        Called once when the MCP server starts. Uses more retries and
        shorter delays than tool-call login since msfrpcd is expected
        to need 30-90s to boot (PostgreSQL init + Ruby startup).

        Does NOT set the cooldown on failure — tool calls should still
        attempt their own login cycle.
        """
        logger.info(
            "Starting background authentication to msfrpcd at %s "
            "(up to %d retries × %ds = %ds)...",
            self.url,
            self.STARTUP_RETRIES,
            self.STARTUP_RETRY_DELAY,
            self.STARTUP_RETRIES * self.STARTUP_RETRY_DELAY,
        )
        for attempt in range(1, self.STARTUP_RETRIES + 1):
            result = await self._try_single_login()
            if result is True:
                logger.info(
                    "Startup auth succeeded on attempt %d/%d — "
                    "msfrpcd token acquired.",
                    attempt, self.STARTUP_RETRIES,
                )
                return
            if result is False:
                logger.error(
                    "Startup auth: msfrpcd rejected credentials. "
                    "Check MSFRPC_USER/MSFRPC_PASS env vars.",
                )
                return

            if attempt < self.STARTUP_RETRIES:
                logger.info(
                    "Startup auth: msfrpcd not ready (attempt %d/%d), "
                    "retrying in %ds...",
                    attempt, self.STARTUP_RETRIES,
                    self.STARTUP_RETRY_DELAY,
                )
                await asyncio.sleep(self.STARTUP_RETRY_DELAY)

        logger.error(
            "Startup auth: all %d attempts failed. msfrpcd may not be "
            "running. Tool calls will retry on demand.",
            self.STARTUP_RETRIES,
        )
        # NOTE: Do NOT set _last_login_failure here — let tool calls
        # attempt their own login cycle independently.

    async def call(self, method: str, *args: Any) -> dict[str, Any]:
        """Call an MSFRPC method using msgpack encoding.

        Re-authenticates once on token expiry (default 300s timeout).
        """
        # If startup login is still running, wait for it (with timeout)
        # instead of starting a competing login cycle.
        global _startup_login_task
        if not self.token and _startup_login_task and not _startup_login_task.done():
            logger.info(
                "Waiting for startup authentication to complete before "
                "calling %s...", method,
            )
            try:
                await asyncio.wait_for(
                    asyncio.shield(_startup_login_task), timeout=120,
                )
            except asyncio.TimeoutError:
                logger.warning("Startup auth still running after 120s.")

        if not self.token:
            if not await self.login():
                # Build a diagnostic error message
                cooldown_info = ""
                if self._last_login_failure > 0:
                    elapsed = time.monotonic() - self._last_login_failure
                    remaining = max(0, self.LOGIN_COOLDOWN - elapsed)
                    if remaining > 0:
                        cooldown_info = (
                            f" Login cooldown active ({remaining:.0f}s remaining). "
                            "Use the msf_status tool to force a reconnection attempt."
                        )
                return {
                    "error": (
                        "Not authenticated to msfrpcd. "
                        "Ensure msfrpcd is running and credentials are correct "
                        f"(user={MSFRPC_USER}, ssl={MSFRPC_SSL}, "
                        f"host={MSFRPC_HOST}:{MSFRPC_PORT}).{cooldown_info}"
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

# Background task handle for startup authentication
_startup_login_task: asyncio.Task | None = None


@asynccontextmanager
async def _lifespan(server: FastMCP):
    """FastMCP lifespan — launch background msfrpcd authentication."""
    global _startup_login_task

    # Pre-flight check: quick connectivity test before starting retry loop
    import socket
    try:
        sock = socket.create_connection(
            (MSFRPC_HOST, MSFRPC_PORT), timeout=2,
        )
        sock.close()
        logger.info(
            "Pre-flight: msfrpcd port %s:%d is reachable.",
            MSFRPC_HOST, MSFRPC_PORT,
        )
    except (ConnectionRefusedError, OSError, socket.timeout):
        logger.warning(
            "Pre-flight: msfrpcd is NOT reachable at %s:%d. "
            "All Metasploit tools will fail until msfrpcd is started. "
            "Ensure msfrpcd is running: "
            "msfrpcd -U %s -P <pass> -p %d -a %s",
            MSFRPC_HOST, MSFRPC_PORT,
            MSFRPC_USER, MSFRPC_PORT, MSFRPC_HOST,
        )

    _startup_login_task = asyncio.create_task(_rpc.startup_login())
    try:
        yield {}
    finally:
        if _startup_login_task and not _startup_login_task.done():
            _startup_login_task.cancel()
        await _rpc.close()


mcp = FastMCP(
    "metasploit-mcp", host="0.0.0.0", port=MCP_PORT, lifespan=_lifespan,
)


def _json(data: Any) -> str:
    """Serialize to JSON, handling non-serializable types."""
    return json.dumps(data, indent=2, default=str)


# ---------------------------------------------------------------------------
# MCP Tools — Diagnostics
# ---------------------------------------------------------------------------

@mcp.tool()
async def msf_status(force_reconnect: bool = False) -> str:
    """Check msfrpcd connection status and optionally force reconnection.

    Use this tool to diagnose authentication failures. When force_reconnect
    is True, it bypasses the login cooldown and attempts a fresh connection.

    Args:
        force_reconnect: If True, clear cooldown and attempt a fresh login.
    """
    status: dict[str, Any] = {
        "msfrpcd_url": _rpc.url,
        "ssl": MSFRPC_SSL,
        "user": MSFRPC_USER,
        "authenticated": _rpc.token is not None,
        "token_present": _rpc.token is not None,
    }

    # Cooldown info
    if _rpc._last_login_failure > 0:
        elapsed = time.monotonic() - _rpc._last_login_failure
        remaining = max(0, _rpc.LOGIN_COOLDOWN - elapsed)
        status["cooldown_active"] = remaining > 0
        status["cooldown_remaining_seconds"] = round(remaining, 1)
        status["last_failure_seconds_ago"] = round(elapsed, 1)
    else:
        status["cooldown_active"] = False

    # Startup task status
    if _startup_login_task:
        status["startup_login_done"] = _startup_login_task.done()
    else:
        status["startup_login_done"] = "not_started"

    if force_reconnect:
        logger.info("Force reconnect requested — clearing cooldown and token.")
        _rpc.token = None
        _rpc._last_login_failure = 0.0
        status["action"] = "force_reconnect"

        # Try a single login attempt first (fast check)
        result = await _rpc._try_single_login()
        if result is True:
            status["reconnect_result"] = "success"
            status["authenticated"] = True
            status["token_present"] = True
        elif result is False:
            status["reconnect_result"] = "credentials_rejected"
            status["authenticated"] = False
        else:
            # Connection failed — try full retry cycle (no cooldown)
            status["reconnect_result"] = "connection_failed_trying_retries"
            success = await _rpc.login(
                retries=5, delay=3, respect_cooldown=False,
            )
            status["reconnect_result"] = "success" if success else "failed"
            status["authenticated"] = success
            status["token_present"] = _rpc.token is not None
    elif not _rpc.token:
        # Not authenticated — try a quick single login (non-blocking)
        result = await _rpc._try_single_login()
        if result is True:
            status["quick_login"] = "success"
            status["authenticated"] = True
            status["token_present"] = True
        elif result is False:
            status["quick_login"] = "credentials_rejected"
        else:
            status["quick_login"] = "msfrpcd_unreachable"
            status["hint"] = (
                "msfrpcd may still be starting up (takes 30-90s). "
                "Use msf_status(force_reconnect=True) to retry with "
                "multiple attempts."
            )

    return _json(status)


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
