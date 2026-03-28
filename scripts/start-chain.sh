#!/usr/bin/env bash
# start-chain.sh — Unified local chain launcher for M3
#
# Usage:
#   ./scripts/start-chain.sh         # defaults to "local"
#   ./scripts/start-chain.sh local   # Anvil local (chain_id 31337)
#   ./scripts/start-chain.sh fork    # Anvil mainnet fork (chain_id 1)
#
# Prerequisites: foundry (anvil, forge) installed — https://getfoundry.sh
# Windows users: run via Git Bash.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
CONTRACTS_DIR="$PROJECT_ROOT/contracts"

# Load .env if present
if [[ -f "$PROJECT_ROOT/.env" ]]; then
    set -a
    source "$PROJECT_ROOT/.env"
    set +a
fi

MODE="${1:-local}"
PORT="${ANVIL_PORT:-8545}"
RPC_URL="http://127.0.0.1:$PORT"

start_local() {
    echo "==> Starting Anvil local chain (chain_id=31337) on port $PORT ..."
    anvil --port "$PORT" &
    ANVIL_PID=$!
    echo "    Anvil PID: $ANVIL_PID"
}

start_fork() {
    if [[ -z "${ETH_RPC_URL:-}" ]]; then
        echo "ERROR: ETH_RPC_URL not set. Required for fork mode."
        echo "       Set it in .env or export ETH_RPC_URL=https://..."
        exit 1
    fi
    BLOCK_FLAG=""
    if [[ -n "${FORK_BLOCK_NUMBER:-}" ]]; then
        BLOCK_FLAG="--fork-block-number $FORK_BLOCK_NUMBER"
    fi
    echo "==> Starting Anvil mainnet fork (chain_id=1) on port $PORT ..."
    echo "    RPC: $ETH_RPC_URL"
    [[ -n "${FORK_BLOCK_NUMBER:-}" ]] && echo "    Pinned block: $FORK_BLOCK_NUMBER"
    # shellcheck disable=SC2086
    anvil --fork-url "$ETH_RPC_URL" $BLOCK_FLAG --port "$PORT" &
    ANVIL_PID=$!
    echo "    Anvil PID: $ANVIL_PID"
}

deploy_contracts() {
    echo "==> Waiting for Anvil to be ready ..."
    for i in $(seq 1 30); do
        if cast block-number --rpc-url "$RPC_URL" &>/dev/null; then
            break
        fi
        sleep 0.5
    done

    if ! cast block-number --rpc-url "$RPC_URL" &>/dev/null; then
        echo "ERROR: Anvil did not become ready within 15s"
        exit 1
    fi

    echo "==> Deploying SwapGuard ..."
    DEPLOYER_KEY="0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"

    forge script "$CONTRACTS_DIR/script/Deploy.s.sol" \
        --rpc-url "$RPC_URL" \
        --private-key "$DEPLOYER_KEY" \
        --broadcast
}

cleanup() {
    echo ""
    echo "==> Shutting down Anvil (PID $ANVIL_PID) ..."
    kill "$ANVIL_PID" 2>/dev/null || true
    wait "$ANVIL_PID" 2>/dev/null || true
    echo "    Done."
}

# ── Main ──────────────────────────────────────────────────────────────────
case "$MODE" in
    local)
        start_local
        ;;
    fork)
        start_fork
        ;;
    *)
        echo "Unknown mode: $MODE"
        echo "Usage: $0 [local|fork]"
        exit 1
        ;;
esac

trap cleanup EXIT INT TERM

deploy_contracts

echo ""
echo "=========================================="
echo "  Anvil ($MODE) running on $RPC_URL"
echo "  Press Ctrl+C to stop"
echo "=========================================="

wait "$ANVIL_PID"
