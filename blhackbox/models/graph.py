"""Graph node and relationship models for Neo4j knowledge graph."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Relationships
# ---------------------------------------------------------------------------

class RelationshipType(StrEnum):
    RESOLVES_TO = "RESOLVES_TO"
    HAS_PORT = "HAS_PORT"
    RUNS_SERVICE = "RUNS_SERVICE"
    RUNS = "RUNS"
    HAS_FINDING = "HAS_FINDING"
    DISCOVERED_BY = "DISCOVERED_BY"
    SUBDOMAIN_OF = "SUBDOMAIN_OF"
    LINKED_TO = "LINKED_TO"
    CONTAINS = "CONTAINS"
    HAS_AGGREGATED_SESSION = "HAS_AGGREGATED_SESSION"


# ---------------------------------------------------------------------------
# Base node
# ---------------------------------------------------------------------------

class GraphNode(BaseModel):
    """Base for all graph nodes."""

    label: str
    properties: dict[str, Any] = Field(default_factory=dict)
    merge_key: str = Field(description="Property name used as the unique merge key")
    merge_value: Any = Field(description="Value of the merge key")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    def to_cypher_properties(self) -> dict[str, Any]:
        props = {**self.properties, "created_at": self.created_at.isoformat()}
        props[self.merge_key] = self.merge_value
        return props


# ---------------------------------------------------------------------------
# Concrete node types
# ---------------------------------------------------------------------------

class DomainNode(GraphNode):
    label: str = "Domain"
    merge_key: str = "name"

    def __init__(self, name: str, **kwargs: Any) -> None:
        super().__init__(merge_value=name, **kwargs)


class IPAddressNode(GraphNode):
    label: str = "IPAddress"
    merge_key: str = "address"

    def __init__(self, address: str, **kwargs: Any) -> None:
        super().__init__(merge_value=address, **kwargs)


class PortNode(GraphNode):
    label: str = "Port"
    merge_key: str = "port_id"

    def __init__(self, number: int, protocol: str = "tcp", **kwargs: Any) -> None:
        props = kwargs.pop("properties", {})
        props["protocol"] = protocol
        props["number"] = number
        port_id = f"{number}/{protocol}"
        super().__init__(merge_value=port_id, properties=props, **kwargs)


class ServiceNode(GraphNode):
    label: str = "Service"
    merge_key: str = "name"

    def __init__(self, name: str, version: str = "", **kwargs: Any) -> None:
        props = kwargs.pop("properties", {})
        if version:
            props["version"] = version
        super().__init__(merge_value=name, properties=props, **kwargs)


class VulnerabilityNode(GraphNode):
    label: str = "Vulnerability"
    merge_key: str = "identifier"

    def __init__(
        self,
        identifier: str,
        severity: str = "info",
        title: str = "",
        **kwargs: Any,
    ) -> None:
        props = kwargs.pop("properties", {})
        props["severity"] = severity
        if title:
            props["title"] = title
        super().__init__(merge_value=identifier, properties=props, **kwargs)


class FindingNode(GraphNode):
    label: str = "Finding"
    merge_key: str = "finding_id"

    def __init__(
        self,
        finding_id: str,
        tool: str = "",
        title: str = "",
        severity: str = "info",
        description: str = "",
        evidence: str = "",
        remediation: str = "",
        **kwargs: Any,
    ) -> None:
        props = kwargs.pop("properties", {})
        props.update(
            {
                "tool": tool,
                "title": title,
                "severity": severity,
                "description": description[:5000],
                "evidence": evidence[:5000],
                "remediation": remediation[:2000],
            }
        )
        super().__init__(merge_value=finding_id, properties=props, **kwargs)


class TechnologyNode(GraphNode):
    label: str = "Technology"
    merge_key: str = "name"

    def __init__(self, name: str, category: str = "", **kwargs: Any) -> None:
        props = kwargs.pop("properties", {})
        if category:
            props["category"] = category
        super().__init__(merge_value=name, properties=props, **kwargs)


class AggregatedSessionNode(GraphNode):
    """Represents an aggregated pentest session processed by the Ollama pipeline."""

    label: str = "AggregatedSession"
    merge_key: str = "session_id"

    def __init__(
        self,
        session_id: str,
        target: str = "",
        scan_timestamp: str = "",
        tools_run: str = "",
        agents_run: str = "",
        compression_ratio: float = 0.0,
        ollama_model: str = "",
        duration_seconds: float = 0.0,
        warning: str = "",
        **kwargs: Any,
    ) -> None:
        props = kwargs.pop("properties", {})
        props.update(
            {
                "target": target,
                "scan_timestamp": scan_timestamp,
                "tools_run": tools_run,
                "agents_run": agents_run,
                "compression_ratio": compression_ratio,
                "ollama_model": ollama_model,
                "duration_seconds": duration_seconds,
                "warning": warning,
            }
        )
        super().__init__(merge_value=session_id, properties=props, **kwargs)


# ---------------------------------------------------------------------------
# Relationship model
# ---------------------------------------------------------------------------

class GraphRelationship(BaseModel):
    """A typed relationship between two graph nodes."""

    source: GraphNode
    target: GraphNode
    rel_type: RelationshipType
    properties: dict[str, Any] = Field(default_factory=dict)
