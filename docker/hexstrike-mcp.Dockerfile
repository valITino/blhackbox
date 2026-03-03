# HexStrike MCP Server for blhackbox
# Thin MCP adapter over the HexStrike AI REST API.
# Translates MCP tool calls into HTTP requests against hexstrike:8888.
# Transport: FastMCP SSE on port 9005.
# Build context: repository root

FROM python:3.13-slim

WORKDIR /app

# Copy requirements first for better layer caching
COPY hexstrike-mcp/requirements.txt /app/requirements.txt

# Install Python MCP SDK and dependencies in a venv
RUN python3 -m venv /app/venv && \
    /app/venv/bin/pip install --no-cache-dir -r /app/requirements.txt

# Copy server code
COPY hexstrike-mcp/server.py /app/server.py

EXPOSE 9005

ENTRYPOINT ["/app/venv/bin/python3", "/app/server.py"]
