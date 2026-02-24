# Kali Linux MCP Server for blhackbox
# Based on k3nn3dy-ai/kali-mcp architecture
# Provides MCP-accessible security tools in a Docker container
# NOTE: The primary Dockerfile used by docker-compose is docker/kali-mcp.Dockerfile.
# This file is for standalone builds from the kali-mcp/ directory.

FROM kalilinux/kali-rolling:latest

# Install the full Kali security toolchain (must stay in sync with docker/kali-mcp.Dockerfile)
RUN apt-get update && apt-get install -y --no-install-recommends \
    nmap \
    masscan \
    netdiscover \
    arp-scan \
    traceroute \
    hping3 \
    subfinder \
    amass \
    fierce \
    dnsenum \
    dnsrecon \
    dnsutils \
    whois \
    theharvester \
    nikto \
    gobuster \
    dirb \
    dirsearch \
    ffuf \
    feroxbuster \
    whatweb \
    wafw00f \
    wpscan \
    arjun \
    dalfox \
    sqlmap \
    hydra \
    medusa \
    john \
    hashcat \
    crackmapexec \
    evil-winrm \
    smbclient \
    enum4linux \
    responder \
    netexec \
    aircrack-ng \
    bettercap \
    binwalk \
    foremost \
    exiftool \
    steghide \
    hashid \
    curl \
    wget \
    netcat-openbsd \
    socat \
    sshpass \
    proxychains4 \
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
