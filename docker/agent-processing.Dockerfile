# blhackbox Agent 2: Processing
# Deduplicates, compresses, and annotates ingested data.
# Calls Ollama /api/chat with the processing system prompt.

FROM python:3.13-slim
WORKDIR /app
COPY blhackbox/agents/ /app/blhackbox/agents/
COPY blhackbox/prompts/agents/ /app/blhackbox/prompts/agents/
COPY blhackbox/__init__.py /app/blhackbox/__init__.py
RUN pip install --no-cache-dir fastapi uvicorn httpx pydantic
EXPOSE 8002
CMD ["python3", "-m", "blhackbox.agents.processing_server"]
