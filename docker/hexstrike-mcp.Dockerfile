# HexStrike MCP Adapter for blhackbox
# Bridges the HexStrike Flask REST API to the MCP protocol.
# Transport: FastMCP SSE on port 9005.
# Build context: repository root

FROM python:3.13-slim
WORKDIR /app

COPY hexstrike-mcp/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY hexstrike-mcp/server.py /app/server.py

EXPOSE 9005

CMD ["python3", "/app/server.py"]
