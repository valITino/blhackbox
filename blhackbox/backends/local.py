"""Local CLI backend – execute security tools directly via subprocess."""

from __future__ import annotations

import asyncio
import logging
import shutil
from typing import Any

from blhackbox.backends.base import ToolBackend, ToolResult

logger = logging.getLogger("blhackbox.backends.local")

# Maps (category, tool) → command builder.
# Each builder returns (executable, [args]) from the user-supplied params.
_TOOL_COMMANDS: dict[str, dict[str, Any]] = {
    "nmap": {
        "bin": "nmap",
        "build": lambda p: _nmap_args(p),
    },
    "subfinder": {
        "bin": "subfinder",
        "build": lambda p: ["-d", p.get("domain", p.get("target", ""))],
    },
    "amass": {
        "bin": "amass",
        "build": lambda p: [
            "enum", "-passive", "-d",
            p.get("domain", p.get("target", "")),
        ],
    },
    "fierce": {
        "bin": "fierce",
        "build": lambda p: [
            "--domain", p.get("domain", p.get("target", "")),
        ],
    },
    "dnsenum": {
        "bin": "dnsenum",
        "build": lambda p: [p.get("domain", p.get("target", ""))],
    },
    "httpx": {
        "bin": "httpx",
        "build": lambda p: _httpx_args(p),
    },
    "nuclei": {
        "bin": "nuclei",
        "build": lambda p: ["-u", p.get("target", ""), "-silent"],
    },
    "ffuf": {
        "bin": "ffuf",
        "build": lambda p: _ffuf_args(p),
    },
    "gobuster": {
        "bin": "gobuster",
        "build": lambda p: _gobuster_args(p),
    },
    "nikto": {
        "bin": "nikto",
        "build": lambda p: ["-h", p.get("target", p.get("url", ""))],
    },
    "rustscan": {
        "bin": "rustscan",
        "build": lambda p: ["-a", p.get("target", "")],
    },
    "masscan": {
        "bin": "masscan",
        "build": lambda p: [
            p.get("target", ""),
            "-p", p.get("ports", "1-1000"),
            "--rate", str(p.get("rate", 1000)),
        ],
    },
    "dirsearch": {
        "bin": "dirsearch",
        "build": lambda p: ["-u", p.get("url", p.get("target", ""))],
    },
    "katana": {
        "bin": "katana",
        "build": lambda p: ["-u", p.get("url", p.get("target", ""))],
    },
    "wafw00f": {
        "bin": "wafw00f",
        "build": lambda p: [p.get("url", p.get("target", ""))],
    },
}

# Timeout in seconds for individual tool execution
_DEFAULT_TIMEOUT = 300


def _nmap_args(p: dict[str, Any]) -> list[str]:
    args: list[str] = []
    scan_type = p.get("scan_type")
    if scan_type:
        args.append(f"-{scan_type}")
    else:
        args.extend(["-sV", "-sC"])
    ports = p.get("ports")
    if ports:
        args.extend(["-p", str(ports)])
    args.append(p.get("target", ""))
    return args


def _httpx_args(p: dict[str, Any]) -> list[str]:
    target = p.get("target", "")
    args = ["-u", target, "-silent", "-status-code", "-title", "-tech-detect"]
    return args


def _ffuf_args(p: dict[str, Any]) -> list[str]:
    url = p.get("url", p.get("target", ""))
    wordlist = p.get("wordlist", "/usr/share/wordlists/dirb/common.txt")
    return ["-u", url, "-w", wordlist, "-mc", "200,301,302,403"]


def _gobuster_args(p: dict[str, Any]) -> list[str]:
    url = p.get("url", p.get("target", ""))
    wordlist = p.get("wordlist", "/usr/share/wordlists/dirb/common.txt")
    return ["dir", "-u", url, "-w", wordlist, "-q"]


class LocalBackend(ToolBackend):
    """Execute security tools directly on the local system via subprocess."""

    name = "local"

    async def connect(self) -> None:
        pass  # Nothing to initialise

    async def close(self) -> None:
        pass

    async def health_check(self) -> bool:
        # Check if at least one core tool is installed
        return shutil.which("nmap") is not None

    async def run_tool(
        self,
        category: str,
        tool: str,
        params: dict[str, Any] | None = None,
    ) -> ToolResult:
        params = params or {}
        spec = _TOOL_COMMANDS.get(tool)
        if spec is None:
            return ToolResult(
                success=False,
                tool=f"{category}/{tool}",
                category=category,
                output="",
                errors=[f"Tool '{tool}' is not supported by the local backend"],
            )

        binary = spec["bin"]
        if shutil.which(binary) is None:
            return ToolResult(
                success=False,
                tool=f"{category}/{tool}",
                category=category,
                output="",
                errors=[f"'{binary}' not found on PATH"],
            )

        args = spec["build"](params)
        cmd = [binary, *args]
        logger.info("Local exec: %s", " ".join(cmd))

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(),
                timeout=params.get("timeout", _DEFAULT_TIMEOUT),
            )
        except TimeoutError:
            return ToolResult(
                success=False,
                tool=f"{category}/{tool}",
                category=category,
                output="",
                errors=[f"Timeout after {_DEFAULT_TIMEOUT}s"],
            )
        except OSError as exc:
            return ToolResult(
                success=False,
                tool=f"{category}/{tool}",
                category=category,
                output="",
                errors=[str(exc)],
            )

        stdout_text = stdout.decode("utf-8", errors="replace")
        stderr_text = stderr.decode("utf-8", errors="replace")
        errors: list[str] = []
        if stderr_text.strip():
            errors.append(stderr_text.strip())

        return ToolResult(
            success=proc.returncode == 0,
            tool=f"{category}/{tool}",
            category=category,
            output=stdout_text,
            errors=errors,
            raw_data={
                "stdout": stdout_text,
                "stderr": stderr_text,
                "returncode": proc.returncode,
                "command": " ".join(cmd),
            },
        )

    async def list_tools(self) -> list[dict[str, str]]:
        available: list[dict[str, str]] = []
        for tool_name, spec in _TOOL_COMMANDS.items():
            if shutil.which(spec["bin"]):
                # Infer category from the tool map
                available.append({"category": "local", "tool": tool_name})
        return available
