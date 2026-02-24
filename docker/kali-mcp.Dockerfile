# Kali Linux MCP Server for blhackbox
# Provides MCP-accessible security tools in a Docker container.
# Adapted from community Kali MCP servers (k3nn3dy-ai/kali-mcp).
# Transport: FastMCP SSE on port 9001.
# Build context: repository root

FROM kalilinux/kali-rolling

# Install the full Kali security toolchain referenced in kali-mcp/server.py.
# Grouped by category — must stay in sync with the ALLOWED_TOOLS allowlist.
RUN apt-get update && apt-get install -y --no-install-recommends \
    # --- Network / Recon ---
    nmap \
    masscan \
    netdiscover \
    arp-scan \
    traceroute \
    hping3 \
    # --- DNS ---
    subfinder \
    amass \
    fierce \
    dnsenum \
    dnsrecon \
    dnsutils \
    whois \
    theharvester \
    # --- Web Application ---
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
    # --- Exploitation / Brute-force ---
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
    # --- Wireless ---
    aircrack-ng \
    bettercap \
    # --- Forensics / Binary ---
    binwalk \
    foremost \
    exiftool \
    steghide \
    hashid \
    # --- Utilities ---
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
