# Kali Linux MCP Server for blhackbox
# Provides MCP-accessible security tools in a Docker container.
# Adapted from community Kali MCP servers (k3nn3dy-ai/kali-mcp).
# Transport: FastMCP SSE on port 9001.
# Build context: repository root

FROM kalilinux/kali-rolling

# Install ALL security tools referenced in the server.py allowlist.
# Must match the ALLOWED_TOOLS list in kali-mcp/server.py.
RUN apt-get update && apt-get install -y --no-install-recommends \
    nmap \
    nikto \
    gobuster \
    dirb \
    whatweb \
    wafw00f \
    masscan \
    hydra \
    sqlmap \
    wpscan \
    subfinder \
    amass \
    fierce \
    dnsenum \
    whois \
    curl \
    python3 \
    python3-pip \
    python3-venv \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements first for better layer caching
COPY kali-mcp/requirements.txt /app/requirements.txt

# Install Python MCP SDK in a venv
RUN python3 -m venv /app/venv && \
    /app/venv/bin/pip install --no-cache-dir -r /app/requirements.txt

# Copy server code
COPY kali-mcp/server.py /app/server.py

EXPOSE 9001

ENTRYPOINT ["/app/venv/bin/python3", "/app/server.py"]
