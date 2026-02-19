# blhackbox Agent 2: Processing
# Deduplicates, compresses, and annotates ingested data.
# Calls Ollama via the official ollama Python package.

FROM python:3.13-slim
WORKDIR /app
COPY blhackbox/agents/ /app/blhackbox/agents/
COPY blhackbox/prompts/agents/ /app/blhackbox/prompts/agents/
COPY blhackbox/__init__.py /app/blhackbox/__init__.py
RUN pip install --no-cache-dir fastapi uvicorn ollama pydantic
EXPOSE 8002
CMD ["python3", "-m", "blhackbox.agents.processing_server"]
