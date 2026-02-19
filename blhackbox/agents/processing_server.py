"""Processing Agent — FastAPI container server.

Deduplicates, compresses, and annotates ingested data.
Runs as a standalone container on port 8002.
"""

from blhackbox.agents.base_agent_server import run_agent

if __name__ == "__main__":
    run_agent("processingagent", port=8002)
