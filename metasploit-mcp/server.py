"""Metasploit MCP Server for blhackbox.

Provides MCP tool access to the Metasploit Framework via the MSF RPC API
(msfrpcd).  Inspired by GH05TCREW/MetasploitMCP (Apache 2.0) and
fishke22/MetasploitMCP.

Exposes 14 core tools for exploit lifecycle management:
  - msf_status (diagnostics)
  - list_exploits, list_payloads, run_exploit, run_auxiliary_module
  - run_post_module, generate_payload
  - list_sessions, send_session_command, terminate_session
  - list_listeners, start_listener, stop_job
  - msf_console_execute (raw msfconsole command execution)

Connection: Connects to msfrpcd via HTTPS using **MessagePack** binary
protocol (Content-Type: binary/message-pack).  msfrpcd does NOT speak
JSON — it uses msgpack exclusively for request/response encoding.

Reference implementation: pymetasploit3 (Coalfire-Research/pymetasploit3)

Transport: FastMCP SSE on port 9002 (default) or stdio.

NOTE: Requires a running msfrpcd instance. The Docker container bundles
Metasploit Framework and starts msfrpcd automatically on startup.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import shutil
import socket
import time
from contextlib import asynccontextmanager
from enum import Enum
from typing import Any

import httpx
import msgpack
from mcp.server.fastmcp import FastMCP

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("metasploit-mcp")

# --- Configuration (all overridable via environment variables) ---
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
# Failure reason enum — differentiates error causes (report issue #5)
# ---------------------------------------------------------------------------

class FailureReason(str, Enum):
    """Categorised failure reasons for diagnostic clarity."""
    MSFRPCD_NOT_INSTALLED = "msfrpcd_not_installed"
    MSFRPCD_NOT_RUNNING = "msfrpcd_not_running"
    CONNECTION_REFUSED = "connection_refused"
    CONNECTION_TIMEOUT = "connection_timeout"
    CREDENTIALS_REJECTED = "credentials_rejected"
    SSL_ERROR = "ssl_error"
    COOLDOWN_ACTIVE = "cooldown_active"
    UNKNOWN = "unknown"


# ---------------------------------------------------------------------------
# Standardised error response (report issue #6)
# ---------------------------------------------------------------------------

def _error_response(
    tool: str,
    reason: FailureReason,
    message: str,
    *,
    cooldown_remaining: float | None = None,
) -> dict[str, Any]:
    """Build a consistent error response dict used by all tools."""
    resp: dict[str, Any] = {
        "error": True,
        "tool": tool,
        "reason": reason.value,
        "message": message,
        "config": {
            "msfrpcd_url": f"{'https' if MSFRPC_SSL else 'http'}://{MSFRPC_HOST}:{MSFRPC_PORT}/api/",
            "user": MSFRPC_USER,
            "ssl": MSFRPC_SSL,
        },
    }
    if cooldown_remaining is not None and cooldown_remaining > 0:
        resp["cooldown_remaining_seconds"] = round(cooldown_remaining, 1)
        resp["hint"] = (
            "Use msf_status(force_reconnect=True) to bypass cooldown "
            "and force a fresh connection attempt."
        )
    return resp


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

    # Cooldown (seconds) after all login retries are exhausted.
    # Reduced from 30s to 10s to avoid blocking parallel tool calls too long
    # (report issue #3).
    LOGIN_COOLDOWN = int(os.environ.get("MSFRPC_LOGIN_COOLDOWN", "10"))

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
        # Tracks the reason for the last failure (report issue #5)
        self._last_failure_reason: FailureReason = FailureReason.UNKNOWN
        # Startup login result tracking (report issue #9)
        self.startup_login_result: str = "pending"

    async def _try_single_login(self) -> tuple[bool | None, FailureReason]:
        """Attempt a single login to msfrpcd.

        Returns a tuple of (result, reason):
          - (True, _) on success
          - (False, reason) on auth rejection
          - (None, reason) on connection failure
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
                self._last_failure_reason = FailureReason.UNKNOWN
                return True, FailureReason.UNKNOWN
            logger.warning("MSFRPC auth rejected: %s", data)
            return False, FailureReason.CREDENTIALS_REJECTED
        except httpx.ConnectError:
            logger.debug("msfrpcd connection refused at %s", self.url)
            return None, FailureReason.CONNECTION_REFUSED
        except httpx.ConnectTimeout:
            logger.debug("msfrpcd connection timed out at %s", self.url)
            return None, FailureReason.CONNECTION_TIMEOUT
        except Exception as exc:
            exc_str = str(exc).lower()
            if "ssl" in exc_str or "tls" in exc_str or "certificate" in exc_str:
                logger.warning("MSFRPC SSL error: %s", exc)
                return None, FailureReason.SSL_ERROR
            logger.warning("MSFRPC connection failed: %s", exc)
            return None, FailureReason.UNKNOWN

    async def login(
        self,
        retries: int | None = None,
        delay: int | None = None,
        respect_cooldown: bool = True,
    ) -> bool:
        """Authenticate to msfrpcd using msgpack binary protocol.

        msfrpcd can take 30-90 seconds to fully start. This method retries
        the login attempt with a delay between attempts.

        After all retries are exhausted, a cooldown period prevents
        subsequent tool calls from immediately re-running the full retry
        cycle (which would cause ~90s latency per failed call).
        """
        max_retries = retries if retries is not None else self.LOGIN_RETRIES
        retry_delay = delay if delay is not None else self.LOGIN_RETRY_DELAY

        # Cooldown check
        if respect_cooldown and self._last_login_failure > 0:
            now = time.monotonic()
            elapsed = now - self._last_login_failure
            if elapsed < self.LOGIN_COOLDOWN:
                remaining = self.LOGIN_COOLDOWN - elapsed
                logger.info(
                    "Login cooldown active (%.0fs remaining). "
                    "Skipping retry cycle.",
                    remaining,
                )
                self._last_failure_reason = FailureReason.COOLDOWN_ACTIVE
                return False

        for attempt in range(1, max_retries + 1):
            result, reason = await self._try_single_login()
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
                self._last_failure_reason = reason
                return False

            # result is None → connection failed, msfrpcd not ready
            self._last_failure_reason = reason
            if attempt < max_retries:
                logger.info(
                    "msfrpcd not ready (%s, attempt %d/%d), retrying in %ds...",
                    reason.value, attempt, max_retries, retry_delay,
                )
                await asyncio.sleep(retry_delay)

        logger.error(
            "All %d msfrpcd login attempts failed at %s (%s). "
            "Verify msfrpcd is running and credentials are correct.",
            max_retries, self.url, self._last_failure_reason.value,
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
            "(up to %d retries x %ds = %ds)...",
            self.url,
            self.STARTUP_RETRIES,
            self.STARTUP_RETRY_DELAY,
            self.STARTUP_RETRIES * self.STARTUP_RETRY_DELAY,
        )
        for attempt in range(1, self.STARTUP_RETRIES + 1):
            result, reason = await self._try_single_login()
            if result is True:
                logger.info(
                    "Startup auth succeeded on attempt %d/%d — "
                    "msfrpcd token acquired.",
                    attempt, self.STARTUP_RETRIES,
                )
                self.startup_login_result = "success"
                return
            if result is False:
                logger.error(
                    "Startup auth: msfrpcd rejected credentials. "
                    "Check MSFRPC_USER/MSFRPC_PASS env vars.",
                )
                self.startup_login_result = f"failed:{reason.value}"
                return

            if attempt < self.STARTUP_RETRIES:
                logger.info(
                    "Startup auth: msfrpcd not ready (%s, attempt %d/%d), "
                    "retrying in %ds...",
                    reason.value, attempt, self.STARTUP_RETRIES,
                    self.STARTUP_RETRY_DELAY,
                )
                await asyncio.sleep(self.STARTUP_RETRY_DELAY)

        logger.error(
            "Startup auth: all %d attempts failed (%s). msfrpcd may not be "
            "running. Tool calls will retry on demand.",
            self.STARTUP_RETRIES, self._last_failure_reason.value,
        )
        self.startup_login_result = f"failed:{self._last_failure_reason.value}"
        # NOTE: Do NOT set _last_login_failure here — let tool calls
        # attempt their own login cycle independently.

    async def call(self, method: str, *args: Any, tool_name: str = "") -> dict[str, Any]:
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
                # Build a diagnostic error message with specific reason
                cooldown_remaining = None
                reason = self._last_failure_reason
                if self._last_login_failure > 0:
                    elapsed = time.monotonic() - self._last_login_failure
                    cooldown_remaining = max(0, self.LOGIN_COOLDOWN - elapsed)

                # Check if msfrpcd binary exists (report issue #1)
                msfrpcd_installed = shutil.which("msfrpcd") is not None
                if not msfrpcd_installed and reason in (
                    FailureReason.CONNECTION_REFUSED,
                    FailureReason.UNKNOWN,
                ):
                    reason = FailureReason.MSFRPCD_NOT_INSTALLED

                messages = {
                    FailureReason.MSFRPCD_NOT_INSTALLED: (
                        "Metasploit Framework is not installed. "
                        "Install with: apt-get install -y metasploit-framework, "
                        "or use Docker: docker compose up metasploit-mcp"
                    ),
                    FailureReason.MSFRPCD_NOT_RUNNING: (
                        f"msfrpcd is not running at {MSFRPC_HOST}:{MSFRPC_PORT}. "
                        f"Start it with: msfrpcd -U {MSFRPC_USER} -P <pass> "
                        f"-p {MSFRPC_PORT} -a {MSFRPC_HOST}"
                    ),
                    FailureReason.CONNECTION_REFUSED: (
                        f"Connection refused at {MSFRPC_HOST}:{MSFRPC_PORT}. "
                        "msfrpcd is not running or not listening on this port."
                    ),
                    FailureReason.CONNECTION_TIMEOUT: (
                        f"Connection timed out at {MSFRPC_HOST}:{MSFRPC_PORT}. "
                        "Check firewall rules or network connectivity."
                    ),
                    FailureReason.CREDENTIALS_REJECTED: (
                        f"msfrpcd rejected credentials (user={MSFRPC_USER}). "
                        "Check MSFRPC_USER and MSFRPC_PASS environment variables."
                    ),
                    FailureReason.SSL_ERROR: (
                        f"SSL/TLS error connecting to {MSFRPC_HOST}:{MSFRPC_PORT}. "
                        "Verify MSFRPC_SSL matches msfrpcd config "
                        "(current: MSFRPC_SSL={}).".format(MSFRPC_SSL)
                    ),
                    FailureReason.COOLDOWN_ACTIVE: (
                        "Login cooldown is active after previous failed attempts. "
                        "Use msf_status(force_reconnect=True) to bypass."
                    ),
                }
                msg = messages.get(
                    reason,
                    f"Cannot connect to msfrpcd at {MSFRPC_HOST}:{MSFRPC_PORT}.",
                )
                return _error_response(
                    tool=tool_name or method,
                    reason=reason,
                    message=msg,
                    cooldown_remaining=cooldown_remaining,
                )

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
                return _error_response(
                    tool=tool_name or method,
                    reason=FailureReason.CREDENTIALS_REJECTED,
                    message="Re-authentication to msfrpcd failed after token expiry.",
                )
            return data
        except Exception as exc:
            logger.error("MSFRPC call %s failed: %s", method, exc)
            return _error_response(
                tool=tool_name or method,
                reason=FailureReason.UNKNOWN,
                message=f"RPC call failed: {exc}",
            )

    async def close(self) -> None:
        await self._client.aclose()


