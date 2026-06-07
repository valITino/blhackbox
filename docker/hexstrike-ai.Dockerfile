# Optional HexStrike AI Gamma API container for blhackbox.
# This image capsules the upstream gamma repo behind an optional compose profile.
FROM kalilinux/kali-rolling

ARG HEXSTRIKE_REPO=https://github.com/valITino/hexstrike-ai_gamma.git
ARG HEXSTRIKE_REF=master

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HEXSTRIKE_PORT=8888

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    git \
    python3 \
    python3-pip \
    python3-venv \
    python3-flask \
    python3-requests \
    python3-psutil \
    python3-bs4 \
    python3-selenium \
    python3-aiohttp \
    python3-bcrypt \
    python3-pwntools \
    python3-angr \
    mitmproxy \
    nmap \
    gobuster \
    dirb \
    nikto \
    sqlmap \
    hydra \
    john \
    hashcat \
    ffuf \
    feroxbuster \
    dirsearch \
    whatweb \
    wafw00f \
    wpscan \
    nuclei \
    subfinder \
    amass \
    fierce \
    dnsenum \
    theharvester \
    binwalk \
    foremost \
    exiftool \
    steghide \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /opt
RUN git clone --depth 1 --branch "${HEXSTRIKE_REF}" "${HEXSTRIKE_REPO}" hexstrike-ai

WORKDIR /opt/hexstrike-ai
RUN python3 -m venv --system-site-packages /opt/hexstrike-venv && \
    /opt/hexstrike-venv/bin/pip install --no-cache-dir --upgrade pip && \
    /opt/hexstrike-venv/bin/pip install --no-cache-dir \
        "fastmcp>=0.2.0,<1.0.0" \
        "webdriver-manager>=4.0.0,<5.0.0"

EXPOSE 8888

ENTRYPOINT ["/opt/hexstrike-venv/bin/python", "/opt/hexstrike-ai/hexstrike_server.py", "--port", "8888"]
