"""Validate blhackbox MCP server definitions and live endpoints."""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

EXPECTED_CORE_TOOLS = {
    "run_tool",
    "query_graph",
    "get_findings",
    "list_tools",
    "search_tools",
    "get_tool_details",
    "recommend_workflow",
    "generate_report",
    "list_templates",
    "get_template",
    "aggregate_results",
    "get_payload_schema",
    "take_screenshot",
    "take_element_screenshot",
    "list_screenshots",
    "annotate_screenshot",
}


@dataclass(frozen=True)
class Endpoint:
    name: str
    url: str
    required: bool = True


LIVE_ENDPOINTS = [
    # Health probes use each server's dedicated /health route. A bare GET to
    # the Streamable HTTP endpoint (/mcp) returns HTTP 4xx, which urlopen
    # raises on — so health checks target /health (200) instead.
    Endpoint("kali-mcp", "http://localhost:9001/health"),
    Endpoint("wire-mcp", "http://localhost:9003/health"),
    Endpoint("screenshot-mcp", "http://localhost:9004/health"),
    Endpoint("mcp-gateway", "http://localhost:8080/mcp", required=False),
    Endpoint("hexstrike-api", "http://localhost:8888/health"),
    Endpoint("hexstrike-bridge", "http://localhost:9006/health"),
    Endpoint("boaz-mcp", "http://localhost:9005/health"),
]


@dataclass
class CheckResult:
    name: str
    status: str
    detail: str


def check_core_tools() -> CheckResult:
    from blhackbox.mcp.server import _TOOLS

    names = {tool.name for tool in _TOOLS}
    missing = sorted(EXPECTED_CORE_TOOLS - names)
    extra = sorted(names - EXPECTED_CORE_TOOLS)
    if missing:
        return CheckResult("core-tools", "fail", f"missing={missing}")
    if extra:
        return CheckResult("core-tools", "warn", f"extra={extra}")
    return CheckResult("core-tools", "pass", f"{len(names)} tools")


def check_catalog_search() -> CheckResult:
    from blhackbox.utils.catalog import load_tools_catalog, search_tools_catalog

    results = search_tools_catalog(load_tools_catalog(), "xss", limit=5)
    names = {entry["tool_name"] for entry in results}
    if "dalfox" not in names:
        return CheckResult("catalog-search", "fail", "expected dalfox for xss query")
    return CheckResult("catalog-search", "pass", f"results={sorted(names)}")


def check_endpoint(endpoint: Endpoint, timeout: float = 3.0) -> CheckResult:
    try:
        request = urllib.request.Request(endpoint.url, method="GET")
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return CheckResult(endpoint.name, "pass", f"HTTP {response.status} {endpoint.url}")
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        if endpoint.required:
            return CheckResult(endpoint.name, "fail", f"{endpoint.url}: {exc}")
        return CheckResult(endpoint.name, "skip", f"optional endpoint offline: {endpoint.url}")


def run_checks(live: bool) -> list[CheckResult]:
    results = [check_core_tools(), check_catalog_search()]
    if live:
        results.extend(check_endpoint(endpoint) for endpoint in LIVE_ENDPOINTS)
    else:
        results.extend(
            CheckResult(endpoint.name, "skip", f"live check disabled for {endpoint.url}")
            for endpoint in LIVE_ENDPOINTS
        )
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate blhackbox MCP servers")
    parser.add_argument("--live", action="store_true", help="Check live HTTP endpoints")
    parser.add_argument("--json", action="store_true", help="Emit JSON")
    args = parser.parse_args()

    results = run_checks(live=args.live)
    if args.json:
        print(json.dumps([asdict(result) for result in results], indent=2))
    else:
        for result in results:
            print(f"{result.status.upper():5} {result.name}: {result.detail}")

    return 1 if any(result.status == "fail" for result in results) else 0


if __name__ == "__main__":
    raise SystemExit(main())
