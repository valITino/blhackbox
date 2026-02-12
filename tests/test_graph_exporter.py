"""Tests for the graph exporter's parsing logic."""

from __future__ import annotations

from blhackbox.core.graph_exporter import _to_text


class TestToText:
    def test_string_input(self) -> None:
        assert _to_text("hello") == "hello"

    def test_dict_input(self) -> None:
        result = _to_text({"a": "1", "b": "2"})
        assert "1" in result
        assert "2" in result

    def test_list_input(self) -> None:
        result = _to_text(["a", "b", "c"])
        assert "a" in result
        assert "c" in result

    def test_nested_input(self) -> None:
        result = _to_text({"data": [{"ip": "1.2.3.4"}, {"ip": "5.6.7.8"}]})
        assert "1.2.3.4" in result
        assert "5.6.7.8" in result

    def test_int_input(self) -> None:
        assert _to_text(42) == "42"
