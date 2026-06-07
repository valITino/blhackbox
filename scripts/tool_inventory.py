"""Inventory blhackbox MCP tool/catalog consistency.

The report intentionally separates hard errors from review warnings so it can be
used both in CI and during local Docker/MCP maintenance.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CATALOG_PATH = ROOT / "blhackbox" / "data" / "tools_catalog.json"
KALI_SERVER_PATH = ROOT / "kali-mcp" / "server.py"
DOCKERFILE_PATH = ROOT / "docker" / "kali-mcp.Dockerfile"
WIRE_SERVER_PATH = ROOT / "wire-mcp" / "server.py"
SCREENSHOT_SERVER_PATH = ROOT / "screenshot-mcp" / "server.py"
BOAZ_SERVER_PATH = ROOT / "boaz-mcp" / "server.py"
HEXSTRIKE_BRIDGE_PATH = ROOT / "hexstrike-mcp" / "server.py"
BOAZ_FALLBACK_TOOLS = {
    "generate_payload",
    "list_loaders",
    "list_encoders",
    "analyze_binary",
    "validate_options",
}
HEXSTRIKE_FALLBACK_TOOL_COUNT = 151
MCP_JSON_PATH = ROOT / "blhackbox-mcp.json"
MCP_CATALOG_PATH = ROOT / "blhackbox-mcp-catalog.yaml"

ALIASES = {
    "metasploit": {"msfconsole", "msfvenom", "metasploit-framework"},
    "msfvenom": {"metasploit-framework"},
    "httpx": {"httpx-toolkit"},
    "tshark": {"capture_packets", "read_pcap", "list_interfaces"},
}

EXTERNAL_BINARY_INSTALLS = {"dalfox", "katana", "rustscan"}


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_catalog() -> list[dict[str, Any]]:
    catalog: list[dict[str, Any]] = load_json(CATALOG_PATH)
    return catalog


def _load_module(path: Path, module_name: str) -> Any:
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load module from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_kali_allowlist() -> set[str]:
    module = _load_module(KALI_SERVER_PATH, "blhackbox_kali_inventory")
    return set(module.ALLOWED_TOOLS)


def discover_fastmcp_tools(path: Path) -> set[str]:
    source = path.read_text(encoding="utf-8")
    pattern = re.compile(r"@mcp\.tool\(\)\s*(?:async\s+)?def\s+([a-zA-Z_][a-zA-Z0-9_]*)")
    return set(pattern.findall(source))


def _first_existing_path(env_names: tuple[str, ...], candidates: tuple[Path, ...]) -> Path | None:
    for env_name in env_names:
        configured = os.environ.get(env_name)
        if configured:
            path = Path(configured).expanduser()
            if path.exists():
                return path
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def discover_boaz_upstream_tools() -> set[str]:
    """Discover BOAZ-MCP Gamma tools from a local upstream checkout when available."""

    upstream = _first_existing_path(
        ("BOAZ_MCP_UPSTREAM_PATH", "BOAZ_MCP_PATH"),
        (ROOT / "BOAZ-MCP_gamma", ROOT.parent / "BOAZ-MCP_gamma"),
    )
    if upstream is None:
        return set(BOAZ_FALLBACK_TOOLS)

    server_path = upstream / "boaz_mcp" / "server.py"
    if not server_path.exists():
        return set(BOAZ_FALLBACK_TOOLS)

    source = server_path.read_text(encoding="utf-8")
    tools = set(re.findall(r"Tool\(\s*name=[\"']([^\"']+)[\"']", source))
    return tools or set(BOAZ_FALLBACK_TOOLS)


def discover_hexstrike_upstream_tool_count() -> int:
    """Discover HexStrike Gamma MCP tool count from a local upstream checkout."""

    upstream = _first_existing_path(
        ("HEXSTRIKE_UPSTREAM_PATH", "HEXSTRIKE_PATH"),
        (ROOT / "hexstrike-ai_gamma", ROOT.parent / "hexstrike-ai_gamma"),
    )
    if upstream is None:
        return HEXSTRIKE_FALLBACK_TOOL_COUNT

    mcp_path = upstream / "hexstrike_mcp.py"
    if not mcp_path.exists():
        return HEXSTRIKE_FALLBACK_TOOL_COUNT

    tools = discover_fastmcp_tools(mcp_path)
    return len(tools) or HEXSTRIKE_FALLBACK_TOOL_COUNT


def parse_docker_packages() -> set[str]:
    packages: set[str] = set()
    in_install = False
    for raw_line in DOCKERFILE_PATH.read_text(encoding="utf-8").splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if "apt-get install" in line:
            in_install = True
            continue
        if not in_install:
            continue
        if line.startswith("&&") or line.startswith("RUN ") or not line:
            if line.startswith("&&"):
                break
            continue
        token = line.rstrip("\\").strip()
        if token and not token.startswith("-"):
            packages.add(token)
    return packages


def inspect_configs() -> dict[str, bool]:
    mcp_json = MCP_JSON_PATH.read_text(encoding="utf-8")
    catalog_yaml = MCP_CATALOG_PATH.read_text(encoding="utf-8")
    return {
        "kali_json": "9001" in mcp_json and "kali" in mcp_json,
        "wire_json": "wireshark" in mcp_json or "wire" in mcp_json,
        "screenshot_json": "9004" in mcp_json and "screenshot" in mcp_json,
        "gateway_catalog_kali": "kali-mcp" in catalog_yaml and "9001" in catalog_yaml,
        "gateway_catalog_wire": "wire-mcp" in catalog_yaml and "9003" in catalog_yaml,
        "gateway_catalog_screenshot": "screenshot-mcp" in catalog_yaml and "9004" in catalog_yaml,
        "hexstrike_json": "hexstrike" in mcp_json and "9006" in mcp_json,
        "boaz_json": "boaz" in mcp_json and "9005" in mcp_json,
        "gateway_catalog_hexstrike": (
            "hexstrike-bridge-mcp" in catalog_yaml and "9006" in catalog_yaml
        ),
        "gateway_catalog_boaz": "boaz-mcp" in catalog_yaml and "9005" in catalog_yaml,
    }


def build_report() -> dict[str, Any]:
    catalog = load_catalog()
    catalog_names = {entry["tool_name"] for entry in catalog}
    kali_catalog = {entry["tool_name"] for entry in catalog if entry.get("backend") == "kali-mcp"}
    screenshot_catalog = {
        entry["tool_name"] for entry in catalog if entry.get("backend") == "screenshot-mcp"
    }
    wire_catalog = {entry["tool_name"] for entry in catalog if entry.get("backend") == "wire-mcp"}

    kali_allowlist = load_kali_allowlist()
    wire_tools = discover_fastmcp_tools(WIRE_SERVER_PATH)
    screenshot_tools = discover_fastmcp_tools(SCREENSHOT_SERVER_PATH)
    boaz_tools = discover_boaz_upstream_tools()
    hexstrike_mcp_tools = discover_hexstrike_upstream_tool_count()
    docker_packages = parse_docker_packages()
    config_checks = inspect_configs()

    effective_kali = set(kali_allowlist)
    for catalog_name, aliases in ALIASES.items():
        if aliases & kali_allowlist:
            effective_kali.add(catalog_name)

    warnings: list[str] = []
    errors: list[str] = []

    missing_kali = sorted(kali_catalog - effective_kali)
    if missing_kali:
        warnings.append(f"Kali catalogue entries not in allowlist/aliases: {missing_kali}")

    missing_wire = sorted(wire_catalog - wire_tools - {"tshark"})
    if missing_wire:
        warnings.append(f"WireMCP catalogue entries not exposed as tools: {missing_wire}")

    missing_screenshot = sorted(screenshot_catalog - screenshot_tools)
    if missing_screenshot:
        warnings.append(
            f"Screenshot catalogue entries not exposed as tools: {missing_screenshot}"
        )

    if not all(config_checks.values()):
        failed = sorted(name for name, passed in config_checks.items() if not passed)
        errors.append(f"MCP config checks failed: {failed}")

    effective_packages = set(docker_packages) | set(EXTERNAL_BINARY_INSTALLS)
    for tool, aliases in ALIASES.items():
        if aliases & docker_packages:
            effective_packages.add(tool)

    likely_missing_packages = sorted(
        tool for tool in kali_catalog if tool in kali_allowlist and tool not in effective_packages
    )

    return {
        "summary": {
            "catalog_tools": len(catalog_names),
            "kali_allowlist_tools": len(kali_allowlist),
            "wire_tools": len(wire_tools),
            "screenshot_tools": len(screenshot_tools),
            "boaz_mcp_tools": len(boaz_tools),
            "hexstrike_mcp_tools": hexstrike_mcp_tools,
            "docker_packages": len(docker_packages),
        },
        "warnings": warnings,
        "errors": errors,
        "details": {
            "config_checks": config_checks,
            "likely_missing_docker_packages": likely_missing_packages,
            "wire_tools": sorted(wire_tools),
            "screenshot_tools": sorted(screenshot_tools),
            "boaz_mcp_tools": sorted(boaz_tools),
            "hexstrike_mcp_tools": hexstrike_mcp_tools,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Check MCP tool/catalog consistency")
    parser.add_argument("--json", action="store_true", help="Emit JSON report")
    parser.add_argument("--strict", action="store_true", help="Treat warnings as failures")
    args = parser.parse_args()

    report = build_report()
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print("blhackbox MCP tool inventory")
        for key, value in report["summary"].items():
            print(f"- {key}: {value}")
        for warning in report["warnings"]:
            print(f"WARNING: {warning}")
        for error in report["errors"]:
            print(f"ERROR: {error}")

    if report["errors"] or (args.strict and report["warnings"]):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
