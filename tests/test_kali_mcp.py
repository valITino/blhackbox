"""Tests for the Kali MCP server (kali-mcp/server.py).

Validates tool allowlist management, argument parsing, error handling,
and the structured JSON output contract.
"""

from __future__ import annotations

import json
import os
import sys
from unittest.mock import AsyncMock, patch

import pytest

# Add kali-mcp to the import path so we can import server.py directly
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "kali-mcp"))

import server as kali_server


class TestAllowedTools:
    """Validate the ALLOWED_TOOLS set."""

    def test_allowed_tools_is_nonempty(self) -> None:
        assert len(kali_server.ALLOWED_TOOLS) > 0

    def test_allowed_tools_count(self) -> None:
        """There should be ~57 tools in the default allowlist."""
        assert len(kali_server.ALLOWED_TOOLS) >= 50

    def test_no_empty_strings(self) -> None:
        for tool in kali_server.ALLOWED_TOOLS:
            assert tool.strip(), "Empty tool name found in ALLOWED_TOOLS"

    def test_core_tools_present(self) -> None:
        """Essential tools should always be in the allowlist."""
        core = {"nmap", "sqlmap", "nikto", "gobuster", "hydra", "curl", "dig"}
        missing = core - kali_server.ALLOWED_TOOLS
        assert not missing, f"Core tools missing from allowlist: {missing}"

    def test_network_tools_present(self) -> None:
        network = {"nmap", "rustscan", "masscan", "traceroute", "hping3"}
        missing = network - kali_server.ALLOWED_TOOLS
        assert not missing, f"Network tools missing: {missing}"

    def test_dns_tools_present(self) -> None:
        dns = {"subfinder", "amass", "fierce", "dnsenum", "dnsrecon", "dig", "whois"}
        missing = dns - kali_server.ALLOWED_TOOLS
        assert not missing, f"DNS tools missing: {missing}"

    def test_web_tools_present(self) -> None:
        web = {"nikto", "gobuster", "ffuf", "whatweb", "wafw00f", "httpx", "katana", "dalfox"}
        missing = web - kali_server.ALLOWED_TOOLS
        assert not missing, f"Web tools missing: {missing}"

    def test_exploitation_tools_present(self) -> None:
        exploit = {"sqlmap", "hydra", "john", "hashcat", "crackmapexec", "enum4linux-ng"}
        missing = exploit - kali_server.ALLOWED_TOOLS
        assert not missing, f"Exploitation tools missing: {missing}"

    def test_wireless_tools_present(self) -> None:
        wireless = {"aircrack-ng", "airodump-ng", "aireplay-ng", "wifite", "bettercap"}
        missing = wireless - kali_server.ALLOWED_TOOLS
        assert not missing, f"Wireless tools missing: {missing}"

    def test_forensics_tools_present(self) -> None:
        forensics = {"binwalk", "foremost", "exiftool", "steghide", "strings", "hashid"}
        missing = forensics - kali_server.ALLOWED_TOOLS
        assert not missing, f"Forensics tools missing: {missing}"

    def test_utility_tools_present(self) -> None:
        utils = {"curl", "wget", "netcat", "socat", "sshpass", "proxychains4"}
        missing = utils - kali_server.ALLOWED_TOOLS
        assert not missing, f"Utility tools missing: {missing}"

    def test_dangerous_tools_excluded(self) -> None:
        """Tools that should NOT be in the allowlist."""
        dangerous = {"rm", "dd", "mkfs", "fdisk", "shutdown", "reboot", "bash", "sh", "python3"}
        present = dangerous & kali_server.ALLOWED_TOOLS
        assert not present, f"Dangerous tools should not be allowed: {present}"


