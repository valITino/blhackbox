"""Tests for MCP tool inventory helpers."""

from __future__ import annotations

from scripts import tool_inventory


def test_inventory_report_has_summary() -> None:
    report = tool_inventory.build_report()
    assert report["summary"]["catalog_tools"] > 0
    assert report["summary"]["kali_allowlist_tools"] > 0
    assert report["summary"]["boaz_mcp_tools"] == 5
    assert report["summary"]["hexstrike_mcp_tools"] == 151
    assert "errors" in report
    assert "warnings" in report


def test_inventory_config_checks_pass() -> None:
    report = tool_inventory.build_report()
    assert all(report["details"]["config_checks"].values())


def test_inventory_discovers_upstream_tool_counts_from_env(tmp_path, monkeypatch) -> None:
    boaz_root = tmp_path / "BOAZ-MCP_gamma"
    boaz_server = boaz_root / "boaz_mcp" / "server.py"
    boaz_server.parent.mkdir(parents=True)
    boaz_server.write_text(
        'Tool(name="alpha", description="A", inputSchema={})\n'
        'Tool(name="beta", description="B", inputSchema={})\n',
        encoding="utf-8",
    )

    hexstrike_root = tmp_path / "hexstrike-ai_gamma"
    hexstrike_root.mkdir()
    (hexstrike_root / "hexstrike_mcp.py").write_text(
        "@mcp.tool()\n"
        "def first_tool():\n"
        "    pass\n\n"
        "@mcp.tool()\n"
        "async def second_tool():\n"
        "    pass\n",
        encoding="utf-8",
    )

    monkeypatch.setenv("BOAZ_MCP_UPSTREAM_PATH", str(boaz_root))
    monkeypatch.setenv("HEXSTRIKE_UPSTREAM_PATH", str(hexstrike_root))

    report = tool_inventory.build_report()

    assert report["summary"]["boaz_mcp_tools"] == 2
    assert report["details"]["boaz_mcp_tools"] == ["alpha", "beta"]
    assert report["summary"]["hexstrike_mcp_tools"] == 2
    assert report["details"]["hexstrike_mcp_tools"] == 2
