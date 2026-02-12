"""Async Neo4j knowledge graph client for attack surface modeling."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from neo4j import AsyncGraphDatabase, AsyncDriver, AsyncSession

from blhackbox.config import Settings, settings as default_settings
from blhackbox.exceptions import GraphError
from blhackbox.models.graph import (
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


class KnowledgeGraphClient:
    """Async client for Neo4j knowledge graph operations.

    Provides high-level methods for merging nodes and creating
    relationships that model the attack surface.
    """

    def __init__(self, settings: Optional[Settings] = None) -> None:
        self._settings = settings or default_settings
        self._driver: Optional[AsyncDriver] = None

    # -- lifecycle -----------------------------------------------------------

    async def __aenter__(self) -> "KnowledgeGraphClient":
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
        cypher = (
            f"MERGE (n:{node.label} {{{node.merge_key}: $merge_value}}) "
            f"SET n += $props"
        )
        props = node.to_cypher_properties()
        merge_value = props.pop(node.merge_key)

        async with self.driver.session() as session:
            await session.run(cypher, merge_value=merge_value, props=props)
        logger.debug("Merged %s(%s=%s)", node.label, node.merge_key, merge_value)

    async def create_relationship(
        self,
        source: GraphNode,
        rel_type: RelationshipType,
        target: GraphNode,
        properties: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Create a relationship between two existing nodes."""
        props = properties or {}
        cypher = (
            f"MATCH (a:{source.label} {{{source.merge_key}: $a_val}}) "
            f"MATCH (b:{target.label} {{{target.merge_key}: $b_val}}) "
            f"MERGE (a)-[r:{rel_type.value}]->(b) "
            f"SET r += $props"
        )
        async with self.driver.session() as session:
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

    # -- query helpers -------------------------------------------------------

    async def run_query(
        self, cypher: str, params: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Execute a raw Cypher query and return records as dicts."""
        async with self.driver.session() as session:
            result = await session.run(cypher, **(params or {}))
            records = await result.data()
        return records

    async def get_target_summary(self, target: str) -> Dict[str, int]:
        """Return node-type counts for a target's subgraph."""
        cypher = """
        MATCH (root {name: $target})-[*0..3]-(n)
        RETURN labels(n)[0] AS label, count(DISTINCT n) AS cnt
        ORDER BY cnt DESC
        """
        records = await self.run_query(cypher, {"target": target})
        return {r["label"]: r["cnt"] for r in records if r.get("label")}

    async def get_findings_for_target(self, target: str) -> List[Dict[str, Any]]:
        """Retrieve all findings linked to a target."""
        cypher = """
        MATCH (root)-[:HAS_FINDING]->(f:Finding)
        WHERE root.name = $target OR root.address = $target
        RETURN f
        ORDER BY f.severity DESC
        """
        records = await self.run_query(cypher, {"target": target})
        return [r["f"] for r in records]

    async def clear_all(self) -> None:
        """Delete all nodes and relationships. Use with caution."""
        async with self.driver.session() as session:
            await session.run("MATCH (n) DETACH DELETE n")
        logger.warning("All graph data cleared")


def _looks_like_ip(value: str) -> bool:
    parts = value.split(".")
    if len(parts) != 4:
        return False
    return all(p.isdigit() and 0 <= int(p) <= 255 for p in parts)
