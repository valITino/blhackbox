"""Tests for custom module base class."""

from __future__ import annotations

from typing import Any, List
from unittest.mock import AsyncMock

import pytest

from blhackbox.models.base import Finding, Severity
from blhackbox.modules.base import HexStrikeModule


class DummyModule(HexStrikeModule):
    name = "dummy"
    description = "Test module"
    category = "test"

    async def run(self, target: str, **kwargs: Any) -> List[Finding]:
        self.clear_findings()
        self.add_finding(
            target=target,
            title="Dummy Finding",
            severity=Severity.LOW,
        )
        return self.findings


class TestHexStrikeModule:
    def test_module_repr(self) -> None:
        client = AsyncMock()
        mod = DummyModule(client)
        assert "dummy" in repr(mod)

    @pytest.mark.asyncio
    async def test_module_run(self) -> None:
        client = AsyncMock()
        mod = DummyModule(client)
        findings = await mod.run("example.com")
        assert len(findings) == 1
        assert findings[0].title == "Dummy Finding"
        assert findings[0].tool == "module/dummy"

    @pytest.mark.asyncio
    async def test_module_clear_findings(self) -> None:
        client = AsyncMock()
        mod = DummyModule(client)
        await mod.run("example.com")
        assert len(mod.findings) == 1
        mod.clear_findings()
        assert len(mod.findings) == 0
