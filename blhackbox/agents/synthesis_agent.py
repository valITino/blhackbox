"""Synthesis Agent — merges all agent outputs into a single AggregatedPayload.

Final stage of the preprocessing pipeline. Combines Ingestion and Processing
agent outputs, resolves conflicts, and adds metadata.
"""

from __future__ import annotations

from blhackbox.agents.base_agent import BaseAgent


class SynthesisAgent(BaseAgent):
    """Merge Ingestion + Processing outputs into one AggregatedPayload.

    Input: dict containing ingestion_output and processing_output.
    Output: AggregatedPayload-compatible dict with findings, error_log,
            and metadata.
    """
