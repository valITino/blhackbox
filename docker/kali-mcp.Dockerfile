# Kali Linux MCP Server for blhackbox
# Provides MCP-accessible security tools in a Docker container
# Build context: repository root

FROM kalilinux/kali-rolling:latest

# Install security tools
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

# Create non-root user for tool execution
RUN useradd -m -s /bin/bash kali-runner

WORKDIR /app

# Install Python MCP SDK in isolated venv
RUN python3 -m venv /app/venv && \
    /app/venv/bin/pip install --no-cache-dir mcp httpx

COPY kali-mcp/server.py /app/server.py

USER kali-runner

ENTRYPOINT ["/app/venv/bin/python3", "/app/server.py"]
