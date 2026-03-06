# Kali Linux MCP Server for blhackbox
# Provides MCP-accessible security tools in a Docker container.
# Adapted from community Kali MCP servers (k3nn3dy-ai/kali-mcp).
# Includes Metasploit Framework (msfconsole, msfvenom) — no separate
# metasploit-mcp container needed.
# Transport: FastMCP SSE on port 9001.
# Build context: repository root

FROM kalilinux/kali-rolling

# Install the full Kali security toolchain referenced in kali-mcp/server.py.
# Grouped by category — must stay in sync with the ALLOWED_TOOLS allowlist.
#
# NOTE: metasploit-framework is included here.  Metasploit tools in the MCP
# server use `msfconsole -qx` (CLI) instead of msfrpcd (RPC daemon), so
# there is no need for a separate metasploit-mcp container.
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
    host \
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
    # --- Metasploit Framework ---
    metasploit-framework \
    postgresql \
    locales \
    iproute2 \
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
    # --- Wordlists (required by dirb, gobuster, wpscan, etc.) ---
    wordlists \
    seclists \
    && rm -rf /var/lib/apt/lists/*

# Generate en_US.UTF-8 locale — PostgreSQL's initdb requires a valid locale.
RUN sed -i '/en_US.UTF-8/s/^# //' /etc/locale.gen && locale-gen
ENV LANG=en_US.UTF-8
ENV LC_ALL=en_US.UTF-8

# Ensure wordlists are decompressed and accessible at standard paths
RUN [ -f /usr/share/wordlists/rockyou.txt.gz ] && \
    gunzip /usr/share/wordlists/rockyou.txt.gz || true

# Symlink theHarvester -> theharvester for backward compatibility (Issue #16)
RUN ln -sf "$(which theHarvester 2>/dev/null || echo /usr/bin/theHarvester)" \
    /usr/local/bin/theharvester 2>/dev/null || true

# Kali installs ProjectDiscovery httpx as "httpx-toolkit" to avoid conflict
# with the Python httpx CLI. Create a symlink so "httpx" also works. (Issue #14)
RUN ln -sf "$(which httpx-toolkit 2>/dev/null || echo /usr/bin/httpx-toolkit)" \
    /usr/local/bin/httpx 2>/dev/null || true

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

# Copy requirements first for better layer caching
COPY kali-mcp/requirements.txt /app/requirements.txt

# Install Python MCP SDK in a venv
RUN python3 -m venv /app/venv && \
    /app/venv/bin/pip install --no-cache-dir -r /app/requirements.txt

# Copy server code and entrypoint
COPY kali-mcp/server.py /app/server.py
COPY kali-mcp/entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

EXPOSE 9001

ENTRYPOINT ["/app/entrypoint.sh"]
