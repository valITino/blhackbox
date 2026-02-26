# Kali Linux MCP Server for blhackbox
# Provides MCP-accessible security tools in a Docker container.
# Adapted from community Kali MCP servers (k3nn3dy-ai/kali-mcp).
# Transport: FastMCP SSE on port 9001.
# Build context: repository root

FROM kalilinux/kali-rolling

# Install the full Kali security toolchain referenced in kali-mcp/server.py.
# Grouped by category — must stay in sync with the ALLOWED_TOOLS allowlist.
#
# NOTE: rustscan, katana, paramspider, and dalfox are NOT in the Kali apt
# repos and are installed separately from GitHub releases / pip below.
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
    httpx-toolkit \
    arjun \
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
    enum4linux-ng \
    responder \
    netexec \
    # --- Wireless ---
    aircrack-ng \
    wifite \
    bettercap \
    # --- Forensics / Binary ---
    binwalk \
    foremost \
    libimage-exiftool-perl \
    steghide \
    hashid \
    binutils \
    # --- Utilities ---
    curl \
    wget \
    netcat-openbsd \
    socat \
    sshpass \
    proxychains4 \
    unzip \
    python3 \
    python3-pip \
    python3-venv \
    && rm -rf /var/lib/apt/lists/*

# Tools not in Kali apt repos — installed from GitHub releases or pip.
# Follows the same pattern for each: download, extract, place in /usr/local/bin.

# rustscan — high-speed port scanner (Rust)
RUN RUSTSCAN_VERSION="2.4.1" && \
    curl -sL "https://github.com/bee-san/RustScan/releases/download/${RUSTSCAN_VERSION}/x86_64-linux-rustscan.zip" \
    -o /tmp/rustscan.zip && \
    unzip -jo /tmp/rustscan.zip -d /tmp/rustscan && \
    find /tmp/rustscan -name 'rustscan' -type f -exec mv {} /usr/local/bin/rustscan \; && \
    chmod +x /usr/local/bin/rustscan && \
    rm -rf /tmp/rustscan.zip /tmp/rustscan

# katana — next-generation web crawler (Go, ProjectDiscovery)
RUN KATANA_VERSION="1.4.0" && \
    curl -sL "https://github.com/projectdiscovery/katana/releases/download/v${KATANA_VERSION}/katana_${KATANA_VERSION}_linux_amd64.zip" \
    -o /tmp/katana.zip && \
    unzip -jo /tmp/katana.zip katana -d /usr/local/bin/ && \
    chmod +x /usr/local/bin/katana && \
    rm -f /tmp/katana.zip

# dalfox — XSS scanner (Go)
RUN DALFOX_VERSION="2.9.3" && \
    curl -sL "https://github.com/hahwul/dalfox/releases/download/v${DALFOX_VERSION}/dalfox_${DALFOX_VERSION}_linux_amd64.tar.gz" \
    | tar xz -C /usr/local/bin dalfox

# paramspider — parameter discovery from web archives (Python)
RUN pip3 install --no-cache-dir --break-system-packages paramspider

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
