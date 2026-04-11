#!/bin/bash
# Start the Agent API server using uv
# Usage: ./scripts/start_agent.sh

set -e

cd "$(dirname "$0")/.."

echo "🚀 Starting Agent API Server..."
echo "   Config: DEFENSE_CONFIG=$DEFENSE_CONFIG"
echo "   LLM: $LLM_MODEL_NAME"
echo ""

# Use uv run to execute with the virtual environment
uv run python -m uvicorn agent_client.src.main:app --host 0.0.0.0 --port 8000 --reload
