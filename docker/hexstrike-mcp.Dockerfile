# HexStrike MCP Server for blhackbox
#
# Uses the official hexstrike_mcp.py (100+ tools) from the hexstrike-ai
# submodule, wrapped with an SSE transport entrypoint for Docker.
#
# Architecture:
#   hexstrike-mcp/server.py  (SSE entrypoint)
#     -> imports hexstrike_mcp.py (upstream MCP server with 100+ tools)
#       -> HTTP calls to hexstrike:8888 (Flask REST API)
#
# Transport: FastMCP SSE on port 9005.
# Build context: repository root

FROM python:3.13-slim
WORKDIR /app

# Install upstream hexstrike requirements (FastMCP, requests, etc.)
COPY hexstrike/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy the upstream hexstrike MCP server (100+ tools, full implementation)
COPY hexstrike/hexstrike_mcp.py /app/hexstrike_mcp.py

# Copy our SSE transport wrapper
COPY hexstrike-mcp/server.py /app/server.py

EXPOSE 9005

ENV MCP_PORT=9005
ENV MCP_HOST=0.0.0.0
ENV HEXSTRIKE_URL=http://hexstrike:8888

CMD ["python3", "/app/server.py"]
