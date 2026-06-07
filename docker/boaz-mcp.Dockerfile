# Upstream BOAZ-MCP Gamma service for blhackbox.
# The upstream MCP server content is cloned unchanged; this image only adds an
# SSE entrypoint so it can run like the other blhackbox MCP containers.
FROM python:3.11-slim

ARG BOAZ_MCP_REPO=https://github.com/valITino/BOAZ-MCP_gamma.git
ARG BOAZ_MCP_REF=main
ARG BOAZ_REPO=https://github.com/valITino/BOAZ_gamma.git
ARG BOAZ_REF=main

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    BOAZ_MCP_PATH=/opt/BOAZ-MCP_gamma \
    BOAZ_PATH=/opt/BOAZ_gamma \
    BOAZ_MCP_HOST=0.0.0.0 \
    BOAZ_MCP_PORT=9005

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    git \
    python3 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /opt
RUN git clone --depth 1 --branch "${BOAZ_MCP_REF}" "${BOAZ_MCP_REPO}" BOAZ-MCP_gamma && \
    git clone --depth 1 --branch "${BOAZ_REF}" "${BOAZ_REPO}" BOAZ_gamma

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r /opt/BOAZ-MCP_gamma/boaz_mcp/requirements.txt \
    "uvicorn>=0.30" "starlette>=0.37"

WORKDIR /app
COPY boaz-mcp/server.py /app/server.py

EXPOSE 9005

ENTRYPOINT ["python", "/app/server.py"]
