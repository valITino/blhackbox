"""Tests for the core runner utilities."""

from __future__ import annotations

import json
from pathlib import Path

from blhackbox.core.runner import save_session
from blhackbox.models.base import ScanSession


class TestSaveSession:
    def test_save_session(self, sample_session: ScanSession, tmp_path: Path) -> None:
        path = save_session(sample_session, tmp_path)
        assert path.exists()
        assert path.suffix == ".json"

        data = json.loads(path.read_text())
        assert data["status"] == "completed"
        assert data["target"]["value"] == "example.com"