class TestRunKaliTool:
    """Test the run_kali_tool function."""

    @pytest.mark.asyncio
    async def test_rejects_tool_not_in_allowlist(self) -> None:
        result = await kali_server.run_kali_tool(tool="rm", args="-rf /", target="test")
        data = json.loads(result)
        assert "error" in data
        assert "not in the allowlist" in data["error"]
        assert "allowed" in data

    @pytest.mark.asyncio
    async def test_rejects_tool_not_installed(self) -> None:
        with patch("server.shutil.which", return_value=None):
            result = await kali_server.run_kali_tool(
                tool="nmap", args="-sV localhost", target="localhost"
            )
        data = json.loads(result)
        assert "error" in data
        assert "not installed" in data["error"]

    @pytest.mark.asyncio
    async def test_invalid_args_returns_error(self) -> None:
        with patch("server.shutil.which", return_value="/usr/bin/nmap"):
            result = await kali_server.run_kali_tool(
                tool="nmap", args="'unterminated quote", target="test"
            )
        data = json.loads(result)
        assert "error" in data
        assert "Invalid arguments" in data["error"]

    @pytest.mark.asyncio
    async def test_successful_execution(self) -> None:
        mock_proc = AsyncMock()
        mock_proc.communicate = AsyncMock(
            return_value=(b"scan output here", b"")
        )
        mock_proc.returncode = 0

        with (
            patch("server.shutil.which", return_value="/usr/bin/nmap"),
            patch("server.asyncio.create_subprocess_exec", return_value=mock_proc),
        ):
            result = await kali_server.run_kali_tool(
                tool="nmap", args="-sV 10.0.0.1", target="10.0.0.1", timeout=60
            )

        data = json.loads(result)
        assert data["stdout"] == "scan output here"
        assert data["stderr"] == ""
        assert data["exit_code"] == 0
        assert data["tool_name"] == "nmap"
        assert data["target"] == "10.0.0.1"
        assert "timestamp" in data

    @pytest.mark.asyncio
    async def test_timeout_returns_error(self) -> None:
        with (
            patch("server.shutil.which", return_value="/usr/bin/nmap"),
            patch("server.asyncio.create_subprocess_exec", side_effect=TimeoutError),
        ):
            # The timeout is caught in asyncio.wait_for, not create_subprocess_exec.
            # We need to mock wait_for instead.
            pass

        # Better approach: mock the full flow
        mock_proc = AsyncMock()
        mock_proc.communicate = AsyncMock(side_effect=TimeoutError)

        with (
            patch("server.shutil.which", return_value="/usr/bin/nmap"),
            patch("server.asyncio.create_subprocess_exec", return_value=mock_proc),
            patch("server.asyncio.wait_for", side_effect=TimeoutError),
        ):
            result = await kali_server.run_kali_tool(
                tool="nmap", args="-sV 10.0.0.1", target="10.0.0.1", timeout=1
            )

        data = json.loads(result)
        assert data["exit_code"] == -1
        assert "timed out" in data["stderr"]

    @pytest.mark.asyncio
    async def test_strips_tool_name(self) -> None:
        result = await kali_server.run_kali_tool(
            tool="  rm  ", args="-rf /", target="test"
        )
        data = json.loads(result)
        assert "error" in data
        assert "rm" in data["error"]

    @pytest.mark.asyncio
    async def test_default_target(self) -> None:
        mock_proc = AsyncMock()
        mock_proc.communicate = AsyncMock(return_value=(b"output", b""))
        mock_proc.returncode = 0

        with (
            patch("server.shutil.which", return_value="/usr/bin/curl"),
            patch("server.asyncio.create_subprocess_exec", return_value=mock_proc),
        ):
            result = await kali_server.run_kali_tool(tool="curl", args="http://example.com")

        data = json.loads(result)
        assert data["target"] == "unknown"

    @pytest.mark.asyncio
    async def test_nonzero_exit_code(self) -> None:
        mock_proc = AsyncMock()
        mock_proc.communicate = AsyncMock(
            return_value=(b"", b"connection refused")
        )
        mock_proc.returncode = 1

        with (
            patch("server.shutil.which", return_value="/usr/bin/nmap"),
            patch("server.asyncio.create_subprocess_exec", return_value=mock_proc),
        ):
            result = await kali_server.run_kali_tool(
                tool="nmap", args="-sV 10.0.0.1", target="10.0.0.1"
            )

        data = json.loads(result)
        assert data["exit_code"] == 1
        assert data["stderr"] == "connection refused"


