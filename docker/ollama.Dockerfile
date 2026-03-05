# Ollama with model pre-loading for blhackbox.
# Wraps the official Ollama image with an entrypoint that pulls and warms up
# the configured model on startup, eliminating cold-start delays.

FROM ollama/ollama:latest

COPY docker/ollama-entrypoint.sh /ollama-entrypoint.sh
RUN chmod +x /ollama-entrypoint.sh

ENTRYPOINT ["/ollama-entrypoint.sh"]
