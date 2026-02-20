#!/bin/bash
set -euo pipefail

# Resolve project root from this script's location (.claude/ -> project root)
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

# Ensure virtual environment exists
if [ ! -d ".venv" ]; then
  python3 -m venv .venv 2>/dev/null
fi

# Ensure package is installed (entry point must exist)
if [ ! -f ".venv/bin/blhackbox" ]; then
  .venv/bin/pip install -e . --quiet 2>/dev/null
fi

# Load .env if present (for NEO4J_*, OLLAMA_*, etc.)
if [ -f ".env" ]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

exec .venv/bin/blhackbox mcp
