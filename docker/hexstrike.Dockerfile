# HexStrike AI MCP Server for blhackbox
# Source: https://github.com/0x4m4/hexstrike-ai
# Build context: repository root
#
# NOTE: Only runtime dependencies for the MCP server are installed here.
# The submodule's requirements.txt includes heavy optional packages
# (angr, pwntools, mitmproxy, selenium) that require native compilation
# and are not needed for the MCP server to run.

FROM python:3.13-slim
WORKDIR /app
COPY hexstrike/ /app/hexstrike/
RUN pip install --no-cache-dir \
    "flask>=2.3.0,<4.0.0" \
    "requests>=2.31.0,<3.0.0" \
    "psutil>=5.9.0,<6.0.0" \
    "beautifulsoup4>=4.12.0,<5.0.0" \
    "aiohttp>=3.8.0,<4.0.0" \
    "mcp>=1.23.0"
EXPOSE 8888
CMD ["python3", "hexstrike/hexstrike_server.py", "--port", "8888"]
