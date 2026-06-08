"""Tool catalogue loader and helpers."""

from __future__ import annotations

import json
from importlib import resources
from typing import Any

_SEARCH_FIELDS = ("tool_name", "category", "description", "phase", "backend", "tags")


def load_tools_catalog() -> list[dict[str, Any]]:
    """Load the tools catalogue from the bundled JSON file.

    Returns catalogue entries with at least: category, tool_name,
    description, and phase. Newer entries may also include backend,
    tags and example_params metadata.
    """
    ref = resources.files("blhackbox.data").joinpath("tools_catalog.json")
    text = ref.read_text(encoding="utf-8")
    catalog: list[dict[str, Any]] = json.loads(text)
    return catalog


def catalog_to_tool_list_string(catalog: list[dict[str, Any]]) -> str:
    """Format the catalogue as a readable string for the LLM planner.

    Groups tools by category, matching the format the planner expects.
    """
    groups: dict[str, list[dict[str, Any]]] = {}
    for entry in catalog:
        cat = entry.get("category", "other")
        groups.setdefault(cat, []).append(entry)

    lines: list[str] = []
    for category, tools in groups.items():
        label = category.replace("_", " ").title()
        lines.append(f"{label}:")
        for tool in tools:
            backend = tool.get("backend", "kali-mcp")
            lines.append(
                f"  - {tool['tool_name']}: {tool['description']} "
                f"(phase={tool.get('phase', 'active')}, backend={backend})"
            )
        lines.append("")

    return "\n".join(lines)


def resolve_tool_names(
    catalog: list[dict[str, Any]],
    names: list[str],
) -> list[dict[str, str]]:
    """Resolve a list of tool names (or category names) to (category, tool_name) pairs.

    Accepts both exact tool names (e.g. 'nmap') and category names (e.g. 'dns'),
    which expand to all tools in that category.

    Raises ValueError if a name cannot be resolved.
    """
    by_tool: dict[str, dict[str, str]] = {}
    by_category: dict[str, list[dict[str, str]]] = {}
    for entry in catalog:
        key = {"category": entry["category"], "tool_name": entry["tool_name"]}
        by_tool[entry["tool_name"]] = key
        by_category.setdefault(entry["category"], []).append(key)

    resolved: list[dict[str, str]] = []
    seen: set[str] = set()

    for name in names:
        name_lower = name.strip().lower()
        if name_lower in by_tool:
            tool_key = f"{by_tool[name_lower]['category']}/{by_tool[name_lower]['tool_name']}"
            if tool_key not in seen:
                resolved.append(by_tool[name_lower])
                seen.add(tool_key)
        elif name_lower in by_category:
            for entry in by_category[name_lower]:
                tool_key = f"{entry['category']}/{entry['tool_name']}"
                if tool_key not in seen:
                    resolved.append(entry)
                    seen.add(tool_key)
        else:
            raise ValueError(
                f"Unknown tool or category: {name!r}. "
                f"Run 'blhackbox catalog' to see available tools."
            )

    return resolved


def get_full_pentest_order(catalog: list[dict[str, Any]]) -> list[dict[str, str]]:
    """Return all tools from the catalogue in a sensible execution order.

    Passive tools first (dns, intelligence), then active (network, web).
    """
    phase_order = {"passive": 0, "active": 1}
    sorted_catalog = sorted(
        catalog,
        key=lambda e: phase_order.get(e.get("phase", "active"), 1),
    )
    return [
        {"category": e["category"], "tool_name": e["tool_name"]}
        for e in sorted_catalog
    ]


def _field_text(value: Any) -> str:
    if isinstance(value, list):
        return " ".join(str(item) for item in value)
    if isinstance(value, dict):
        return " ".join(f"{key} {val}" for key, val in value.items())
    return str(value or "")


