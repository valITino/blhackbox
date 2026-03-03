# Screenshot MCP Server for blhackbox
# Provides headless Chromium screenshot capture for bug bounty PoC
# evidence documentation during penetration testing engagements.
# Transport: FastMCP SSE on port 9004.
# Build context: repository root

FROM python:3.13-slim

# Install system dependencies for Playwright Chromium
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Playwright Chromium dependencies
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libdbus-1-3 \
    libxkbcommon0 \
    libatspi2.0-0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libpango-1.0-0 \
    libcairo2 \
    libasound2 \
    # Fonts for proper web page rendering
    fonts-dejavu-core \
    fonts-liberation \
    fonts-noto-color-emoji \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements and install Python dependencies
COPY screenshot-mcp/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Install Playwright browsers (Chromium only to minimize image size)
RUN playwright install chromium

# Copy server code
COPY screenshot-mcp/server.py /app/server.py

# Create screenshots directory
RUN mkdir -p /tmp/screenshots

EXPOSE 9004

ENTRYPOINT ["python3", "/app/server.py"]
