"""Core domain models."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class Severity(StrEnum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class Target(BaseModel):
    """Represents a scan target."""

    value: str = Field(description="Domain, IP, or URL")
    target_type: str = Field(default="auto", description="Type: domain, ip, url, cidr")
    metadata: dict[str, Any] = Field(default_factory=dict)

    def __str__(self) -> str:
        return self.value


class Finding(BaseModel):
    """A single security finding from any tool or agent."""

    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    target: str
    tool: str = Field(description="Tool that produced this finding")
    category: str = Field(default="general")
    title: str
    description: str = ""
    severity: Severity = Severity.INFO
    evidence: str = ""
    remediation: str = ""
    raw_data: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))

    model_config = ConfigDict(use_enum_values=True)


class ScanSession(BaseModel):
    """Tracks a complete scanning session."""

    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:8])
    target: Target
    started_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    finished_at: datetime | None = None
    tools_executed: list[str] = Field(default_factory=list)
    findings: list[Finding] = Field(default_factory=list)
    status: str = Field(default="running")
    metadata: dict[str, Any] = Field(default_factory=dict)

    def add_finding(self, finding: Finding) -> None:
        self.findings.append(finding)

    def mark_tool_done(self, tool_name: str) -> None:
        if tool_name not in self.tools_executed:
            self.tools_executed.append(tool_name)

    def finish(self) -> None:
        self.finished_at = datetime.now(UTC)
        self.status = "completed"

    @property
    def severity_counts(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for f in self.findings:
            sev = f.severity if isinstance(f.severity, str) else f.severity.value
            counts[sev] = counts.get(sev, 0) + 1
        return counts

    @property
    def duration_seconds(self) -> float | None:
        if self.finished_at:
            return (self.finished_at - self.started_at).total_seconds()
        return None