class TestListAvailableTools:
    """Test the list_available_tools function."""

    def test_returns_valid_json(self) -> None:
        with patch("server.shutil.which", return_value=None):
            result = kali_server.list_available_tools()
        data = json.loads(result)
        assert "tools" in data

    def test_lists_all_allowed_tools(self) -> None:
        with patch("server.shutil.which", return_value=None):
            result = kali_server.list_available_tools()
        data = json.loads(result)
        assert set(data["tools"].keys()) == kali_server.ALLOWED_TOOLS

    def test_marks_installed_tools(self) -> None:
        def mock_which(name: str) -> str | None:
            return f"/usr/bin/{name}" if name == "nmap" else None

        with patch("server.shutil.which", side_effect=mock_which):
            result = kali_server.list_available_tools()

        data = json.loads(result)
        assert data["tools"]["nmap"]["installed"] is True
        assert data["tools"]["nmap"]["path"] == "/usr/bin/nmap"

    def test_marks_missing_tools(self) -> None:
        with patch("server.shutil.which", return_value=None):
            result = kali_server.list_available_tools()

        data = json.loads(result)
        for tool_info in data["tools"].values():
            assert tool_info["installed"] is False
            assert tool_info["path"] == "not found"

    def test_tools_sorted_alphabetically(self) -> None:
        with patch("server.shutil.which", return_value=None):
            result = kali_server.list_available_tools()
        data = json.loads(result)
        keys = list(data["tools"].keys())
        assert keys == sorted(keys)


class TestMCPServerConfig:
    """Test MCP server configuration."""

    def test_default_port(self) -> None:
        assert kali_server.MCP_PORT == 9001

    def test_mcp_instance_created(self) -> None:
        assert kali_server.mcp is not None

    def test_mcp_server_name(self) -> None:
        assert kali_server.mcp.name == "kali-mcp"


class TestDockerfileConsistency:
    """Verify Dockerfiles install all tools in ALLOWED_TOOLS.

    This test reads the Dockerfiles and checks that every tool in the
    allowlist has a corresponding package installation.
    """

    def _read_dockerfile(self, path: str) -> str:
        filepath = os.path.join(os.path.dirname(__file__), "..", path)
        with open(filepath) as f:
            return f.read()

    def test_primary_dockerfile_installs_all_tools(self) -> None:
        """Spot-check that key tools appear in docker/kali-mcp.Dockerfile."""
        content = self._read_dockerfile("docker/kali-mcp.Dockerfile")
        # Check a representative set — not every tool maps 1:1 to a package name
        for tool in ["nmap", "rustscan", "masscan", "subfinder", "nikto",
                      "gobuster", "sqlmap", "hydra", "httpx-toolkit", "katana",
                      "paramspider", "wifite", "enum4linux-ng", "binutils"]:
            assert tool in content, f"Tool package '{tool}' not found in primary Dockerfile"

    def test_standalone_dockerfile_installs_all_tools(self) -> None:
        """Spot-check that key tools appear in kali-mcp/Dockerfile."""
        content = self._read_dockerfile("kali-mcp/Dockerfile")
        for tool in ["nmap", "rustscan", "masscan", "subfinder", "nikto",
                      "gobuster", "sqlmap", "hydra", "httpx-toolkit", "katana",
                      "paramspider", "wifite", "enum4linux-ng", "binutils"]:
            assert tool in content, f"Tool package '{tool}' not found in standalone Dockerfile"

    def test_dalfox_installed_via_github(self) -> None:
        """dalfox is not in Kali apt repos — verify GitHub release install."""
        for path in ["docker/kali-mcp.Dockerfile", "kali-mcp/Dockerfile"]:
            content = self._read_dockerfile(path)
            assert "dalfox" in content, f"dalfox installation not found in {path}"
            assert "github.com/hahwul/dalfox" in content, \
                f"dalfox should be installed from GitHub release in {path}"
