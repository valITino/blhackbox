"""Session persistence and utility helpers for scan results."""

from __future__ import annotations

import logging
import re
from datetime import UTC, datetime
from pathlib import Path

from blhackbox.config import settings
from blhackbox.models.base import ScanSession, Severity

logger = logging.getLogger("blhackbox.core.runner")


def _sanitize_filename(value: str) -> str:
    """Sanitize a string for safe use in filenames (prevent path traversal)."""
    # Replace path separators and other dangerous characters
    safe = re.sub(r"[^a-zA-Z0-9._\-]", "_", value)
    # Remove any leading dots or dashes to prevent hidden files
    safe = safe.lstrip("._")
    # Truncate to reasonable length
    return safe[:100] if safe else "unknown"


def save_session(session: ScanSession, results_dir: Path | None = None) -> Path:
    """Persist a scan session as JSON to the results directory."""
    out_dir = results_dir or settings.results_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    safe_target = _sanitize_filename(session.target.value)
    safe_id = _sanitize_filename(session.id)
    filename = f"{safe_target}_{safe_id}_{timestamp}.json"
    filepath = out_dir / filename

    # Verify the resolved path stays within the output directory
    resolved = filepath.resolve()
    if not str(resolved).startswith(str(out_dir.resolve())):
        raise ValueError(f"Output path escapes results directory: {filepath}")

    filepath.write_text(
        session.model_dump_json(indent=2),
        encoding="utf-8",
    )
    logger.info("Session saved to %s", filepath)
    return filepath


def _risk_to_severity(score: float) -> Severity:
    if score >= 8.0:
        return Severity.CRITICAL
    if score >= 6.0:
        return Severity.HIGH
    if score >= 4.0:
        return Severity.MEDIUM
    if score >= 2.0:
        return Severity.LOW
    return Severity.INFO
