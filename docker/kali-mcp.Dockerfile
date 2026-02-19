# Kali Linux MCP Server for blhackbox
# Provides MCP-accessible security tools in a Docker container
# Build context: repository root

FROM kalilinux/kali-rolling
RUN apt-get update && apt-get install -y \
    nmap nikto gobuster dirb whatweb wafw00f \
    masscan hydra sqlmap wpscan python3 python3-pip python3-venv \
    && apt-get clean && rm -rf /var/lib/apt/lists/*
COPY kali-mcp/ /app/
WORKDIR /app
RUN python3 -m venv /app/venv && /app/venv/bin/pip install --no-cache-dir -r requirements.txt
CMD ["/app/venv/bin/python3", "server.py"]
