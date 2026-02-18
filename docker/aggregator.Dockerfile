# syntax=docker/dockerfile:1

# blhackbox Aggregator MCP Server
# Custom Ollama preprocessing pipeline — NOT an official Ollama product.
# Uses Ollama's standard /api/chat endpoint as its LLM inference backend.
# Build context: repository root

# ---- Build stage ----
FROM python:3.13-slim-bookworm AS builder

WORKDIR /build

RUN apt-get update && apt-get upgrade -y && apt-get install -y --no-install-recommends \
    build-essential \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Install dependencies into a virtual environment
COPY requirements.txt .
RUN python -m venv /opt/venv && \
    /opt/venv/bin/pip install --no-cache-dir --upgrade "pip>=26.0" "setuptools>=78.1.1" && \
    /opt/venv/bin/pip install --no-cache-dir -r requirements.txt

# Remove build-only packages
RUN /opt/venv/bin/pip uninstall -y setuptools wheel pip

# ---- Runtime stage ----
FROM python:3.13-slim-bookworm

LABEL maintainer="Blhackbox Contributors"
LABEL org.opencontainers.image.description="blhackbox Aggregator MCP Server — Ollama preprocessing pipeline"

WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy application source (needed for imports and prompt .md files)
COPY blhackbox/ ./blhackbox/
COPY mcp_servers/ ./mcp_servers/

# Create non-root user
RUN useradd -m -r -s /usr/sbin/nologin aggregator && \
    chown -R aggregator:aggregator /app

USER aggregator

ENTRYPOINT ["python", "mcp_servers/blhackbox_aggregator_mcp.py"]
