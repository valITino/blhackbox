"""Tests for the tools catalogue utilities."""

from __future__ import annotations

from blhackbox.utils.catalog import load_tools_catalog


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


class TestSearchToolsCatalog:
    def test_search_by_keyword(self) -> None:
        from blhackbox.utils.catalog import search_tools_catalog

        catalog = load_tools_catalog()
        result = search_tools_catalog(catalog, "xss", limit=5)
        names = [entry["tool_name"] for entry in result]
        assert "dalfox" in names

    def test_search_filters_by_category_and_phase(self) -> None:
        from blhackbox.utils.catalog import search_tools_catalog

        catalog = load_tools_catalog()
        result = search_tools_catalog(
            catalog,
            "web",
            category="web",
            phase="active",
            limit=50,
        )
        assert result
        assert all(entry.get("category") == "web" for entry in result)
        assert all(entry.get("phase") == "active" for entry in result)

    def test_get_tool_details(self) -> None:
        from blhackbox.utils.catalog import get_tool_details

        catalog = load_tools_catalog()
        details = get_tool_details(catalog, "nmap")
        assert details["backend"] == "kali-mcp"
        assert "ports" in details["tags"]

    def test_recommend_workflow_tools(self) -> None:
        from blhackbox.utils.catalog import recommend_workflow_tools

        catalog = load_tools_catalog()
        tools = recommend_workflow_tools(catalog, "web-app-assessment")
        names = [entry["tool_name"] for entry in tools]
        assert names[:3] == ["httpx", "whatweb", "wafw00f"]
        assert "nuclei" in names
