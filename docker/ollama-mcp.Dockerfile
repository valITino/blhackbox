# blhackbox Ollama MCP Server
# Custom blhackbox component — NOT an official Ollama product.
# Runs 3 preprocessing agents against Ollama's /api/chat endpoint.

FROM python:3.13-slim
WORKDIR /app
COPY blhackbox/ /app/blhackbox/
COPY mcp_servers/ /app/mcp_servers/
COPY requirements.txt pyproject.toml ./
RUN pip install --no-cache-dir -r requirements.txt mcp httpx pydantic
CMD ["python3", "mcp_servers/ollama_mcp_server.py"]
