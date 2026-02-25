# WireMCP Server for blhackbox
# Provides MCP-accessible tshark/Wireshark tools for packet capture
# and network traffic analysis.
# Transport: FastMCP SSE on port 9003.
# Build context: repository root

FROM debian:bookworm-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    tshark \
    tcpdump \
    net-tools \
    python3 \
    python3-pip \
    python3-venv \
    && rm -rf /var/lib/apt/lists/*

# Allow non-root users to capture packets
RUN setcap cap_net_raw,cap_net_admin+eip /usr/bin/dumpcap 2>/dev/null || true

WORKDIR /app

# Copy requirements first for better layer caching
COPY wire-mcp/requirements.txt /app/requirements.txt

# Install Python MCP SDK in a venv
RUN python3 -m venv /app/venv && \
    /app/venv/bin/pip install --no-cache-dir -r /app/requirements.txt

# Copy server code
COPY wire-mcp/server.py /app/server.py

# Create captures directory
RUN mkdir -p /tmp/captures

EXPOSE 9003

ENTRYPOINT ["/app/venv/bin/python3", "/app/server.py"]
