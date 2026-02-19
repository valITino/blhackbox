"""Processing Agent — deduplicates, compresses, and annotates ingested data.

Takes structured data from the Ingestion Agent, removes duplicates,
extracts errors/anomalies into an annotated error_log, and compresses
redundant data for optimal context window usage.
"""

from __future__ import annotations

from blhackbox.agents.base_agent import BaseAgent


class ProcessingAgent(BaseAgent):
    """Clean and compress the Ingestion Agent's structured output.

    Input: Ingestion Agent's structured output dict.
    Output: deduplicated + compressed data + annotated error_log
            with security_relevance and security_note fields.
    """
