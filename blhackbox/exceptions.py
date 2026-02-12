"""Custom exceptions for Blhackbox."""

from __future__ import annotations


class BlhackboxError(Exception):
    """Base exception for all Blhackbox errors."""


class HexStrikeConnectionError(BlhackboxError):
    """Raised when connection to HexStrike API fails."""


class HexStrikeAPIError(BlhackboxError):
    """Raised when HexStrike returns an error response."""

    def __init__(self, status_code: int, detail: str) -> None:
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"HexStrike API error {status_code}: {detail}")


class HexStrikeTimeoutError(BlhackboxError):
    """Raised when a HexStrike request exceeds the timeout."""


class GraphError(BlhackboxError):
    """Raised on Neo4j / knowledge graph failures."""


class OrchestratorError(BlhackboxError):
    """Raised when the AI orchestrator encounters an unrecoverable issue."""


class AuthorizationRequiredError(BlhackboxError):
    """Raised when the --authorized flag is not provided."""


class ReportingError(BlhackboxError):
    """Raised on report generation failures."""


class LLMProviderError(BlhackboxError):
    """Raised when no LLM provider is available or all providers fail."""


class ModuleError(BlhackboxError):
    """Raised when a custom module encounters an error."""
