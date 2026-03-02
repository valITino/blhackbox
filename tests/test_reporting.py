"""Tests for the reporting engine."""

from __future__ import annotations

from pathlib import Path

from blhackbox.models.base import ScanSession
from blhackbox.reporting.html_generator import generate_html_report
from blhackbox.reporting.md_generator import generate_md_report
from blhackbox.reporting.paths import get_report_dir, get_report_path


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

        original = settings.reports_dir
        settings.reports_dir = tmp_path
        try:
            result = generate_html_report(sample_session)
            assert result.exists()
            assert "example-com" in result.name
            assert result.suffix == ".html"
            # Check it lands in a date-subfolder
            assert result.parent.name.startswith("reports-")
        finally:
            settings.reports_dir = original


class TestMarkdownReport:
    def test_generate_md(self, sample_session: ScanSession, tmp_path: Path) -> None:
        out = tmp_path / "report.md"
        result = generate_md_report(sample_session, str(out))
        assert result.exists()
        assert result.suffix == ".md"

        content = result.read_text()
        assert "Blhackbox" in content
        assert "example.com" in content
        assert "Open Port 80" in content

    def test_md_contains_severity_table(
        self, sample_session: ScanSession, tmp_path: Path
    ) -> None:
        out = tmp_path / "report.md"
        result = generate_md_report(sample_session, str(out))
        content = result.read_text()
        assert "| Severity | Count |" in content
        assert "INFO" in content

    def test_md_default_output(self, sample_session: ScanSession, tmp_path: Path) -> None:
        from blhackbox.config import settings

        original = settings.reports_dir
        settings.reports_dir = tmp_path
        try:
            result = generate_md_report(sample_session)
            assert result.exists()
            assert "example-com" in result.name
            assert result.suffix == ".md"
            assert result.parent.name.startswith("reports-")
        finally:
            settings.reports_dir = original


class TestReportPaths:
    def test_get_report_dir_creates_folder(self, tmp_path: Path) -> None:
        from blhackbox.config import settings

        original = settings.reports_dir
        settings.reports_dir = tmp_path
        try:
            report_dir = get_report_dir()
            assert report_dir.exists()
            assert report_dir.parent == tmp_path
            assert report_dir.name.startswith("reports-")
            # DDMMYYYY = 8 digits
            date_part = report_dir.name.replace("reports-", "")
            assert len(date_part) == 8
            assert date_part.isdigit()
        finally:
            settings.reports_dir = original

    def test_get_report_path_structure(self, tmp_path: Path) -> None:
        from blhackbox.config import settings

        original = settings.reports_dir
        settings.reports_dir = tmp_path
        try:
            path = get_report_path("example.com", "md")
            assert path.name.startswith("report-")
            assert "example-com" in path.name
            assert path.suffix == ".md"
            assert path.parent.name.startswith("reports-")
        finally:
            settings.reports_dir = original

    def test_get_report_path_pdf(self, tmp_path: Path) -> None:
        from blhackbox.config import settings

        original = settings.reports_dir
        settings.reports_dir = tmp_path
        try:
            path = get_report_path("10.0.0.1", "pdf")
            assert "10-0-0-1" in path.name
            assert path.suffix == ".pdf"
        finally:
            settings.reports_dir = original
