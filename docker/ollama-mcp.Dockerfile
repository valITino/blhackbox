# blhackbox Ollama MCP Server
# Custom blhackbox component — NOT an official Ollama product.
# Calls 3 agent containers via HTTP. Uses FastMCP for tool schema generation.

FROM python:3.13-slim
WORKDIR /app
COPY blhackbox/ /app/blhackbox/
COPY mcp_servers/ /app/mcp_servers/
COPY requirements.txt pyproject.toml ./
RUN pip install --no-cache-dir "mcp>=1.2.0" httpx pydantic
CMD ["python3", "mcp_servers/ollama_mcp_server.py"]
