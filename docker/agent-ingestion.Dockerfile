# blhackbox Agent 1: Ingestion
# Parses raw tool output into structured typed data.
# Calls Ollama via the official ollama Python package.

FROM python:3.13-slim
WORKDIR /app
COPY blhackbox/agents/ /app/blhackbox/agents/
COPY blhackbox/prompts/agents/ /app/blhackbox/prompts/agents/
COPY blhackbox/__init__.py /app/blhackbox/__init__.py
RUN pip install --no-cache-dir fastapi uvicorn ollama pydantic
EXPOSE 8001
CMD ["python3", "-m", "blhackbox.agents.ingestion_server"]
