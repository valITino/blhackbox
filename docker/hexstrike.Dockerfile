# HexStrike AI MCP Server for blhackbox
# Source: https://github.com/0x4m4/hexstrike-ai
# Build context: repository root

FROM python:3.13-slim
WORKDIR /app

# Install build dependencies required by C-extension packages (msgpack, etc.)
RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc build-essential git \
    && rm -rf /var/lib/apt/lists/*

# Clone hexstrike directly so the build is self-contained
# (no dependency on host submodule state)
ARG HEXSTRIKE_REPO=https://github.com/0x4m4/hexstrike-ai.git
ARG HEXSTRIKE_REF=33267047667b9accfbf0fdac1c1c7ff12f3a5512
RUN git clone --depth 1 "$HEXSTRIKE_REPO" hexstrike \
    && cd hexstrike && git fetch --depth 1 origin "$HEXSTRIKE_REF" \
    && git checkout "$HEXSTRIKE_REF" \
    && rm -rf .git

RUN pip install --no-cache-dir -r hexstrike/requirements.txt
EXPOSE 8888
CMD ["python3", "hexstrike/hexstrike_server.py", "--port", "8888"]
