# syntax=docker/dockerfile:1

# ---- Build stage ----
FROM python:3.14.3-slim-bookworm AS builder

WORKDIR /build

# Install build-time system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies into a virtual environment
COPY requirements.txt .
RUN python -m venv /opt/venv && \
    /opt/venv/bin/pip install --no-cache-dir --upgrade pip setuptools && \
    /opt/venv/bin/pip install --no-cache-dir -r requirements.txt

# Copy application code and install the package
COPY pyproject.toml setup.py ./
COPY blhackbox/ ./blhackbox/
RUN /opt/venv/bin/pip install --no-cache-dir .

# ---- Runtime stage ----
FROM python:3.14.3-slim-bookworm

LABEL maintainer="Blhackbox Contributors"
LABEL org.opencontainers.image.source="https://github.com/crhacky/blhackbox"
LABEL org.opencontainers.image.description="Blhackbox - HexStrike Hybrid Autonomous Pentesting Framework"

# Runtime system dependencies only (no compilers, no git)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf-2.0-0 \
    libcairo2 \
    shared-mime-info \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get purge -y --auto-remove

WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy only the application code (no pyproject.toml, setup.py, tests, etc.)
COPY blhackbox/ ./blhackbox/

# Create non-root user for running scans
RUN useradd -m -r -s /usr/sbin/nologin blhackbox && \
    mkdir -p /app/results /app/wordlists && \
    chown -R blhackbox:blhackbox /app

USER blhackbox

# Healthcheck to verify the CLI is functional
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD ["python", "-c", "import blhackbox; print('ok')"]

ENTRYPOINT ["blhackbox"]
CMD ["--help"]
