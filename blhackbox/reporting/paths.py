"""Organized report path resolution.

Creates a structured folder layout for reports:
    reports/
        reports-DDMMYYYY/
            report-<target-slug>-DDMMYYYY.md
            report-<target-slug>-DDMMYYYY.pdf
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from pathlib import Path

from blhackbox.config import settings


def _slugify(value: str, max_len: int = 60) -> str:
    """Convert a string to a safe filesystem slug."""
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value).strip("-").lower()
    return slug[:max_len].rstrip("-")


def get_report_dir(date: datetime | None = None) -> Path:
    """Return the date-specific report sub-directory, creating it if needed.

    Example: ``reports/reports-02032026/``
    """
    dt = date or datetime.now(UTC)
    folder_name = f"reports-{dt.strftime('%d%m%Y')}"
    report_dir = settings.reports_dir / folder_name
    report_dir.mkdir(parents=True, exist_ok=True)
    return report_dir


def get_report_path(
    target_label: str,
    ext: str,
    date: datetime | None = None,
) -> Path:
    """Build the full report file path.

    Args:
        target_label: Human-readable target name (e.g. ``example.com``).
        ext: File extension without dot (``md``, ``pdf``, ``html``).
        date: Override date (defaults to UTC now).

    Returns:
        Path like ``reports/reports-02032026/report-example-com-02032026.md``
    """
    dt = date or datetime.now(UTC)
    date_str = dt.strftime("%d%m%Y")
    slug = _slugify(target_label)
    filename = f"report-{slug}-{date_str}.{ext}"
    return get_report_dir(dt) / filename
