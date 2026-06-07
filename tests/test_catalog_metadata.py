"""Tests for catalogue metadata conventions."""

from __future__ import annotations

from blhackbox.utils.catalog import load_tools_catalog, recommend_workflow_tools


def test_catalog_has_no_risk_gates() -> None:
    catalog = load_tools_catalog()
    assert all("risk" not in entry for entry in catalog)


def test_hexstrike_inspired_workflows_exist() -> None:
    catalog = load_tools_catalog()
    bug_bounty = recommend_workflow_tools(catalog, "bug-bounty-recon")
    wordpress = recommend_workflow_tools(catalog, "wordpress-assessment")
    ctf = recommend_workflow_tools(catalog, "ctf-enumeration")
    assert [entry["tool_name"] for entry in bug_bounty][:3] == [
        "subfinder",
        "amass",
        "httpx",
    ]
    assert "wpscan" in {entry["tool_name"] for entry in wordpress}
    assert "steghide" in {entry["tool_name"] for entry in ctf}
