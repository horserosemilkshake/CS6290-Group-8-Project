# CS6290 Group 8 - Adversarially-Robust DeFi Swap Agent

AI agent that converts natural-language cryptocurrency swap requests into unsigned transaction plans, with layered guardrails against prompt injection, excessive agency, and unsafe swap parameters.

This project intentionally favors a small, well-tested security envelope over a
larger but weakly verified feature surface. In particular, the current MVP
supports plain-language swap intents and rejects untrusted execution-control
overrides such as manual slippage, router, recipient, deadline, gas, or
user-supplied price directives unless they are added later with their own
verified normalization and policy path.

## Architecture

`User -> Telegram Bot -> FastAPI Agent API -> L1 -> LLM -> Tool Coordinator -> L2 -> [L3 eth_call] -> TxPlan`

| Component | Location | Description |
| --- | --- | --- |
| Agent API | `agent_client/` | FastAPI backend for planning requests |
| L1 Guardrails | `agent_client/src/agents/` | Input sanitization and output validation |
| L2 Policy Engine | `policy_engine/` | Deterministic router/token/slippage/value checks |
| L3 On-Chain | `contracts/` + `policy_engine/l3_validator.py` | `SwapGuard` contract validated via `eth_call` |
| Telegram Bot | `telegram_bot/` | Optional chat frontend |
| Harness | `harness/` + `scripts/` | ASR / FP / TR evaluation pipeline |
| Report Assets | `report-latex/` | Final paper source, figures, tables |
| Presentation | `report-beamer/` | Beamer slides for final presentation |

## Security Posture

- Plain swap intents are supported: token pair, amount, and chain scope.
- Unsafe request-side execution overrides are rejected by design.
- `TxPlan` remains unsigned and pauses at an explicit owner-action boundary.
- L3 is used as an additional mirror of deterministic checks, not as a reason to weaken L1/L2.

## Defense Configurations

| Config | Env Value | Meaning |
| --- | --- | --- |
| Config0 | `bare` | No guardrails |
| Config1 | `l1` | L1 only |
| Config2 | `l1l2` | L1 + L2 |
| Config3 | `l1l2l3` | L1 + L2 + L3 (`SwapGuard`) |

## Current Canonical Results

Latest checked-in comparison artifact on the final 125-case dataset:

| Config | ASR | FP | TR (max) |
| --- | ---: | ---: | ---: |
| `bare` | 84.00% | 0.00% | 4.2929s |
| `l1` | 25.00% | 0.00% | 3.1442s |
| `l1l2` | 0.00% | 0.00% | 3.0779s |
| `l1l2l3` | 0.00% | 0.00% | 2.9626s |

Artifacts live under `artifacts/final_results/`.

If you change guardrails or policy logic, treat these numbers as stale until
you rerun the final pipeline and refresh the committed artifacts.

## Quick Start

### 1. Install dependencies

```powershell
pip install -r agent_client/src/agent_requirements.txt
pip install -r requirements-dev.txt
```

### 2. Configure environment

Create a project-root `.env` from [`.env.example`](./.env.example).

Minimum variables:

```dotenv
OPENAI_API_KEY=sk-your-key-here
OPENAI_BASE_URL=https://api.deepseek.com
LLM_MODEL_NAME=deepseek-chat
DEFENSE_CONFIG=l1l2
REAL_TOOLS=false
```

### 3. Start the agent API

```powershell
$env:PYTHONPATH = "."
python -m uvicorn agent_client.src.main:app --port 8000
```

### 4. Run tests

```powershell
python -m pytest tests -v
```

## Reproducibility Pipeline

The final benchmark dataset is fixed at
`testcases/final_attack_dataset.json`. For final reporting, prefer freezing
the dataset and rerunning the pipeline instead of mutating the benchmark cases
to chase better metrics.

### Archived / deterministic

```powershell
$env:PYTHONPATH = "."
python scripts/run_integration_test.py
```

### Live 4-config comparison

```powershell
./scripts/start-chain.sh local

$env:PYTHONPATH = "."
$env:REAL_TOOLS = "false"
$env:DEFENSE_CONFIG = "bare"
$env:SWAP_GUARD_ADDRESS = "0x5FbDB2315678afecb367f032d93F642f64180aa3"
python -m uvicorn agent_client.src.main:app --port 8000

$env:PYTHONPATH = "."
python scripts/run_integration_test.py --mode live
```

