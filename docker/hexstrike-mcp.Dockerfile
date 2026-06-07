# Upstream HexStrike AI Gamma MCP server for blhackbox.
# The upstream MCP server content is cloned unchanged; this image only adds an
# SSE entrypoint so it can run like the other blhackbox MCP containers.
FROM python:3.11-slim

ARG HEXSTRIKE_REPO=https://github.com/valITino/hexstrike-ai_gamma.git
ARG HEXSTRIKE_REF=main

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HEXSTRIKE_PATH=/opt/hexstrike-ai \
    HEXSTRIKE_URL=http://hexstrike-ai:8888 \
    HEXSTRIKE_MCP_HOST=0.0.0.0 \
    HEXSTRIKE_MCP_PORT=9006

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /opt
RUN git clone --depth 1 --branch "${HEXSTRIKE_REF}" "${HEXSTRIKE_REPO}" hexstrike-ai

WORKDIR /opt/hexstrike-ai
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt "uvicorn>=0.30" "starlette>=0.37"

WORKDIR /app
COPY hexstrike-mcp/server.py /app/server.py

EXPOSE 9006

ENTRYPOINT ["python", "/app/server.py"]
