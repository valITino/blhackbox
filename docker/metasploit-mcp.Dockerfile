# Metasploit MCP Server for blhackbox
# Bundles the Metasploit Framework with msfrpcd and a FastMCP server.
# Provides 13+ MCP tools for exploit lifecycle management.
# Transport: FastMCP SSE on port 9002.
# Build context: repository root

FROM kalilinux/kali-rolling

# Install Metasploit Framework and dependencies.
# - locales: Required for PostgreSQL initdb/pg_createcluster (fails without
#   a valid locale in minimal Docker images — "no usable system locales").
# - iproute2: Provides the `ss` command used by the healthcheck to verify
#   that msfrpcd is listening on port 55553.
RUN apt-get update && apt-get install -y --no-install-recommends \
    metasploit-framework \
    postgresql \
    curl \
    iproute2 \
    locales \
    python3 \
    python3-pip \
    python3-venv \
    && rm -rf /var/lib/apt/lists/*

# Generate en_US.UTF-8 locale — PostgreSQL's initdb requires a valid locale.
# Without this, pg_createcluster fails with "no usable system locales were found"
# inside minimal Docker images like kali-rolling.
RUN sed -i '/en_US.UTF-8/s/^# //' /etc/locale.gen && locale-gen
ENV LANG=en_US.UTF-8
ENV LC_ALL=en_US.UTF-8

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
