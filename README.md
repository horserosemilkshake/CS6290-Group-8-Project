# CS6290 Group 8 — Adversarially-Robust DeFi Swap Agent

An AI agent that converts natural-language cryptocurrency swap requests into unsigned transaction plans, hardened with layered guardrails against prompt injection, excessive agency, and economic attacks.

## Architecture

```
User ─► Telegram Bot ─► FastAPI Agent API ─► L1 Guardrails ─► LLM Planner ─► Tool Coordinator ─► L2 Policy Engine ─► TxPlan
```

| Component | Location | Description |
|-----------|----------|-------------|
| **Agent API** | `agent_client/` | FastAPI server; LLM intent parsing (DeepSeek / OpenAI-compatible) with mock DEX tool coordinator |
| **L1 Guardrails** | `agent_client/src/agents/` | Input sanitisation (injection detection, encoding attacks, length limits) + output validation |
| **L2 Policy Engine** | `policy_engine/` | 7 deterministic rules: token allowlist, router allowlist, slippage, value cap, unlimited approval, tx structure, chain scope |
| **Telegram Bot** | `telegram_bot/` | Natural-language front-end; group-chat privacy (ALLOW details sent via owner DM only) |
| **Test Harness** | `harness/` | Automated red-team runner with ASR / FP / TR metrics |
| **Test Cases** | `testcases/` | 100 adversarial cases (`adv_100_cases.json`) covering injection, social engineering, encoding attacks, logic overrides |

## Defense Configurations

| Config | Flag | Guardrails |
|--------|------|------------|
| Config 0 (bare) | `DEFENSE_CONFIG=bare` | None — baseline |
| Config 1 (L1) | `DEFENSE_CONFIG=l1` | L1 input/output guardrails only |
| Config 2 (L1+L2) | `DEFENSE_CONFIG=l1l2` | L1 + L2 policy engine (default) |

**Latest 100-case adversarial results:**

| Config | ASR ↓ | FP | TR (max) |
|--------|-------|----|----------|
| bare | 69 % | 0 % | 3.89 s |
| l1 | 28 % | 0 % | 3.79 s |
| l1l2 | 17 % | 0 % | 3.88 s |

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
├── policy_engine/         # L2 deterministic policy rules
├── telegram_bot/          # Telegram front-end
├── harness/               # Test harness + metrics (ASR/FP/TR)
├── testcases/             # Adversarial & benign test suites
├── scripts/               # Integration test runners
├── tests/                 # Unit tests (pytest)
├── artifacts/             # Run results & artifacts
├── docs/                  # Spec, threat model, project management
├── .env.example           # Environment variable template
└── requirements-dev.txt   # Dev/test dependencies
```