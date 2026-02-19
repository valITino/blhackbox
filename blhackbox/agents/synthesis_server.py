"""Synthesis Agent — FastAPI container server.

Merges Ingestion + Processing outputs into final AggregatedPayload.
Runs as a standalone container on port 8003.
"""

from blhackbox.agents.base_agent_server import run_agent

if __name__ == "__main__":
    run_agent("synthesisagent", port=8003)
