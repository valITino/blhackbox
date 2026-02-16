"""Abstract base class for tool execution backends."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, Field


class ToolResult(BaseModel):
    """Unified result from any backend."""

    success: bool = True
    tool: str = ""
    category: str = ""
    output: str = ""
    errors: list[str] = Field(default_factory=list)
    execution_time: float | None = None
    raw_data: dict[str, Any] = Field(default_factory=dict)

    @property
    def has_errors(self) -> bool:
        return bool(self.errors) or not self.success


class ToolBackend(ABC):
    """Interface that all tool execution backends must implement."""

    name: str = "base"

    @abstractmethod
    async def connect(self) -> None:
        """Initialise connections / resources."""

    @abstractmethod
    async def close(self) -> None:
        """Release connections / resources."""

    @abstractmethod
    async def health_check(self) -> bool:
        """Return True if this backend is ready to execute tools."""

    @abstractmethod
    async def run_tool(
        self,
        category: str,
        tool: str,
        params: dict[str, Any] | None = None,
    ) -> ToolResult:
        """Execute a security tool and return a unified result."""

    @abstractmethod
    async def list_tools(self) -> list[dict[str, str]]:
        """Return the tools this backend can execute."""

    async def __aenter__(self) -> ToolBackend:
        await self.connect()
        return self

    async def __aexit__(self, *exc: Any) -> None:
        await self.close()
