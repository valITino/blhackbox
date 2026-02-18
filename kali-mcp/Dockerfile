# Kali Linux MCP Server for blhackbox
# Based on k3nn3dy-ai/kali-mcp architecture
# Provides MCP-accessible security tools in a Docker container

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

# Install Python MCP SDK
RUN python3 -m venv /app/venv && \
    /app/venv/bin/pip install --no-cache-dir mcp httpx

COPY server.py /app/server.py

USER kali-runner

ENTRYPOINT ["/app/venv/bin/python3", "/app/server.py"]
