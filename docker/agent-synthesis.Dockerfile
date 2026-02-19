# blhackbox Agent 3: Synthesis
# Merges Ingestion + Processing outputs into final AggregatedPayload.
# Calls Ollama via the official ollama Python package.

FROM python:3.13-slim
WORKDIR /app
COPY blhackbox/agents/ /app/blhackbox/agents/
COPY blhackbox/prompts/agents/ /app/blhackbox/prompts/agents/
COPY blhackbox/__init__.py /app/blhackbox/__init__.py
RUN pip install --no-cache-dir fastapi uvicorn ollama pydantic
EXPOSE 8003
CMD ["python3", "-m", "blhackbox.agents.synthesis_server"]
