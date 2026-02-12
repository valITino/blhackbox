"""Core domain models."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class Severity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class Target(BaseModel):
    """Represents a scan target."""

    value: str = Field(description="Domain, IP, or URL")
    target_type: str = Field(default="auto", description="Type: domain, ip, url, cidr")
    metadata: Dict[str, Any] = Field(default_factory=dict)

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
    raw_data: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = ConfigDict(use_enum_values=True)


class ScanSession(BaseModel):
    """Tracks a complete scanning session."""

    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:8])
    target: Target
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    finished_at: Optional[datetime] = None
    tools_executed: List[str] = Field(default_factory=list)
    findings: List[Finding] = Field(default_factory=list)
    status: str = Field(default="running")
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def add_finding(self, finding: Finding) -> None:
        self.findings.append(finding)

    def mark_tool_done(self, tool_name: str) -> None:
        if tool_name not in self.tools_executed:
            self.tools_executed.append(tool_name)

    def finish(self) -> None:
        self.finished_at = datetime.now(timezone.utc)
        self.status = "completed"

    @property
    def severity_counts(self) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for f in self.findings:
            sev = f.severity if isinstance(f.severity, str) else f.severity.value
            counts[sev] = counts.get(sev, 0) + 1
        return counts

    @property
    def duration_seconds(self) -> Optional[float]:
        if self.finished_at:
            return (self.finished_at - self.started_at).total_seconds()
        return None
