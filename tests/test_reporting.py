"""Tests for the reporting engine."""

from __future__ import annotations

from pathlib import Path

from blhackbox.models.base import ScanSession
from blhackbox.reporting.html_generator import generate_html_report


class TestHTMLReport:
    def test_generate_html(self, sample_session: ScanSession, tmp_path: Path) -> None:
        out = tmp_path / "report.html"
        result = generate_html_report(sample_session, str(out))
        assert result.exists()
        assert result.suffix == ".html"

        content = result.read_text()
        assert "Blhackbox" in content
        assert "example.com" in content
        assert "Open Port 80" in content

    def test_html_contains_severity_cards(
        self, sample_session: ScanSession, tmp_path: Path
    ) -> None:
        out = tmp_path / "report.html"
        result = generate_html_report(sample_session, str(out))
        content = result.read_text()
        assert "summary-card" in content
        assert "INFO" in content

    def test_html_default_output(self, sample_session: ScanSession, tmp_path: Path) -> None:
        from blhackbox.config import settings

        original = settings.results_dir
        settings.results_dir = tmp_path
        try:
            result = generate_html_report(sample_session)
            assert result.exists()
            assert sample_session.id in result.name
        finally:
            settings.results_dir = original
