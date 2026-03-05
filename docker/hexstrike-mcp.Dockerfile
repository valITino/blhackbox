# HexStrike MCP Server for blhackbox
#
# Uses the official hexstrike_mcp.py (100+ tools) from hexstrike-ai,
# wrapped with an SSE transport entrypoint for Docker.
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

# Add retries for transient network failures in build environments
RUN echo 'Acquire::Retries "5";' > /etc/apt/apt.conf.d/80-retries \
    && echo 'Acquire::http::Timeout "30";' >> /etc/apt/apt.conf.d/80-retries \
    && apt-get update \
    && apt-get install -y --no-install-recommends git g++ \
    && rm -rf /var/lib/apt/lists/*

# Clone hexstrike directly so the build is self-contained
# (no dependency on host submodule state)
ARG HEXSTRIKE_REPO=https://github.com/0x4m4/hexstrike-ai.git
ARG HEXSTRIKE_REF=33267047667b9accfbf0fdac1c1c7ff12f3a5512
RUN git clone --depth 1 "$HEXSTRIKE_REPO" /tmp/hexstrike \
    && cd /tmp/hexstrike && git fetch --depth 1 origin "$HEXSTRIKE_REF" \
    && git checkout "$HEXSTRIKE_REF" \
    && cp requirements.txt /app/requirements.txt \
    && cp hexstrike_mcp.py /app/hexstrike_mcp.py \
    && rm -rf /tmp/hexstrike

# Install upstream hexstrike requirements (FastMCP, requests, etc.)
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy our SSE transport wrapper
COPY hexstrike-mcp/server.py /app/server.py

EXPOSE 9005

ENV MCP_PORT=9005
ENV MCP_HOST=0.0.0.0
ENV HEXSTRIKE_URL=http://hexstrike:8888

CMD ["python3", "/app/server.py"]
