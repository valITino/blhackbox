"""Report generation for scan sessions."""

from __future__ import annotations

from pathlib import Path

from pydantic import ValidationError

from blhackbox.models.aggregated_payload import AggregatedPayload
from blhackbox.models.base import ScanSession
from blhackbox.reporting.html_generator import (
    generate_html_report,
    generate_html_report_from_payload,
)
from blhackbox.reporting.md_generator import (
    generate_md_report,
    generate_md_report_from_payload,
)
from blhackbox.reporting.pdf_generator import (
    generate_pdf_report,
    generate_pdf_report_from_payload,
)

__all__ = [
    "generate_html_report",
    "generate_md_report",
    "generate_pdf_report",
    "load_session_source",
    "build_reports",
]


def load_session_source(session_path: Path) -> AggregatedPayload | ScanSession:
    """Load a persisted session file as the model that produced it.

    ``aggregate_results`` persists an :class:`AggregatedPayload`; older or
    externally produced session files may instead hold a :class:`ScanSession`.
    The AggregatedPayload schema is tried first (the format the MCP host
    writes), falling back to ScanSession for those legacy files.
    """
    text = session_path.read_text(encoding="utf-8")
    try:
        return AggregatedPayload.model_validate_json(text)
    except ValidationError:
        return ScanSession.model_validate_json(text)


def _generate_one(
    source: AggregatedPayload | ScanSession,
    fmt: str,
    output_path: str | None,
) -> Path:
    """Render a single report in ``fmt`` from the loaded session source."""
    if isinstance(source, AggregatedPayload):
        if fmt == "md":
            return generate_md_report_from_payload(source, output_path)
        if fmt == "pdf":
            return generate_pdf_report_from_payload(source, output_path)
        return generate_html_report_from_payload(source, output_path)
    if fmt == "md":
        return generate_md_report(source, output_path)
    if fmt == "pdf":
        return generate_pdf_report(source, output_path)
    return generate_html_report(source, output_path)


def build_reports(
    session_path: Path,
    fmt: str = "both",
    output_path: str | None = None,
) -> list[tuple[Path, str]]:
    """Generate report file(s) from a persisted session file.

    Detects whether the file holds an ``AggregatedPayload`` (written by
    ``aggregate_results``) or a legacy ``ScanSession`` and dispatches to the
    matching generator.  ``output_path`` is honoured only for single-format
    requests; ``"both"`` always writes ``.md`` + ``.pdf`` into the organized
    report folder.

    Returns a list of ``(path, format)`` tuples for the generated reports.
    """
    source = load_session_source(session_path)
    if fmt == "both":
        return [
            (_generate_one(source, "md", None), "md"),
            (_generate_one(source, "pdf", None), "pdf"),
        ]
    return [(_generate_one(source, fmt, output_path), fmt)]
