"""Custom exceptions for Blhackbox."""

from __future__ import annotations


class BlhackboxError(Exception):
    """Base exception for all Blhackbox errors."""


class GraphError(BlhackboxError):
    """Raised on Neo4j / knowledge graph failures."""


class ReportingError(BlhackboxError):
    """Raised on report generation failures."""


class ModuleError(BlhackboxError):
    """Raised when a custom module encounters an error."""
