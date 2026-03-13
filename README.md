# CS6290 Group 8 — Adversarially-Robust DeFi Swap Agent

**Last Updated:** March 13, 2026

An AI agent that converts natural-language cryptocurrency swap requests into unsigned transaction plans, hardened with layered guardrails against prompt injection, excessive agency, and economic attacks.

## Architecture

```
User ─► Telegram Bot ─► FastAPI Agent API ─► L1 ─► LLM ─► Tool Coordinator ─► L2 Policy Engine ─► [L3 On-Chain] ─► TxPlan
```

| Component | Location | Description |
|-----------|----------|-------------|
| **Agent API** | `agent_client/` | FastAPI server; LLM intent parsing (DeepSeek / OpenAI-compatible) with mock DEX tool coordinator |
| **L1 Guardrails** | `agent_client/src/agents/` | Input sanitisation (injection detection, encoding attacks, length limits) + output validation |
| **L2 Policy Engine** | `policy_engine/` | Deterministic rules: token/router allowlist, slippage, value cap, unlimited approval, tx structure, chain scope |
| **L3 On-Chain** | `contracts/` + `policy_engine/l3_validator.py` | SwapGuard contract (R-01, R-02, R-04) via `eth_call`; optional, requires Anvil |
| **Telegram Bot** | `telegram_bot/` | Natural-language front-end; group-chat privacy (ALLOW details sent via owner DM only) |
| **Test Harness** | `harness/` | Automated red-team runner with ASR / FP / TR metrics |
| **Test Cases** | `testcases/` | 100 adversarial cases (`adv_100_cases.json`) covering injection, social engineering, encoding attacks, logic overrides |

## Defense Configurations

| Config | Flag | Guardrails |
|--------|------|------------|
| Config 0 (bare) | `DEFENSE_CONFIG=bare` | None — baseline |
| Config 1 (L1) | `DEFENSE_CONFIG=l1` | L1 input/output guardrails only |
| Config 2 (L1+L2) | `DEFENSE_CONFIG=l1l2` | L1 + L2 policy engine (default) |
| Config 3 (L1+L2+L3) | `DEFENSE_CONFIG=l1l2l3` | L1 + L2 + L3 on-chain (requires local Anvil + `SWAP_GUARD_ADDRESS`) |

**Latest 100-case adversarial results:**

| Config | ASR ↓ | FP | TR (max) |
|--------|-------|----|----------|
| bare | 75 % | 0 % | 3.86 s |
| l1 | 25 % | 0 % | 3.37 s |
| l1l2 | 14 % | 0 % | 3.69 s |

## Quick Start

### 1. Install dependencies

```bash
pip install -r agent_client/src/agent_requirements.txt
pip install -r requirements-dev.txt
```

### 2. Configure environment

Copy the example and fill in your keys — **one `.env` file in the project root** covers both Agent API and Telegram Bot:

```bash
cp .env.example .env
```

Required variables:

```dotenv
OPENAI_API_KEY=sk-your-key-here          # LLM API key (DeepSeek, OpenAI, etc.)
OPENAI_BASE_URL=https://api.deepseek.com  # optional: custom endpoint
LLM_MODEL_NAME=deepseek-chat              # optional: model name

TELEGRAM_BOT_TOKEN=123456:ABC-...         # from @BotFather (for Telegram bot only)
OWNER_TELEGRAM_ID=123456789               # your numeric Telegram user ID
```

### 3. Start the Agent API server

```bash
python -m uvicorn agent_client.src.main:app --port 8000
```

The API is available at `http://127.0.0.1:8000/v0/`. Key endpoints:

| Method | Path | Description |
|--------|------|-------------|
| POST | `/v0/agent/plan` | Submit a swap request |
| GET | `/v0/health` | Health check |
| GET / POST | `/v0/defense-config` | View / switch defense config |

### 4. Start the Telegram Bot (optional)

Requires the Agent API server to be running first:

```bash
python -m telegram_bot.main
```

### 5. Run unit tests

```bash
python -m pytest tests/ -v
```

### 6. Run the red-team harness

With the Agent API server running:

```bash
# Single config (default: l1l2)
python scripts/run_integration_test.py testcases/adv_100_cases.json --config l1l2

# All three configs with comparison report
python scripts/run_integration_test.py testcases/adv_100_cases.json --all-configs
```

Results and artifacts are saved to `artifacts/`.

### 7. Run with L3 on-chain (optional)

To enable Config3 (L1+L2+L3): install [Foundry](https://getfoundry.sh), then from the project root:

```bash
./scripts/start-chain.sh local   # start Anvil, deploy SwapGuard, copy printed address
# In .env: DEFENSE_CONFIG=l1l2l3, SWAP_GUARD_ADDRESS=<that address>
python -m uvicorn agent_client.src.main:app --port 8000
```

See `contracts/README.md` for details.

## Project Structure

```
├── agent_client/          # FastAPI agent (LLM + tools + L1 guardrails)
│   └── src/
│       ├── agents/        # L1Agent coordinator + guardrails
│       ├── api/           # FastAPI routes
│       ├── config/        # Pydantic settings
│       ├── llm/           # LLM planner (real API + mock fallback)
│       ├── models/        # Pydantic schemas
│       ├── tools/         # Tool coordinator (mock DEX quotes)
│       └── utils/         # Logger
├── policy_engine/         # L2 policy rules + L3 validator (eth_call wrapper)
├── contracts/             # L3 SwapGuard (Foundry: anvil, forge, cast)
├── telegram_bot/          # Telegram front-end
├── harness/               # Test harness + metrics (ASR/FP/TR)
├── testcases/             # Adversarial & benign test suites
├── scripts/               # Integration test runners, start-chain.sh (local/fork)
├── tests/                 # Unit tests (pytest)
├── artifacts/             # Run results & artifacts
├── docs/                  # Spec, threat model, project management
├── .env.example           # Environment variable template
└── requirements-dev.txt   # Dev/test dependencies
```