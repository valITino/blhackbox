# HexStrike AI MCP Server for blhackbox
# Source: https://github.com/0x4m4/hexstrike-ai
# Build context: repository root

FROM python:3.13-slim
WORKDIR /app
COPY hexstrike/ /app/hexstrike/
RUN pip install --no-cache-dir -r hexstrike/requirements.txt
EXPOSE 8888
CMD ["python3", "hexstrike/hexstrike_server.py", "--port", "8888"]
