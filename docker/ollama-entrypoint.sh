#!/bin/bash
# Ollama entrypoint: starts the server, pulls the model, and sends a warmup
# request so the model is already loaded in memory before any agent calls.
#
# Without this, the first agent request triggers a cold-start model download
# + load, which can take 10-20 minutes.

set -e

MODEL="${OLLAMA_MODEL:-llama3.1:8b}"

# Start the Ollama server in the background
echo "[*] Starting Ollama server..."
ollama serve &
OLLAMA_PID=$!

# Wait for the server to become responsive
echo "[*] Waiting for Ollama server to be ready..."
MAX_WAIT=60
WAITED=0
while [ "$WAITED" -lt "$MAX_WAIT" ]; do
    if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
        echo "[+] Ollama server is ready (took ~${WAITED}s)"
        break
    fi
    sleep 2
    WAITED=$((WAITED + 2))
done

if [ "$WAITED" -ge "$MAX_WAIT" ]; then
    echo "[!] Ollama server did not respond within ${MAX_WAIT}s"
fi

# Pull the model if not already present.
# This is a no-op if the model is already cached in the volume.
echo "[*] Ensuring model '${MODEL}' is available..."
ollama pull "$MODEL" 2>&1 || echo "[!] Failed to pull model ${MODEL} — may already be present"

# Warmup: send a tiny request to load the model into memory.
# The keep_alive ensures it stays loaded for subsequent agent requests.
echo "[*] Warming up model '${MODEL}'..."
curl -s http://localhost:11434/api/chat -d "{
  \"model\": \"${MODEL}\",
  \"messages\": [{\"role\": \"user\", \"content\": \"hi\"}],
  \"stream\": false,
  \"keep_alive\": \"60m\"
}" > /dev/null 2>&1 && echo "[+] Model '${MODEL}' is warm and loaded" \
    || echo "[!] Warmup request failed — model will load on first agent call"

# Bring the Ollama server to foreground
echo "[+] Ollama ready. Model '${MODEL}' is pre-loaded."
wait $OLLAMA_PID
