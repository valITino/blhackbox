# HexStrike AI MCP Server for blhackbox
# Source: https://github.com/0x4m4/hexstrike-ai
# Build context: repository root

FROM python:3.13-slim
WORKDIR /app

# Install build dependencies required by C-extension packages (msgpack, etc.)
RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY hexstrike/ /app/hexstrike/
RUN test -f hexstrike/requirements.txt \
    || { echo "ERROR: hexstrike/requirements.txt not found. Run 'git submodule update --init' first." >&2; exit 1; }
RUN pip install --no-cache-dir -r hexstrike/requirements.txt
EXPOSE 8888
CMD ["python3", "hexstrike/hexstrike_server.py", "--port", "8888"]
