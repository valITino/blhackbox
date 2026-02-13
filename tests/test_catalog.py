"""Tests for the tools catalogue utilities."""

from __future__ import annotations

import pytest

from blhackbox.utils.catalog import (
    catalog_to_tool_list_string,
    get_full_pentest_order,
    load_tools_catalog,
    resolve_tool_names,
)


class TestLoadToolsCatalog:
    def test_returns_list(self) -> None:
        catalog = load_tools_catalog()
        assert isinstance(catalog, list)
        assert len(catalog) > 0

    def test_entries_have_required_keys(self) -> None:
        catalog = load_tools_catalog()
        for entry in catalog:
            assert "category" in entry
            assert "tool_name" in entry
            assert "description" in entry

    def test_known_tool_present(self) -> None:
        catalog = load_tools_catalog()
        names = [e["tool_name"] for e in catalog]
        assert "nmap" in names
        assert "nuclei" in names
        assert "subfinder" in names


class TestCatalogToToolListString:
    def test_contains_tools(self) -> None:
        catalog = load_tools_catalog()
        text = catalog_to_tool_list_string(catalog)
        assert "nmap" in text
        assert "nuclei" in text

    def test_groups_by_category(self) -> None:
        catalog = load_tools_catalog()
        text = catalog_to_tool_list_string(catalog)
        assert "Network:" in text
        assert "Web:" in text


class TestResolveToolNames:
    def test_resolve_by_tool_name(self) -> None:
        catalog = load_tools_catalog()
        result = resolve_tool_names(catalog, ["nmap"])
        assert len(result) == 1
        assert result[0]["tool_name"] == "nmap"
        assert result[0]["category"] == "network"

    def test_resolve_by_category(self) -> None:
        catalog = load_tools_catalog()
        result = resolve_tool_names(catalog, ["dns"])
        dns_tools = [e for e in catalog if e["category"] == "dns"]
        assert len(result) == len(dns_tools)

    def test_resolve_mixed(self) -> None:
        catalog = load_tools_catalog()
        result = resolve_tool_names(catalog, ["nmap", "dns"])
        names = [r["tool_name"] for r in result]
        assert "nmap" in names
        assert "subfinder" in names

    def test_resolve_unknown_raises(self) -> None:
        catalog = load_tools_catalog()
        with pytest.raises(ValueError, match="Unknown tool or category"):
            resolve_tool_names(catalog, ["nonexistent_tool"])

    def test_no_duplicates(self) -> None:
        catalog = load_tools_catalog()
        result = resolve_tool_names(catalog, ["nmap", "network"])
        names = [r["tool_name"] for r in result]
        assert names.count("nmap") == 1


class TestGetFullPentestOrder:
    def test_passive_before_active(self) -> None:
        catalog = load_tools_catalog()
        order = get_full_pentest_order(catalog)
        assert len(order) > 0
        # Find first active tool index and last passive tool index
        phases = {e["tool_name"]: e.get("phase", "active") for e in catalog}
        first_active = None
        last_passive = None
        for i, entry in enumerate(order):
            phase = phases.get(entry["tool_name"], "active")
            if phase == "active" and first_active is None:
                first_active = i
            if phase == "passive":
                last_passive = i
        # All passive tools should come before any active tool
        if first_active is not None and last_passive is not None:
            assert last_passive < first_active

    def test_returns_all_tools(self) -> None:
        catalog = load_tools_catalog()
        order = get_full_pentest_order(catalog)
        assert len(order) == len(catalog)
