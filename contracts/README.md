# L3 On-Chain Enforcement (SwapGuard)

Solidity contracts for on-chain swap validation, mirroring a subset of L2 policy-engine rules.

## Prerequisites

Install [Foundry](https://getfoundry.sh):

```bash
# macOS / Linux
curl -L https://foundry.paradigm.xyz | bash
foundryup

# Windows (via Git Bash)
curl -L https://foundry.paradigm.xyz | bash
source ~/.bashrc
foundryup
```

Verify installation:

```bash
forge --version   # expect 1.x.x
anvil --version
cast --version
```

## Quick Start

### 1. Build contracts

```bash
cd contracts
forge build
```

### 2. Run tests

```bash
forge test -vvv
```

### 3. Start local chain + deploy

From the **project root**:

```bash
# Local Anvil (chain_id=31337, no external dependencies)
./scripts/start-chain.sh local

# Mainnet fork (chain_id=1, requires ETH_RPC_URL in .env)
./scripts/start-chain.sh fork
```

Windows users: run these commands in **Git Bash**.

The script will:
1. Start Anvil (local or fork mode)
2. Deploy `SwapGuard` with seeded allowlists
3. Print the contract address
4. Keep running until Ctrl+C

### 4. Run Agent with L3 (Config3)

To run the full pipeline (L1 → L2 → L3 → TxPlan):

1. Start chain and deploy: `./scripts/start-chain.sh local` (from project root). Copy the printed contract address.
2. In project root `.env`: set `DEFENSE_CONFIG=l1l2l3` and `SWAP_GUARD_ADDRESS=<that address>`.
3. Start the agent: `uvicorn agent_client.src.main:app`.
4. Send requests to `POST /v0/agent/plan`; L3 validation runs automatically when configured.

### 5. Gas report

```bash
cd contracts
forge test --gas-report
```

## Contract: SwapGuard

Enforces three rules as view-function pre-flight checks:

| Rule | Check | Revert message |
|------|-------|---------------|
| R-01 | Token allowlist (sell + buy) | `R-01: sell token not allowed` / `R-01: buy token not allowed` |
| R-02 | Router allowlist | `R-02: router not allowed` |
| R-04 | Per-tx value cap | `R-04: value exceeds cap` |

### Key design decisions

- **`NATIVE_ETH`**: ETH is not ERC-20. The contract uses the 1inch sentinel address `0xEeee...eEEeE` to represent native ETH in the token allowlist.
- **`ethEquivalentValue`**: The value parameter is NOT `tx.value`. It is the ETH-equivalent value computed off-chain by the Python wrapper (same logic as L2 `check_value_cap()`). This ensures ERC-20 swaps are also capped.
- **`validateSwap` is `view`**: Called via `eth_call` (free, no gas cost) as a pre-flight check before submitting the real transaction.

## Directory structure

```
contracts/
├── foundry.toml          # Foundry config (solc 0.8.20, optimizer on)
├── src/
│   └── SwapGuard.sol     # L3 main contract
├── test/
│   └── SwapGuard.t.sol   # Solidity unit tests (Phase 2)
├── script/
│   └── Deploy.s.sol      # Deploy script (local / fork / sepolia)
└── lib/
    └── forge-std/        # Foundry standard library
```
