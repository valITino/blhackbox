"""StructureAgent — merges all agent outputs into a single AggregatedPayload."""

from __future__ import annotations

from blhackbox.agents.base_agent import BaseAgent


class StructureAgent(BaseAgent):
    """Merges outputs from all preceding agents into one coherent JSON object.

    Resolves conflicts, deduplicates across agents, and adds metadata.
    """

    agent_name: str = "structure_agent"