_rpc = MSFRPCClient()

# Background task handle for startup authentication
_startup_login_task: asyncio.Task | None = None

# Pre-flight check results (report issue #2)
_preflight_result: dict[str, Any] = {}


@asynccontextmanager
async def _lifespan(server: FastMCP):
    """FastMCP lifespan — run pre-flight checks and launch background auth."""
    global _startup_login_task, _preflight_result

    # Pre-flight check: detect msfrpcd installation and port reachability
    # (report issues #1, #2)
    msfrpcd_installed = shutil.which("msfrpcd") is not None
    msfconsole_installed = shutil.which("msfconsole") is not None
    port_reachable = False

    try:
        sock = socket.create_connection(
            (MSFRPC_HOST, MSFRPC_PORT), timeout=2,
        )
        sock.close()
        port_reachable = True
        logger.info(
            "Pre-flight: msfrpcd port %s:%d is reachable.",
            MSFRPC_HOST, MSFRPC_PORT,
        )
    except (ConnectionRefusedError, OSError, socket.timeout):
        logger.warning(
            "Pre-flight: msfrpcd port %s:%d is NOT reachable.",
            MSFRPC_HOST, MSFRPC_PORT,
        )

    _preflight_result = {
        "msfrpcd_installed": msfrpcd_installed,
        "msfconsole_installed": msfconsole_installed,
        "port_reachable": port_reachable,
    }

    if not msfrpcd_installed and not port_reachable:
        logger.warning(
            "Pre-flight: Metasploit Framework is NOT installed and msfrpcd "
            "is NOT reachable. All Metasploit tools will fail. "
            "Install with: apt-get install -y metasploit-framework, "
            "or use Docker: docker compose up metasploit-mcp"
        )
    elif not port_reachable:
        logger.warning(
            "Pre-flight: msfrpcd is NOT reachable at %s:%d. "
            "Start it with: msfrpcd -U %s -P <pass> -p %d -a %s",
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
# MCP Tools — Diagnostics (report issue #5: detailed failure info)
# ---------------------------------------------------------------------------

@mcp.tool()
async def msf_status(force_reconnect: bool = False) -> str:
    """Check msfrpcd connection status and optionally force reconnection.

    Use this tool FIRST to diagnose why other Metasploit tools are failing.
    It reports whether msfrpcd is installed, running, and authenticated.

    When force_reconnect is True, it bypasses the login cooldown and
    attempts a fresh connection with multiple retries.

    Args:
        force_reconnect: If True, clear cooldown and attempt a fresh login.
    """
    status: dict[str, Any] = {
        "msfrpcd_url": _rpc.url,
        "ssl": MSFRPC_SSL,
        "user": MSFRPC_USER,
        "authenticated": _rpc.token is not None,
    }

    # Pre-flight results (report issue #2)
    status["preflight"] = _preflight_result

    # Cooldown info
    if _rpc._last_login_failure > 0:
        elapsed = time.monotonic() - _rpc._last_login_failure
        remaining = max(0, _rpc.LOGIN_COOLDOWN - elapsed)
        status["cooldown_active"] = remaining > 0
        status["cooldown_remaining_seconds"] = round(remaining, 1)
        status["last_failure_seconds_ago"] = round(elapsed, 1)
        status["last_failure_reason"] = _rpc._last_failure_reason.value
    else:
        status["cooldown_active"] = False

    # Startup task status (report issue #9: more descriptive)
    status["startup_login_result"] = _rpc.startup_login_result
    if _startup_login_task:
        status["startup_login_task_done"] = _startup_login_task.done()

    if force_reconnect:
        logger.info("Force reconnect requested — clearing cooldown and token.")
        _rpc.token = None
        _rpc._last_login_failure = 0.0
        status["action"] = "force_reconnect"

        # Try a single login attempt first (fast check)
        result, reason = await _rpc._try_single_login()
        if result is True:
            status["reconnect_result"] = "success"
            status["authenticated"] = True
        elif result is False:
            status["reconnect_result"] = "credentials_rejected"
            status["reconnect_detail"] = reason.value
            status["authenticated"] = False
        else:
            # Connection failed — try full retry cycle (no cooldown)
            status["reconnect_detail"] = f"initial_attempt:{reason.value}"
            success = await _rpc.login(
                retries=5, delay=3, respect_cooldown=False,
            )
            status["reconnect_result"] = "success" if success else "failed"
            if not success:
                status["reconnect_detail"] = _rpc._last_failure_reason.value
            status["authenticated"] = success

    elif not _rpc.token:
        # Not authenticated — try a quick single login (non-blocking)
        result, reason = await _rpc._try_single_login()
        if result is True:
            status["quick_login"] = "success"
            status["authenticated"] = True
        elif result is False:
            status["quick_login"] = "credentials_rejected"
            status["quick_login_detail"] = reason.value
        else:
            status["quick_login"] = "msfrpcd_unreachable"
            status["quick_login_detail"] = reason.value
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
    result = await _rpc.call("module.search", search, "exploit", tool_name="list_exploits")
    if "error" in result:
        return _json(result)
    modules = result.get("modules", result.get("result", []))
    if isinstance(modules, list):
        modules = modules[:limit]
    return _json({"tool": "list_exploits", "exploits": modules, "count": len(modules)})


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
    result = await _rpc.call("module.search", query.strip(), "payload", tool_name="list_payloads")
    if "error" in result:
        return _json(result)
    modules = result.get("modules", result.get("result", []))
    if isinstance(modules, list):
        modules = modules[:limit]
    return _json({"tool": "list_payloads", "payloads": modules, "count": len(modules)})


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
        check_result = await _rpc.call("module.check", "exploit", module, options, tool_name="run_exploit")
        if "error" not in check_result:
            vuln_status = check_result.get("result", "unknown")
            if "not vulnerable" in str(vuln_status).lower():
                return _json({
                    "tool": "run_exploit",
                    "status": "not_vulnerable",
                    "check_result": vuln_status,
                    "module": module,
                })

    # Set payload if provided
    if payload:
        options["PAYLOAD"] = payload

    result = await _rpc.call("module.execute", "exploit", module, options, tool_name="run_exploit")
    return _json({"tool": "run_exploit", "module": module, "result": result})


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
    result = await _rpc.call("module.execute", "auxiliary", module, options, tool_name="run_auxiliary_module")
    return _json({"tool": "run_auxiliary_module", "module": module, "result": result})


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
    result = await _rpc.call("module.execute", "post", module, opts, tool_name="run_post_module")
    return _json({"tool": "run_post_module", "module": module, "session_id": session_id, "result": result})


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
    result = await _rpc.call("module.payload_generate", payload, options, format, tool_name="generate_payload")
    if "error" in result:
        return _json(result)
    # Payload data may be binary; return metadata
    payload_data = result.get("payload", "")
    return _json({
        "tool": "generate_payload",
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
    result = await _rpc.call("session.list", tool_name="list_sessions")
    if "error" in result:
        return _json(result)
    sessions = result if isinstance(result, dict) else {}
    # Filter out the token key if present
    sessions.pop("result", None)
    return _json({"tool": "list_sessions", "sessions": sessions, "count": len(sessions)})


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
    write_result = await _rpc.call("session.shell_write", str(session_id), command + "\n", tool_name="send_session_command")
    if "error" in write_result:
        return _json(write_result)

    # Wait and read output
    await asyncio.sleep(min(timeout, 5))
    read_result = await _rpc.call("session.shell_read", str(session_id), tool_name="send_session_command")
    return _json({
        "tool": "send_session_command",
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
    result = await _rpc.call("session.stop", str(session_id), tool_name="terminate_session")
    return _json({"tool": "terminate_session", "session_id": session_id, "result": result})


# ---------------------------------------------------------------------------
# MCP Tools — Listener / Handler Management
# ---------------------------------------------------------------------------

@mcp.tool()
async def list_listeners() -> str:
    """List all active Metasploit handlers (background jobs)."""
    result = await _rpc.call("job.list", tool_name="list_listeners")
    if "error" in result:
        return _json(result)
    return _json({"tool": "list_listeners", "jobs": result, "count": len(result)})


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
        tool_name="start_listener",
    )
    listener = {"payload": payload, "lhost": lhost, "lport": lport}
    return _json({"tool": "start_listener", "listener": listener, "result": result})


@mcp.tool()
async def stop_job(job_id: int) -> str:
    """Stop a running Metasploit background job.

    Args:
        job_id: The job ID to terminate.
    """
    result = await _rpc.call("job.stop", str(job_id), tool_name="stop_job")
    return _json({"tool": "stop_job", "job_id": job_id, "result": result})


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
    console = await _rpc.call("console.create", tool_name="msf_console_execute")
    if "error" in console:
        return _json(console)
    console_id = console.get("id", "0")

    # Write command
    await _rpc.call("console.write", console_id, command + "\n", tool_name="msf_console_execute")

    # Poll for output
    output_parts: list[str] = []
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        read = await _rpc.call("console.read", console_id, tool_name="msf_console_execute")
        data = read.get("data", "")
        if data:
            output_parts.append(data)
        busy = read.get("busy", False)
        if not busy and output_parts:
            break
        await asyncio.sleep(1)

    # Destroy console
    await _rpc.call("console.destroy", console_id, tool_name="msf_console_execute")

    return _json({
        "tool": "msf_console_execute",
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
