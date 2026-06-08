"""Tests for the reporting engine."""

from __future__ import annotations

import json
from pathlib import Path

from blhackbox.models.aggregated_payload import (
    AggregatedPayload,
    Findings,
    VulnerabilityEntry,
)
from blhackbox.models.base import ScanSession
from blhackbox.reporting import build_reports, load_session_source
from blhackbox.reporting.html_generator import generate_html_report
from blhackbox.reporting.md_generator import generate_md_report
from blhackbox.reporting.paths import get_report_dir, get_report_path


def _write_payload_session(tmp_path: Path) -> Path:
    """Persist an AggregatedPayload exactly as aggregate_results does."""
    payload = AggregatedPayload(
        session_id="rt-001",
        target="example.com",
        findings=Findings(
            vulnerabilities=[
                VulnerabilityEntry(
                    id="CVE-2021-44228",
                    title="Log4Shell",
                    severity="critical",
                    host="example.com",
                    description="Remote code execution via JNDI lookup.",
                )
            ],
        ),
    )
    session_file = tmp_path / "session-rt-001.json"
    session_file.write_text(
        json.dumps(payload.to_dict(), indent=2, default=str), encoding="utf-8"
    )
    return session_file


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


class TestBuildReports:
    """Regression coverage for the aggregate_results -> generate_report flow.

    ``aggregate_results`` persists an AggregatedPayload; the report entry points
    must load it with the AggregatedPayload schema (not ScanSession) and use the
    *_from_payload generators.
    """

    def test_load_session_source_detects_payload(self, tmp_path: Path) -> None:
        session_file = _write_payload_session(tmp_path)
        source = load_session_source(session_file)
        assert isinstance(source, AggregatedPayload)
        assert source.target == "example.com"

    def test_load_session_source_detects_scansession(
        self, sample_session: ScanSession, tmp_path: Path
    ) -> None:
        session_file = tmp_path / "scan.json"
        session_file.write_text(sample_session.model_dump_json(), encoding="utf-8")
        source = load_session_source(session_file)
        assert isinstance(source, ScanSession)
        assert source.target.value == "example.com"

    def test_build_reports_from_payload_md(self, tmp_path: Path) -> None:
        session_file = _write_payload_session(tmp_path)
        out = tmp_path / "report.md"
        reports = build_reports(session_file, "md", str(out))
        assert reports == [(out, "md")]
        content = out.read_text()
        assert "example.com" in content
        # The payload-based template renders a Vulnerabilities section.
        assert "Vulnerabilities" in content
        assert "Log4Shell" in content

    def test_build_reports_from_payload_html(self, tmp_path: Path) -> None:
        session_file = _write_payload_session(tmp_path)
        out = tmp_path / "report.html"
        reports = build_reports(session_file, "html", str(out))
        assert reports[0][0].exists()
        assert "example.com" in out.read_text()

    def test_build_reports_scansession_fallback(
        self, sample_session: ScanSession, tmp_path: Path
    ) -> None:
        session_file = tmp_path / "scan.json"
        session_file.write_text(sample_session.model_dump_json(), encoding="utf-8")
        out = tmp_path / "report.md"
        build_reports(session_file, "md", str(out))
        content = out.read_text()
        # The ScanSession template renders a Findings section.
        assert "Findings" in content
        assert "Open Port 80" in content