This regenerates:

- `artifacts/final_results/`
- `report-latex/figures/`
- `docs/threat-model/final_threat_model.md`

Optional hardening for prototype control-plane routes:

```powershell
$env:CONTROL_PLANE_TOKEN = "change-me"
$env:WALLET_HANDOFF_TOKEN = "change-me-too"
```

When these are set, `/v0/defense-config` requires `X-Control-Token` and
`/v0/wallet/handoffs/*` requires `X-Wallet-Handoff-Token`.

## Presentation Paths

For the final presentation, use two demo paths:

1. `Sepolia` as the preferred public-chain demo path
2. `Anvil local` as the fast, reproducible fallback path

Why both:

- `Sepolia` is better for credibility because the audience can inspect the deployed contract and calls on a public testnet.
- `Anvil local` is better for rehearsal reliability and last-minute recovery if RPC, faucet, or public-network issues appear.

Recommended presentation split:

- Main benchmark story: deterministic mode with committed artifacts
- Main live demo: `Sepolia`
- Fallback demo: `Anvil local`

Detailed operator steps live in:

- [`docs/project-management/demo-runbook.md`](./docs/project-management/demo-runbook.md)
- [`docs/project-management/final-readiness-audit.md`](./docs/project-management/final-readiness-audit.md)

## Real Tools Integration Smoke

Use this only for integration validation or live demo rehearsals, not for canonical benchmark numbers.

Server:

```powershell
$env:PYTHONPATH = "."
$env:REAL_TOOLS = "true"
$env:REAL_TOOLS_STRICT = "true"
$env:ONEINCH_API_KEY = "your-1inch-api-key"
$env:COINGECKO_DEMO_API_KEY = "your-coingecko-demo-key"
python -m uvicorn agent_client.src.main:app --port 8000
```

Smoke test:

```powershell
$env:PYTHONPATH = "."
python scripts/run_real_tools_smoke.py --config l1l2
```

`REAL_TOOLS_STRICT=true` is important: the backend will fail closed instead of silently falling back to mock quotes.

Guarded benchmark:

```powershell
$env:PYTHONPATH = "."
python scripts/run_real_tools_benchmark.py --config l1l2 --repeat 2
```

This writes a small live benchmark artifact under `artifacts/real_tools_benchmark/`. It is useful for integration validation, but it is not the canonical reproducible experiment path.

## L2/L3 Parity Check

Use this to compare the current Python L2 policy configuration against a
deployed `SwapGuard` contract:

```powershell
$env:SWAP_GUARD_ADDRESS = "0x..."
python scripts/check_policy_parity.py --strict
```

This writes `artifacts/final_results/policy_parity_report.json`.

## Demo Tips

- `GET /v0/health` now reports `defense_config` and tool runtime status.
- `GET /v0/health` also reports wallet-bridge runtime state for signer-boundary demos.
- `GET /v0/health` now also reports whether optional control-plane route tokens are enabled.
- Real-tool responses now carry `tool_audit` metadata in `tx_plan`, including source, endpoint, latency, and fallback reason.
- `TxPlan` now includes `slippage_bounds`, `quote_validity`, and `wallet_handoff`, so demos can show quote freshness and explicit owner-action pause.
- For a stable presentation, keep the main benchmark on `REAL_TOOLS=false` and use `scripts/run_real_tools_smoke.py` as the live external-integration check.
- For the final live demo, prefer `Sepolia` first and keep `Anvil local` ready as a fallback.

## Key Paths

| Path | Purpose |
| --- | --- |
| `testcases/final_attack_dataset.json` | Frozen final 125-case benchmark dataset |
| `testcases/real_tools_smoke_cases.json` | Small benign suite for real API smoke checks |
| `scripts/run_integration_test.py` | Main reproducibility pipeline |
| `scripts/run_real_tools_smoke.py` | Real CoinGecko + 1inch smoke test |
| `scripts/run_real_tools_benchmark.py` | Guarded live benchmark for real-tool integration |
| `scripts/check_policy_parity.py` | Compare deployed `SwapGuard` settings with Python L2 config |
| `report-latex/CS6290-project-template.tex` | Report source |
| `docs/specification/` | Requirements and traceability source documents |
