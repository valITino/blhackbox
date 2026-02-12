FROM python:3.12-slim-bookworm

# System dependencies for weasyprint and general tooling
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf-2.0-0 \
    libffi-dev \
    libcairo2 \
    shared-mime-info \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies first (layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .
RUN pip install --no-cache-dir -e .

# Create non-root user for running scans
RUN useradd -m -s /bin/bash blhackbox
RUN chown -R blhackbox:blhackbox /app
USER blhackbox

ENTRYPOINT ["blhackbox"]
CMD ["--help"]
