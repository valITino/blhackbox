"""Tests for MCP validation helpers."""

from __future__ import annotations

from scripts.check_mcp_servers import check_catalog_search, check_core_tools, run_checks


def test_core_tool_check_passes() -> None:
    result = check_core_tools()
    assert result.status == "pass"


def test_catalog_search_check_passes() -> None:
    result = check_catalog_search()
    assert result.status == "pass"


def test_run_checks_static_skips_live() -> None:
    results = run_checks(live=False)
    statuses = {result.name: result.status for result in results}
    assert statuses["core-tools"] == "pass"
    assert statuses["catalog-search"] == "pass"
    assert statuses["kali-mcp"] == "skip"
    assert statuses["hexstrike-bridge"] == "skip"
    assert statuses["boaz-mcp"] == "skip"
