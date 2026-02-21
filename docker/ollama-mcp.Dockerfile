# blhackbox Ollama MCP Server
# Custom blhackbox component — NOT an official Ollama product.
# Thin MCP orchestrator: calls 3 agent containers via HTTP, assembles
# AggregatedPayload. Uses FastMCP for tool schema generation.
# Transport: FastMCP SSE on port 9000.

FROM python:3.13-slim
WORKDIR /app
COPY blhackbox/ /app/blhackbox/
COPY mcp_servers/ /app/mcp_servers/
COPY requirements.txt pyproject.toml ./
RUN pip install --no-cache-dir "mcp>=1.23.0" httpx pydantic
EXPOSE 9000
CMD ["python3", "mcp_servers/ollama_mcp_server.py"]
