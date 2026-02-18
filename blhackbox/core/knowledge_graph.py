"""Async Neo4j knowledge graph client for attack surface modeling."""

from __future__ import annotations

import logging
import re
from typing import Any

from neo4j import AsyncDriver, AsyncGraphDatabase

from blhackbox.config import Settings
from blhackbox.config import settings as default_settings
from blhackbox.exceptions import GraphError
from blhackbox.models.graph import (
    AggregatedSessionNode,
    DomainNode,
    FindingNode,
    GraphNode,
    GraphRelationship,
    IPAddressNode,
    PortNode,
    RelationshipType,
    ServiceNode,
    VulnerabilityNode,
)

logger = logging.getLogger("blhackbox.core.knowledge_graph")

# Cypher injection prevention: only allow safe identifiers in dynamic query parts
_SAFE_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _validate_identifier(value: str, context: str) -> str:
    """Validate that a value is safe for use as a Cypher identifier (label, property key)."""
    if not _SAFE_IDENTIFIER.match(value):
        raise GraphError(
            f"Unsafe Cypher identifier in {context}: {value!r}. "
            "Only alphanumeric characters and underscores are allowed."
        )
    return value


class KnowledgeGraphClient:
    """Async client for Neo4j knowledge graph operations.

    Provides high-level methods for merging nodes and creating
    relationships that model the attack surface.
    """

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or default_settings
        self._driver: AsyncDriver | None = None

    # -- lifecycle -----------------------------------------------------------

    async def __aenter__(self) -> KnowledgeGraphClient:
        try:
            self._driver = AsyncGraphDatabase.driver(
                self._settings.neo4j_uri,
                auth=(self._settings.neo4j_user, self._settings.neo4j_password),
            )
            # Verify connectivity
            await self._driver.verify_connectivity()
            logger.info("Connected to Neo4j at %s", self._settings.neo4j_uri)
        except Exception as exc:
            raise GraphError(f"Failed to connect to Neo4j: {exc}") from exc
        return self

    async def __aexit__(self, *exc: Any) -> None:
        if self._driver:
            await self._driver.close()
            self._driver = None

    @property
    def driver(self) -> AsyncDriver:
        if self._driver is None:
            raise GraphError("Driver not initialized. Use 'async with KnowledgeGraphClient():'")
        return self._driver

    # -- generic operations --------------------------------------------------

    async def merge_node(self, node: GraphNode) -> None:
        """MERGE a node by its merge key, setting all properties."""
        label = _validate_identifier(node.label, "node label")
        merge_key = _validate_identifier(node.merge_key, "merge key")
        cypher = (
            f"MERGE (n:{label} {{{merge_key}: $merge_value}}) "
            f"SET n += $props"
        )
        props = node.to_cypher_properties()
        merge_value = props.pop(node.merge_key)

        async with self.driver.session(database=self._settings.neo4j_database) as session:
            await session.run(cypher, merge_value=merge_value, props=props)
        logger.debug("Merged %s(%s=%s)", label, merge_key, merge_value)

    async def create_relationship(
        self,
        source: GraphNode,
        rel_type: RelationshipType,
        target: GraphNode,
        properties: dict[str, Any] | None = None,
    ) -> None:
        """Create a relationship between two existing nodes."""
        props = properties or {}
        src_label = _validate_identifier(source.label, "source label")
        src_key = _validate_identifier(source.merge_key, "source merge key")
        tgt_label = _validate_identifier(target.label, "target label")
        tgt_key = _validate_identifier(target.merge_key, "target merge key")
        rel_name = _validate_identifier(rel_type.value, "relationship type")
        cypher = (
            f"MATCH (a:{src_label} {{{src_key}: $a_val}}) "
            f"MATCH (b:{tgt_label} {{{tgt_key}: $b_val}}) "
            f"MERGE (a)-[r:{rel_name}]->(b) "
            f"SET r += $props"
        )
        async with self.driver.session(database=self._settings.neo4j_database) as session:
            await session.run(
                cypher,
                a_val=source.merge_value,
                b_val=target.merge_value,
                props=props,
            )
        logger.debug(
            "Relationship %s -[%s]-> %s",
            source.merge_value,
            rel_type.value,
            target.merge_value,
        )

    async def apply_relationship(self, rel: GraphRelationship) -> None:
        """Merge both nodes and create the relationship."""
        await self.merge_node(rel.source)
        await self.merge_node(rel.target)
        await self.create_relationship(
            rel.source, rel.rel_type, rel.target, rel.properties
        )

    # -- high-level helpers --------------------------------------------------

    async def merge_domain(self, domain: str) -> DomainNode:
        node = DomainNode(name=domain)
        await self.merge_node(node)
        return node

    async def merge_ip(self, ip: str) -> IPAddressNode:
        node = IPAddressNode(address=ip)
        await self.merge_node(node)
        return node

    async def merge_port(
        self, ip: str, port: int, protocol: str = "tcp"
    ) -> PortNode:
        ip_node = await self.merge_ip(ip)
        port_node = PortNode(number=port, protocol=protocol)
        await self.merge_node(port_node)
        await self.create_relationship(
            ip_node,
            RelationshipType.HAS_PORT,
            port_node,
            {"protocol": protocol},
        )
        return port_node

    async def merge_service(
        self, ip: str, port: int, service_name: str, version: str = ""
    ) -> ServiceNode:
        port_node = await self.merge_port(ip, port)
        svc_node = ServiceNode(name=service_name, version=version)
        await self.merge_node(svc_node)
        await self.create_relationship(
            port_node, RelationshipType.RUNS_SERVICE, svc_node
        )
        return svc_node

    async def merge_finding(
        self,
        target_value: str,
        finding_id: str,
        tool: str,
        title: str,
        severity: str = "info",
        description: str = "",
        evidence: str = "",
        remediation: str = "",
    ) -> FindingNode:
        finding_node = FindingNode(
            finding_id=finding_id,
            tool=tool,
            title=title,
            severity=severity,
            description=description,
            evidence=evidence,
            remediation=remediation,
        )
        await self.merge_node(finding_node)

        # Link to domain or IP
        if _looks_like_ip(target_value):
            parent = IPAddressNode(address=target_value)
        else:
            parent = DomainNode(name=target_value)
        await self.merge_node(parent)
        await self.create_relationship(
            parent, RelationshipType.HAS_FINDING, finding_node
        )
        return finding_node

    async def merge_vulnerability(
        self,
        target_value: str,
        identifier: str,
        severity: str = "info",
        title: str = "",
    ) -> VulnerabilityNode:
        vuln = VulnerabilityNode(
            identifier=identifier, severity=severity, title=title
        )
        await self.merge_node(vuln)

        if _looks_like_ip(target_value):
            parent = IPAddressNode(address=target_value)
        else:
            parent = DomainNode(name=target_value)
        await self.merge_node(parent)
        await self.create_relationship(
            parent, RelationshipType.HAS_FINDING, vuln
        )
        return vuln

    async def link_domain_to_ip(self, domain: str, ip: str) -> None:
        d = await self.merge_domain(domain)
        i = await self.merge_ip(ip)
        await self.create_relationship(d, RelationshipType.RESOLVES_TO, i)

    async def link_subdomain(self, subdomain: str, parent_domain: str) -> None:
        sub = await self.merge_domain(subdomain)
        parent = await self.merge_domain(parent_domain)
        await self.create_relationship(sub, RelationshipType.SUBDOMAIN_OF, parent)

    async def merge_aggregated_session(
        self,
        session_id: str,
        target_value: str,
        scan_timestamp: str = "",
        tools_run: str = "",
        agents_run: str = "",
        compression_ratio: float = 0.0,
        ollama_model: str = "",
        duration_seconds: float = 0.0,
        warning: str = "",
    ) -> AggregatedSessionNode:
        """Merge an AggregatedSession node and link it to a target."""
        node = AggregatedSessionNode(
            session_id=session_id,
            target=target_value,
            scan_timestamp=scan_timestamp,
            tools_run=tools_run,
            agents_run=agents_run,
            compression_ratio=compression_ratio,
            ollama_model=ollama_model,
            duration_seconds=duration_seconds,
            warning=warning,
        )
        await self.merge_node(node)

        # Link to domain or IP
        if _looks_like_ip(target_value):
            parent = IPAddressNode(address=target_value)
        else:
            parent = DomainNode(name=target_value)
        await self.merge_node(parent)
        await self.create_relationship(
            parent, RelationshipType.HAS_AGGREGATED_SESSION, node
        )
        return node

    # -- query helpers -------------------------------------------------------

    async def run_query(
        self, cypher: str, params: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        """Execute a raw Cypher query and return records as dicts."""
        async with self.driver.session(database=self._settings.neo4j_database) as session:
            result = await session.run(cypher, **(params or {}))
            records = await result.data()
        return records

    async def get_target_summary(self, target: str) -> dict[str, int]:
        """Return node-type counts for a target's subgraph."""
        cypher = """
        MATCH (root {name: $target})-[*0..3]-(n)
        RETURN labels(n)[0] AS label, count(DISTINCT n) AS cnt
        ORDER BY cnt DESC
        """
        records = await self.run_query(cypher, {"target": target})
        return {r["label"]: r["cnt"] for r in records if r.get("label")}

    async def get_findings_for_target(self, target: str) -> list[dict[str, Any]]:
        """Retrieve all findings linked to a target."""
        cypher = """
        MATCH (root)-[:HAS_FINDING]->(f:Finding)
        WHERE (root:Domain AND root.name = $target)
           OR (root:IPAddress AND root.address = $target)
        RETURN f
        ORDER BY f.severity DESC
        """
        records = await self.run_query(cypher, {"target": target})
        return [r["f"] for r in records]

    async def clear_all(self) -> None:
        """Delete all nodes and relationships. Use with caution."""
        async with self.driver.session(database=self._settings.neo4j_database) as session:
            await session.run("MATCH (n) DETACH DELETE n")
        logger.warning("All graph data cleared")


def _looks_like_ip(value: str) -> bool:
    parts = value.split(".")
    if len(parts) != 4:
        return False
    return all(p.isdigit() and 0 <= int(p) <= 255 for p in parts)
