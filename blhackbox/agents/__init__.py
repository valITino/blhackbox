"""Ollama preprocessing agents for the blhackbox pipeline.

Three agents run sequentially:
  1. IngestionAgent  — parse raw tool output into structured data
  2. ProcessingAgent — deduplicate, compress, annotate error_log
  3. SynthesisAgent  — merge into final AggregatedPayload
"""

from blhackbox.agents.base_agent import BaseAgent
from blhackbox.agents.ingestion_agent import IngestionAgent
from blhackbox.agents.processing_agent import ProcessingAgent
from blhackbox.agents.synthesis_agent import SynthesisAgent

__all__ = [
    "BaseAgent",
    "IngestionAgent",
    "ProcessingAgent",
    "SynthesisAgent",
]
