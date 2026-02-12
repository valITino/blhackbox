# syntax=docker/dockerfile:1

# ---- Build stage ----
FROM python:3.13-slim-bookworm AS builder

WORKDIR /build

# Install build-time system dependencies and apply all available security patches
RUN apt-get update && apt-get upgrade -y && apt-get install -y --no-install-recommends \
    build-essential \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies into a virtual environment
# Pin pip/setuptools to patched versions to fix:
#   - setuptools <78.1.1: CVE-2025-47273, CVE-2024-6345
#   - pip <25.3: CVE-2025-8869; pip <26.0: CVE-2026-1703
COPY requirements.txt .
RUN python -m venv /opt/venv && \
    /opt/venv/bin/pip install --no-cache-dir --upgrade "pip>=26.0" "setuptools>=78.1.1" && \
    /opt/venv/bin/pip install --no-cache-dir -r requirements.txt

# Copy application code and install the package
COPY pyproject.toml setup.py ./
COPY blhackbox/ ./blhackbox/
RUN /opt/venv/bin/pip install --no-cache-dir .

# Remove build-only packages from the venv to reduce attack surface
# setuptools, wheel, and pip are not needed at runtime
RUN /opt/venv/bin/pip uninstall -y setuptools wheel pip

# ---- Runtime stage ----
FROM python:3.13-slim-bookworm

LABEL maintainer="Blhackbox Contributors"
LABEL org.opencontainers.image.source="https://github.com/crhacky/blhackbox"
LABEL org.opencontainers.image.description="Blhackbox - HexStrike Hybrid Autonomous Pentesting Framework"

# Runtime system dependencies only (no compilers, no git)
# apt-get upgrade applies all available security patches for system packages:
#   - libexpat1 (CVE-2024-45492, CVE-2024-45491, CVE-2024-8176, CVE-2024-45490, CVE-2023-52425)
#   - openssl (CVE-2024-5535, CVE-2025-9230, CVE-2025-69421, CVE-2025-69420, CVE-2024-4741)
#   - krb5 (CVE-2024-37371, CVE-2024-37370, CVE-2025-24528, CVE-2025-3576)
#   - glibc (CVE-2024-33599, CVE-2025-4802, CVE-2024-2961)
#   - systemd (CVE-2023-50868, CVE-2023-50387, CVE-2025-4598)
#   - perl (CVE-2023-31484, CVE-2025-40909, CVE-2024-56406)
#   - sqlite3 (CVE-2025-6965, CVE-2023-7104)
#   - pam (CVE-2025-6020, CVE-2024-22365)
#   - gnupg2 (CVE-2025-68973)
#   - gnutls28 (CVE-2025-6395, CVE-2025-32990, CVE-2025-32988, CVE-2024-28834, CVE-2024-12243)
#   - libtasn1-6 (CVE-2024-12133)
#   - libcap2 (CVE-2025-1390)
#   - shadow (CVE-2023-4641)
RUN apt-get update && apt-get upgrade -y && apt-get install -y --no-install-recommends \
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
