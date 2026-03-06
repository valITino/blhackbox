"""Base class for custom modules that extend Blhackbox capabilities."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any

from blhackbox.models.base import Finding, Severity

logger = logging.getLogger("blhackbox.modules.base")


class BlhackboxModule(ABC):
    """Abstract base class for custom Blhackbox modules.

    Modules wrap tool execution with custom pre/post-processing.
    They add intelligence on top of raw tool output.

    Subclass this and implement:
      - name: unique module identifier
      - description: human-readable description
      - run(): the module's logic
    """

    name: str = "base_module"
    description: str = "Base module"
    category: str = "custom"
    version: str = "1.0.0"

    def __init__(self, client: Any) -> None:
        self._client = client
        self._findings: list[Finding] = []

    @abstractmethod
    async def run(self, target: str, **kwargs: Any) -> list[Finding]:
        """Execute the module and return findings.

        Args:
            target: The scan target (domain, IP, URL).
            **kwargs: Module-specific parameters.

        Returns:
            List of Finding objects.
        """
        ...

    def add_finding(
        self,
        target: str,
        title: str,
        description: str = "",
        severity: Severity = Severity.INFO,
        evidence: str = "",
        remediation: str = "",
        raw_data: dict[str, Any] | None = None,
    ) -> Finding:
        """Create and register a finding."""
        finding = Finding(
            target=target,
            tool=f"module/{self.name}",
            category=self.category,
            title=title,
            description=description,
            severity=severity,
            evidence=evidence,
            remediation=remediation,
            raw_data=raw_data or {},
        )
        self._findings.append(finding)
        return finding

    @property
    def findings(self) -> list[Finding]:
        return list(self._findings)

    def clear_findings(self) -> None:
        self._findings.clear()

    def __repr__(self) -> str:
        return f"<Module:{self.name} v{self.version}>"