def _score_entry(entry: dict[str, Any], terms: list[str]) -> int:
    score = 0
    tool_name = entry.get("tool_name", "").lower()
    category = entry.get("category", "").lower()
    tags = {str(tag).lower() for tag in entry.get("tags", [])}
    haystack = " ".join(_field_text(entry.get(field)) for field in _SEARCH_FIELDS).lower()

    for term in terms:
        if term == tool_name:
            score += 10
        if term == category:
            score += 6
        if term in tags:
            score += 5
        if term in haystack:
            score += 2
    return score


def search_tools_catalog(
    catalog: list[dict[str, Any]],
    query: str,
    *,
    limit: int = 10,
    phase: str | None = None,
    category: str | None = None,
) -> list[dict[str, Any]]:
    """Search the tool catalogue with lightweight relevance scoring.

    This provides a compact discovery layer for MCP clients so they do not need
    to load the full tool catalogue into context before choosing tools.
    """
    terms = [term.lower() for term in query.split() if term.strip()]
    limit = max(1, min(limit, 50))

    candidates: list[tuple[int, dict[str, Any]]] = []
    for entry in catalog:
        if phase and entry.get("phase") != phase:
            continue
        if category and entry.get("category") != category:
            continue
        score = _score_entry(entry, terms) if terms else 1
        if score > 0:
            candidates.append((score, entry))

    candidates.sort(
        key=lambda item: (
            -item[0],
            item[1].get("category", ""),
            item[1].get("tool_name", ""),
        )
    )
    return [entry for _, entry in candidates[:limit]]


def get_tool_details(catalog: list[dict[str, Any]], tool_name: str) -> dict[str, Any]:
    """Return full metadata for a single tool by exact name."""
    wanted = tool_name.strip().lower()
    for entry in catalog:
        if entry.get("tool_name", "").lower() == wanted:
            return entry
    raise ValueError(f"Unknown tool: {tool_name!r}")


_WORKFLOW_PROFILES: dict[str, list[str]] = {
    "quick-scan": ["subfinder", "httpx", "nmap", "nuclei", "take_screenshot"],
    "recon-deep": ["subfinder", "amass", "dnsrecon", "theharvester", "httpx", "katana"],
    "web-app-assessment": [
        "httpx",
        "whatweb",
        "wafw00f",
        "katana",
        "ffuf",
        "nuclei",
        "nikto",
        "sqlmap",
        "dalfox",
    ],
    "network-infrastructure": [
        "nmap",
        "rustscan",
        "masscan",
        "enum4linux-ng",
        "netexec",
        "hydra",
    ],
    "api-security": ["httpx", "katana", "arjun", "ffuf", "nuclei", "sqlmap"],
    "osint-gathering": ["theharvester", "subfinder", "amass", "whois", "exiftool"],
    "forensics-triage": ["exiftool", "binwalk", "foremost", "steghide"],
    "bug-bounty-recon": [
        "subfinder",
        "amass",
        "httpx",
        "katana",
        "paramspider",
        "nuclei",
        "take_screenshot",
    ],
    "wordpress-assessment": ["httpx", "whatweb", "wpscan", "ffuf", "nuclei", "nikto"],
    "api-recon": ["httpx", "katana", "arjun", "ffuf", "nuclei", "sqlmap"],
    "internal-network": ["arp-scan", "rustscan", "nmap", "enum4linux-ng", "netexec"],
    "ctf-enumeration": ["nmap", "gobuster", "ffuf", "binwalk", "exiftool", "steghide"],
}


def recommend_workflow_tools(
    catalog: list[dict[str, Any]],
    workflow: str,
) -> list[dict[str, Any]]:
    """Return ordered catalogue entries for a named workflow profile."""
    names = _WORKFLOW_PROFILES.get(workflow)
    if names is None:
        known = ", ".join(sorted(_WORKFLOW_PROFILES))
        raise ValueError(f"Unknown workflow: {workflow!r}. Known workflows: {known}")

    by_name = {entry["tool_name"]: entry for entry in catalog}
    return [by_name[name] for name in names if name in by_name]
