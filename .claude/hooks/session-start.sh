#!/bin/bash
set -euo pipefail

# Only run in remote (web) environments
if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

cd "$CLAUDE_PROJECT_DIR"

# Create virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi

# Install package with dev dependencies (editable mode)
.venv/bin/pip install -e ".[dev]" --quiet

# Create .env from example if it doesn't exist.
# API keys are commented out in .env.example — Claude Code provides its
# own authentication so ANTHROPIC_API_KEY is not needed here.
if [ ! -f ".env" ] && [ -f ".env.example" ]; then
  cp .env.example .env
fi

# Export venv bin to PATH for the session
echo "export PATH=\"$CLAUDE_PROJECT_DIR/.venv/bin:\$PATH\"" >> "$CLAUDE_ENV_FILE"
