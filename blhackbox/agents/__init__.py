"""Ollama preprocessing agents for the blhackbox pipeline.

Three agents run sequentially as separate containers:
  1. IngestionAgent  — parse raw tool output into structured data
  2. ProcessingAgent — deduplicate, compress, annotate error_log
  3. SynthesisAgent  — merge into final AggregatedPayload

Each agent runs as a FastAPI HTTP server (see base_agent_server.py).
The BaseAgent class is kept for library/testing use.
"""

from blhackbox.agents.base_agent import BaseAgent
from blhackbox.agents.base_agent_server import BaseAgentServer
from blhackbox.agents.ingestion_agent import IngestionAgent
from blhackbox.agents.processing_agent import ProcessingAgent
from blhackbox.agents.synthesis_agent import SynthesisAgent

__all__ = [
    "BaseAgent",
    "BaseAgentServer",
    "IngestionAgent",
    "ProcessingAgent",
    "SynthesisAgent",
]
