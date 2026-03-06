"""WireMCP Server for blhackbox.

Provides MCP tool access to Wireshark/tshark for packet capture and
network traffic analysis.  Inspired by 0xKoda/WireMCP and
khuynh22/mcp-wireshark.

Exposes 7 tools for network traffic analysis:
  - capture_packets     — live packet capture with tshark
  - read_pcap           — parse an existing .pcap file
  - get_conversations   — extract network conversations
  - get_statistics      — protocol hierarchy and endpoint stats
  - extract_credentials — find cleartext credentials in traffic
  - follow_stream       — reconstruct a TCP/UDP stream
  - list_interfaces     — list available capture interfaces

Transport: FastMCP SSE on port 9003.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import shutil
from datetime import UTC, datetime
from pathlib import Path

from mcp.server.fastmcp import FastMCP

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("wire-mcp")

MCP_PORT = int(os.environ.get("MCP_PORT", "9003"))
CAPTURE_DIR = Path(os.environ.get("CAPTURE_DIR", "/tmp/captures"))
CAPTURE_DIR.mkdir(parents=True, exist_ok=True)

mcp = FastMCP("wire-mcp", host="0.0.0.0", port=MCP_PORT)


async def _run_tshark(args: list[str], timeout: int = 60) -> dict:
    """Run a tshark command and return structured output."""
    tshark = shutil.which("tshark")
    if not tshark:
        return {"error": "tshark is not installed in this container"}

    cmd = [tshark] + args
    logger.info("Executing: %s (timeout: %ds)", " ".join(cmd), timeout)

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout_bytes, stderr_bytes = await asyncio.wait_for(
            proc.communicate(), timeout=timeout,
        )
        return {
            "stdout": stdout_bytes.decode("utf-8", errors="replace"),
            "stderr": stderr_bytes.decode("utf-8", errors="replace"),
            "exit_code": proc.returncode or 0,
        }
    except TimeoutError:
        if proc.returncode is None:
            proc.kill()
        return {"stdout": "", "stderr": f"Timed out after {timeout}s", "exit_code": -1}
    except Exception as exc:
        return {"stdout": "", "stderr": str(exc), "exit_code": -1}


def _json(data: object) -> str:
    return json.dumps(data, indent=2, default=str)


# ---------------------------------------------------------------------------
# MCP Tools
# ---------------------------------------------------------------------------

@mcp.tool()
async def capture_packets(
    interface: str = "any",
    count: int = 100,
    filter: str = "",
    duration: int = 30,
    output_file: str = "",
) -> str:
    """Capture live network packets using tshark.

    Args:
        interface: Network interface to capture on (default 'any').
        count: Maximum number of packets to capture (default 100).
        filter: BPF capture filter (e.g. 'tcp port 80', 'host 10.0.0.1').
        duration: Maximum capture duration in seconds (default 30).
        output_file: If provided, save pcap to this filename in /tmp/captures/.
    """
    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")

    args = ["-i", interface, "-c", str(count), "-a", f"duration:{duration}"]

    if filter:
        args.extend(["-f", filter])

    # Save pcap if requested
    pcap_path = ""
    if output_file:
        pcap_path = str(CAPTURE_DIR / output_file)
    else:
        pcap_path = str(CAPTURE_DIR / f"capture_{timestamp}.pcap")

    args.extend(["-w", pcap_path])

    # Also get text summary
    result = await _run_tshark(args, timeout=duration + 10)
    if result.get("exit_code", -1) != 0 and "error" in result:
        return _json(result)

    # Read the captured file for summary
    summary_args = ["-r", pcap_path, "-q", "-z", "io,stat,0"]
    summary = await _run_tshark(summary_args, timeout=30)

    return _json({
        "pcap_file": pcap_path,
        "interface": interface,
        "filter": filter,
        "capture_output": result.get("stderr", ""),
        "statistics": summary.get("stdout", ""),
        "timestamp": timestamp,
    })


@mcp.tool()
async def read_pcap(
    file_path: str,
    display_filter: str = "",
    max_packets: int = 200,
    fields: str = "",
) -> str:
    """Read and parse an existing pcap file.

    Args:
        file_path: Path to the .pcap or .pcapng file.
        display_filter: Wireshark display filter (e.g. 'http', 'dns', 'tcp.flags.syn==1').
        max_packets: Maximum packets to display (default 200).
        fields: Comma-separated tshark fields to extract (e.g. 'ip.src,ip.dst,tcp.port').
    """
    if not Path(file_path).exists():
        return _json({"error": f"File not found: {file_path}"})

    args = ["-r", file_path, "-c", str(max_packets)]

    if display_filter:
        args.extend(["-Y", display_filter])

    if fields:
        args.extend(["-T", "fields"])
        for field in fields.split(","):
            args.extend(["-e", field.strip()])
        args.extend(["-E", "header=y", "-E", "separator=\t"])

    result = await _run_tshark(args, timeout=60)
    return _json({
        "file": file_path,
        "display_filter": display_filter,
        "output": result.get("stdout", ""),
        "stderr": result.get("stderr", ""),
        "exit_code": result.get("exit_code", -1),
    })


@mcp.tool()
async def get_conversations(
    file_path: str,
    conversation_type: str = "tcp",
) -> str:
    """Extract network conversations from a pcap file.

    Args:
        file_path: Path to the .pcap file.
        conversation_type: Type of conversations: tcp, udp, ip, ethernet (default tcp).
    """
    if not Path(file_path).exists():
        return _json({"error": f"File not found: {file_path}"})

    valid_types = {"tcp", "udp", "ip", "ethernet"}
    if conversation_type not in valid_types:
        return _json({"error": f"Invalid type. Use: {', '.join(valid_types)}"})

    args = ["-r", file_path, "-q", "-z", f"conv,{conversation_type}"]
    result = await _run_tshark(args, timeout=60)
    return _json({
        "file": file_path,
        "conversation_type": conversation_type,
        "conversations": result.get("stdout", ""),
        "exit_code": result.get("exit_code", -1),
    })


@mcp.tool()
async def get_statistics(
    file_path: str,
    stat_type: str = "protocol_hierarchy",
) -> str:
    """Get statistical analysis of a pcap file.

    Args:
        file_path: Path to the .pcap file.
        stat_type: Type of statistics: protocol_hierarchy, endpoints,
            io_graph (default protocol_hierarchy).
    """
    if not Path(file_path).exists():
        return _json({"error": f"File not found: {file_path}"})

    stat_flags = {
        "protocol_hierarchy": ["-q", "-z", "io,phs"],
        "endpoints": ["-q", "-z", "endpoints,ip"],
        "io_graph": ["-q", "-z", "io,stat,1"],
    }

    flags = stat_flags.get(stat_type)
    if not flags:
        return _json({"error": f"Invalid stat_type. Use: {', '.join(stat_flags)}"})

    args = ["-r", file_path] + flags
    result = await _run_tshark(args, timeout=60)
    return _json({
        "file": file_path,
        "stat_type": stat_type,
        "statistics": result.get("stdout", ""),
        "exit_code": result.get("exit_code", -1),
    })


@mcp.tool()
async def extract_credentials(
    file_path: str,
) -> str:
    """Extract potential cleartext credentials from a pcap file.

    Searches for HTTP basic auth, FTP credentials, SMTP auth, and other
    cleartext authentication protocols.

    Args:
        file_path: Path to the .pcap file.
    """
    if not Path(file_path).exists():
        return _json({"error": f"File not found: {file_path}"})

    results: dict[str, str] = {}

    # HTTP Basic Auth
    http_args = [
        "-r", file_path, "-Y", "http.authorization",
        "-T", "fields", "-e", "ip.src", "-e", "ip.dst",
        "-e", "http.authorization",
    ]
    http_result = await _run_tshark(http_args, timeout=30)
    results["http_auth"] = http_result.get("stdout", "").strip()

    # FTP credentials
    ftp_args = [
        "-r", file_path, "-Y", "ftp.request.command == USER || ftp.request.command == PASS",
        "-T", "fields", "-e", "ip.src", "-e", "ip.dst",
        "-e", "ftp.request.command", "-e", "ftp.request.arg",
    ]
    ftp_result = await _run_tshark(ftp_args, timeout=30)
    results["ftp_credentials"] = ftp_result.get("stdout", "").strip()

    # SMTP auth
    smtp_args = [
        "-r", file_path, "-Y", "smtp.req.command == AUTH",
        "-T", "fields", "-e", "ip.src", "-e", "ip.dst",
        "-e", "smtp.req.command", "-e", "smtp.req.parameter",
    ]
    smtp_result = await _run_tshark(smtp_args, timeout=30)
    results["smtp_auth"] = smtp_result.get("stdout", "").strip()

    # Telnet data
    telnet_args = [
        "-r", file_path, "-Y", "telnet.data",
        "-T", "fields", "-e", "ip.src", "-e", "ip.dst",
        "-e", "telnet.data",
    ]
    telnet_result = await _run_tshark(telnet_args, timeout=30)
    results["telnet_data"] = telnet_result.get("stdout", "").strip()

    has_findings = any(v for v in results.values())
    return _json({
        "file": file_path,
        "credentials_found": has_findings,
        "findings": results,
    })


@mcp.tool()
async def follow_stream(
    file_path: str,
    stream_type: str = "tcp",
    stream_index: int = 0,
) -> str:
    """Reconstruct and follow a TCP or UDP stream from a pcap file.

    Args:
        file_path: Path to the .pcap file.
        stream_type: Stream type: tcp or udp (default tcp).
        stream_index: Stream index number (default 0, the first stream).
    """
    if not Path(file_path).exists():
        return _json({"error": f"File not found: {file_path}"})

    if stream_type not in {"tcp", "udp"}:
        return _json({"error": "stream_type must be 'tcp' or 'udp'"})

    args = [
        "-r", file_path,
        "-q", "-z", f"follow,{stream_type},ascii,{stream_index}",
    ]
    result = await _run_tshark(args, timeout=60)
    return _json({
        "file": file_path,
        "stream_type": stream_type,
        "stream_index": stream_index,
        "stream_data": result.get("stdout", ""),
        "exit_code": result.get("exit_code", -1),
    })


@mcp.tool()
async def list_interfaces() -> str:
    """List available network interfaces for packet capture."""
    result = await _run_tshark(["-D"], timeout=10)
    return _json({
        "interfaces": result.get("stdout", "").strip(),
        "exit_code": result.get("exit_code", -1),
    })


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    transport = os.environ.get("MCP_TRANSPORT", "sse")
    logger.info(
        "Starting WireMCP Server (%s on port %d)",
        transport, MCP_PORT,
    )
    mcp.run(transport=transport)
