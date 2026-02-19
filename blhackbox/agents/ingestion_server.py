"""Ingestion Agent — FastAPI container server.

Parses raw tool output into structured typed data.
Runs as a standalone container on port 8001.
"""

from blhackbox.agents.base_agent_server import run_agent

if __name__ == "__main__":
    run_agent("ingestionagent", port=8001)
