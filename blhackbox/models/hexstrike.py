"""Pydantic models for HexStrike API responses."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class HexStrikeToolResponse(BaseModel):
    """Response from POST /api/tools/<category>/<tool>."""

    success: bool = True
    tool: str = ""
    category: str = ""
    output: Any = None
    raw_output: str = ""
    execution_time: Optional[float] = None
    errors: List[str] = Field(default_factory=list)

    @property
    def has_errors(self) -> bool:
        return bool(self.errors) or not self.success


class HexStrikeAnalysisResponse(BaseModel):
    """Response from POST /api/intelligence/analyze-target."""

    success: bool = True
    target: str = ""
    analysis_type: str = ""
    results: Dict[str, Any] = Field(default_factory=dict)
    recommendations: List[str] = Field(default_factory=list)
    risk_score: Optional[float] = None
    errors: List[str] = Field(default_factory=list)


class HexStrikeAgentInfo(BaseModel):
    """A single agent entry from GET /api/agents/list."""

    name: str
    description: str = ""
    capabilities: List[str] = Field(default_factory=list)
    status: str = "available"


class HexStrikeAgentResponse(BaseModel):
    """Response from POST /api/agents/<agent>/run."""

    success: bool = True
    agent: str = ""
    target: str = ""
    results: Dict[str, Any] = Field(default_factory=dict)
    findings: List[Dict[str, Any]] = Field(default_factory=list)
    execution_time: Optional[float] = None
    errors: List[str] = Field(default_factory=list)

    @property
    def has_errors(self) -> bool:
        return bool(self.errors) or not self.success
