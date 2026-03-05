# Metasploit MCP Server for blhackbox
# Bundles the Metasploit Framework with msfrpcd and a FastMCP server.
# Provides 13+ MCP tools for exploit lifecycle management.
# Transport: FastMCP SSE on port 9002.
# Build context: repository root

FROM kalilinux/kali-rolling

# Install Metasploit Framework and dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    metasploit-framework \
    postgresql \
    curl \
    python3 \
    python3-pip \
    python3-venv \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements first for better layer caching
COPY metasploit-mcp/requirements.txt /app/requirements.txt

# Install Python MCP SDK in a venv
RUN python3 -m venv /app/venv && \
    /app/venv/bin/pip install --no-cache-dir -r /app/requirements.txt

# Copy server code and entrypoint
COPY metasploit-mcp/server.py /app/server.py
COPY metasploit-mcp/entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

EXPOSE 9002

ENTRYPOINT ["/app/entrypoint.sh"]
