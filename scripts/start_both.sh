#!/bin/bash
# Start both Agent API and Telegram Bot using tmux
# Usage: ./scripts/start_both.sh

set -e

cd "$(dirname "$0")/.."

echo "🚀 Starting both Agent API and Telegram Bot..."
echo ""

# Check if tmux is installed
if ! command -v tmux &> /dev/null; then
    echo "❌ tmux is not installed. Please install it first:"
    echo "   brew install tmux  # macOS"
    echo "   apt-get install tmux  # Ubuntu/Debian"
    exit 1
fi

SESSION_NAME="defi-agent"

# Kill existing session if exists
tmux kill-session -t $SESSION_NAME 2>/dev/null || true

# Create new session
tmux new-session -d -s $SESSION_NAME -n "agent"

# Start Agent API in first window
tmux send-keys -t $SESSION_NAME:agent "./scripts/start_agent.sh" C-m

# Create second window for Bot
tmux new-window -t $SESSION_NAME -n "bot"
tmux send-keys -t $SESSION_NAME:bot "sleep 3 && ./scripts/start_bot.sh" C-m

# Attach to session
echo "✅ Both services started in tmux session: $SESSION_NAME"
echo ""
echo "Commands:"
echo "   tmux attach -t $SESSION_NAME    # Attach to session"
echo "   tmux ls                         # List sessions"
echo "   tmux kill-session -t $SESSION_NAME  # Stop all"
echo ""
echo "Inside tmux:"
echo "   Ctrl+B, N    # Switch to next window"
echo "   Ctrl+B, 0    # Switch to window 0 (Agent)"
echo "   Ctrl+B, 1    # Switch to window 1 (Bot)"
echo "   Ctrl+B, D    # Detach (services keep running)"
echo ""
read -p "Press Enter to attach to tmux session..."
tmux attach -t $SESSION_NAME
