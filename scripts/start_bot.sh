#!/bin/bash
# Start the Telegram Bot using uv
# Usage: ./scripts/start_bot.sh

set -e

cd "$(dirname "$0")/.."

echo "🤖 Starting Telegram Bot..."
echo "   Owner ID: $OWNER_TELEGRAM_ID"
echo "   Agent API: $AGENT_API_BASE_URL"
echo ""

# Check if Agent API is reachable
if ! curl -s http://localhost:8000/v0/health > /dev/null 2>&1; then
    echo "⚠️  Warning: Agent API is not running at http://localhost:8000"
    echo "   Please start the Agent first: ./scripts/start_agent.sh"
    echo ""
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Use uv run to execute with the virtual environment
uv run python -m telegram_bot.main
