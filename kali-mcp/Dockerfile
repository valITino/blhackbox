# Kali Linux MCP Server for blhackbox
# Based on k3nn3dy-ai/kali-mcp architecture
# Provides MCP-accessible security tools in a Docker container
# NOTE: The primary Dockerfile used by docker-compose is docker/kali-mcp.Dockerfile.
# This file is for standalone builds from the kali-mcp/ directory.

FROM kalilinux/kali-rolling:latest

# Install the full Kali security toolchain (must stay in sync with docker/kali-mcp.Dockerfile)
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
    paramspider \
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
    exiftool \
    steghide \
    hashid \
    binutils \
    # --- Screenshot / Evidence ---
    cutycapt \
    xvfb \
    # --- Utilities ---
    unzip \
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

# dalfox is not in Kali apt repos — install from GitHub release binary
RUN DALFOX_VERSION="2.9.3" && \
    curl -sL "https://github.com/hahwul/dalfox/releases/download/v${DALFOX_VERSION}/dalfox_${DALFOX_VERSION}_linux_amd64.tar.gz" \
    | tar xz -C /usr/local/bin dalfox

# rustscan is not in Kali apt repos — install from GitHub release .deb
RUN curl -sL "https://github.com/bee-san/RustScan/releases/download/2.4.1/rustscan.deb.zip" \
    -o /tmp/rustscan.deb.zip && \
    unzip -o /tmp/rustscan.deb.zip -d /tmp && \
    dpkg -i /tmp/rustscan_2.4.1-1_amd64.deb || true && \
    apt-get install -f -y && \
    rm -f /tmp/rustscan.deb.zip /tmp/rustscan_*.deb

# katana is not in Kali apt repos — install from GitHub release binary
RUN KATANA_VERSION="1.4.0" && \
    curl -sL "https://github.com/projectdiscovery/katana/releases/download/v${KATANA_VERSION}/katana_${KATANA_VERSION}_linux_amd64.zip" \
    -o /tmp/katana.zip && \
    unzip -o /tmp/katana.zip -d /usr/local/bin katana && \
    chmod +x /usr/local/bin/katana && \
    rm -f /tmp/katana.zip

WORKDIR /app

# Install Python MCP SDK
RUN python3 -m venv /app/venv && \
    /app/venv/bin/pip install --no-cache-dir mcp httpx

COPY server.py /app/server.py

EXPOSE 9001

ENTRYPOINT ["/app/venv/bin/python3", "/app/server.py"]
