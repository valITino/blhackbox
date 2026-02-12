"""Tests for the graph exporter's parsing logic."""

from __future__ import annotations

from blhackbox.core.graph_exporter import (
    _CVE_PATTERN,
    _IP_PATTERN,
    _SUBDOMAIN_PATTERN,
    _to_text,
)


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


class TestIPPattern:
    def test_valid_ips(self) -> None:
        text = "Found hosts 192.168.1.1 and 10.0.0.1 and 255.255.255.255"
        matches = _IP_PATTERN.findall(text)
        assert "192.168.1.1" in matches
        assert "10.0.0.1" in matches
        assert "255.255.255.255" in matches

    def test_rejects_invalid_octets(self) -> None:
        text = "Invalid IP 999.999.999.999 and 256.1.2.3"
        matches = _IP_PATTERN.findall(text)
        assert "999.999.999.999" not in matches
        assert "256.1.2.3" not in matches

    def test_boundary_values(self) -> None:
        text = "Boundaries: 0.0.0.0 and 255.255.255.255 and 127.0.0.1"
        matches = _IP_PATTERN.findall(text)
        assert "0.0.0.0" in matches
        assert "255.255.255.255" in matches
        assert "127.0.0.1" in matches

    def test_embedded_in_text(self) -> None:
        text = "Nmap scan report for 10.20.30.40\n22/tcp open ssh"
        matches = _IP_PATTERN.findall(text)
        assert matches == ["10.20.30.40"]


class TestCVEPattern:
    def test_standard_cve(self) -> None:
        text = "Detected CVE-2021-44228 (Log4Shell)"
        matches = _CVE_PATTERN.findall(text)
        assert "CVE-2021-44228" in matches

    def test_multiple_cves(self) -> None:
        text = "Found CVE-2023-12345 and CVE-2024-9999 in scan"
        matches = _CVE_PATTERN.findall(text)
        assert len(matches) == 2

    def test_case_insensitive(self) -> None:
        text = "cve-2021-44228 detected"
        matches = _CVE_PATTERN.findall(text)
        assert len(matches) == 1

    def test_no_false_positives(self) -> None:
        text = "No vulnerabilities found"
        matches = _CVE_PATTERN.findall(text)
        assert len(matches) == 0


class TestSubdomainPattern:
    def test_subdomains(self) -> None:
        text = "Found api.example.com and mail.example.com"
        matches = _SUBDOMAIN_PATTERN.findall(text)
        assert "api.example.com" in matches
        assert "mail.example.com" in matches

    def test_nested_subdomains(self) -> None:
        text = "Deep subdomain: dev.api.example.com"
        matches = _SUBDOMAIN_PATTERN.findall(text)
        assert "dev.api.example.com" in matches

    def test_no_match_for_single_label(self) -> None:
        text = "localhost is not a subdomain"
        matches = _SUBDOMAIN_PATTERN.findall(text)
        # Should not match single-label names
        assert "localhost" not in matches
