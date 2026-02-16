# syntax=docker/dockerfile:1

# ---- Build stage ----
FROM python:3.13-slim-bookworm AS builder

WORKDIR /build

# Install build-time system dependencies
RUN apt-get update && apt-get upgrade -y && apt-get install -y --no-install-recommends \
    build-essential \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies into a virtual environment
COPY hexstrike/requirements.txt .
RUN python -m venv /opt/venv && \
    /opt/venv/bin/pip install --no-cache-dir --upgrade "pip>=26.0" "setuptools>=78.1.1" && \
    /opt/venv/bin/pip install --no-cache-dir -r requirements.txt

# Remove build-only packages from the venv to reduce attack surface
RUN /opt/venv/bin/pip uninstall -y setuptools wheel pip

# ---- Runtime stage ----
FROM python:3.13-slim-bookworm

LABEL maintainer="HexStrike Contributors"
LABEL org.opencontainers.image.description="HexStrike AI MCP Server"

# Runtime system dependencies
RUN apt-get update && apt-get upgrade -y && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get purge -y --auto-remove

WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy application code
COPY hexstrike/hexstrike_server.py hexstrike/hexstrike_mcp.py hexstrike/hexstrike-ai-mcp.json ./

# Create non-root user
RUN useradd -m -r -s /usr/sbin/nologin hexstrike && \
    mkdir -p /app/data && \
    chown -R hexstrike:hexstrike /app

USER hexstrike

EXPOSE 8888

HEALTHCHECK --interval=15s --timeout=5s --start-period=30s --retries=5 \
    CMD ["curl", "-f", "http://localhost:8888/health"]

ENTRYPOINT ["python", "hexstrike_server.py"]
