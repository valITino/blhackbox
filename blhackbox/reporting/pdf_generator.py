"""Generate PDF reports from scan sessions using WeasyPrint."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from blhackbox.config import settings
from blhackbox.exceptions import ReportingError
from blhackbox.models.base import ScanSession
from blhackbox.reporting.html_generator import generate_html_report

logger = logging.getLogger("blhackbox.reporting.pdf_generator")


def generate_pdf_report(
    session: ScanSession,
    output_path: Optional[str] = None,
) -> Path:
    """Generate a PDF report from a scan session.

    First generates an HTML report, then converts it to PDF via WeasyPrint.

    Args:
        session: Completed scan session with findings.
        output_path: Override output file path.

    Returns:
        Path to the generated PDF file.
    """
    try:
        from weasyprint import HTML as WeasyprintHTML
    except ImportError as exc:
        raise ReportingError(
            "weasyprint is required for PDF generation. "
            "Install it with: pip install weasyprint"
        ) from exc

    # Generate HTML first
    html_path = generate_html_report(session)

    if output_path:
        pdf_path = Path(output_path)
    else:
        pdf_path = html_path.with_suffix(".pdf")

    try:
        WeasyprintHTML(filename=str(html_path)).write_pdf(str(pdf_path))
    except Exception as exc:
        raise ReportingError(f"PDF generation failed: {exc}") from exc

    logger.info("PDF report generated: %s", pdf_path)
    return pdf_path
