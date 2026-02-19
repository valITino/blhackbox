# blhackbox Agent 1: Ingestion
# Parses raw tool output into structured typed data.
# Calls Ollama /api/chat with the ingestion system prompt.

FROM python:3.13-slim
WORKDIR /app
COPY blhackbox/agents/ /app/blhackbox/agents/
COPY blhackbox/prompts/agents/ /app/blhackbox/prompts/agents/
COPY blhackbox/__init__.py /app/blhackbox/__init__.py
RUN pip install --no-cache-dir fastapi uvicorn httpx pydantic
EXPOSE 8001
CMD ["python3", "-m", "blhackbox.agents.ingestion_server"]
