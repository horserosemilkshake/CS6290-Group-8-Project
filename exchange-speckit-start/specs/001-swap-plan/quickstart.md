# Quickstart: Secure Cryptocurrency Swap Planning Agent

**Version**: 1.0.0  
**Date**: 2026-02-13  
**Target**: Python 3.11+ on Linux/macOS or Docker

---

## What is This Agent?

The Secure Cryptocurrency Swap Planning Agent generates **unsigned transaction plans** for cryptocurrency swaps with deterministic security guardrails. 

**Key Features**:
- ✅ Deterministic quote validation (no override capability)
- ✅ Privacy-preserving plan routing (through intermediary addresses or ZKP)
- ✅ Layered adversarial filtering (L1 pre-filter, L2 deterministic gates, L3 post-filter)
- ✅ Custody-safe execution: NO private keys, NO signatures, NO fund movement during planning
- ✅ Structured audit logs with threat classification
- ✅ Human-in-the-loop approval at signing boundary

**What it Does NOT do**:
- ❌ Sign transactions (responsibility of downstream signing layer)
- ❌ Broadcast to blockchain (user must approve + execute separately)
- ❌ Access private keys (never provided to agent)
- ❌ Make on-chain changes directly (only reads balance, gas prices)

---

## Prerequisites

- **Python 3.11+** (download from python.org if needed)
- **pip** or **conda** (Python package manager)
- **Ethereum RPC endpoint** (Sepolia testnet for Phase 1; Mainnet in Phase 2)
  - Free option: https://1rpc.io/sep (public, rate-limited for Sepolia)
- **API Key** (Anthropic Claude SDK for LLM agent)
  - Sign up at https://console.anthropic.com

---

## Installation

### Option 1: Local Development (Python 3.11+)

**Step 1: Clone the repo and navigate to feature branch**
```bash
cd /path/to/exchange-speckit-start
git checkout 001-swap-plan
```

**Step 2: Create Python virtual environment**
```bash
python3.11 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

**Step 3: Install dependencies**
```bash
cd src
pip install -r requirements.txt
```

**requirements.txt** (to be created during Phase 2 implementation):
```
anthropic>=0.7.0
web3.py>=6.0.0
pydantic>=2.0.0
python-json-logger>=2.0.0
aiohttp>=3.8.0
eth-keys>=0.4.0
pytest>=7.0.0
hypothesis>=6.70.0
```

**Step 4: Set environment variables**
```bash
export ANTHROPIC_API_KEY="your-api-key-here"
export WEB3_PROVIDER_URI="https://1rpc.io/sep"  # Sepolia testnet
export LOG_LEVEL="INFO"  # or "DEBUG" for verbose logging
```

**Step 5: Verify installation**
```bash
python -c "import anthropic; import web3; print('✓ Dependencies loaded')"
```

### Option 2: Docker

**Using provided Dockerfile**:
```bash
docker build -t swap-agent:1.0.0 -f docker/Dockerfile .
docker run -e ANTHROPIC_API_KEY="your-key" \
           -e WEB3_PROVIDER_URI="https://1rpc.io/sep" \
           -i swap-agent:1.0.0 < request.json
```

---

## First Run: Validate a Quote

### Step 1: Create a test quote JSON

Save this as `test_quote.json`:
```json
{
  "action": "validate_quote",
  "quote_id": "550e8400-e29b-41d4-a716-446655440000",
  "from_token": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
  "to_token": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
  "from_amount": "1.0",
  "to_amount": "2000.0",
  "slippage_tolerance": 0.5,
  "market_confidence": 0.95,
  "price_impact": "0.15",
  "quote_expiry": "2026-02-13T12:00:00Z",
  "created_at": "2026-02-13T10:30:00Z"
}
```

**Explanation**:
- `from_token`: WETH address (0xC02...)
- `to_token`: USDC address (0xA0b...)
- `from_amount`: 1 WETH → ~2000 USDC at market rate
- `slippage_tolerance`: 0.5% (L2 policy cap: ≤10%)
- `market_confidence`: 0.95 (high confidence; L2 policy minimum: >0.8)

### Step 2: Run the agent

```bash
python src/main.py < test_quote.json
```

### Step 3: Interpret the output

**Expected stdout** (success):
```json
{
  "status": "accepted",
  "quote_id": "550e8400-e29b-41d4-a716-446655440000",
  "gates_passed": [
    "token_whitelist_check",
    "slippage_tolerance_check",
    "market_confidence_check",
    "price_sanity_check"
  ],
  "ready_for_planning": true
}
```

**Expected stderr** (audit trail):
```
{"timestamp": "2026-02-13T10:30:45.000Z", "event_type": "quote_validated", "threat_detected": false, "event_layer": "L2_VALIDATION", "gate_result": true}
```

**Exit code**: Should be `0` (success)

---

## Second Run: Generate a Plan

### Step 1: Create a plan request JSON

Save this as `test_plan.json`:
```json
{
  "action": "generate_plan",
  "quote": {
    "action": "validate_quote",
    "quote_id": "550e8400-e29b-41d4-a716-446655440000",
    "from_token": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
    "to_token": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
    "from_amount": "1.0",
    "to_amount": "2000.0",
    "slippage_tolerance": 0.5,
    "market_confidence": 0.95",
    "quote_expiry": "2026-02-13T12:00:00Z",
    "created_at": "2026-02-13T10:30:00Z"
  },
  "user_address": "0x1234567890123456789012345678901234567890",
  "preferred_routing": ["dex_aggregator", "liquidity_pool"],
  "execution_window_hours": 24
}
```

### Step 2: Run the agent

```bash
python src/main.py < test_plan.json
```

### Step 3: Interpret the output

**Expected stdout** (plan generated):
```json
{
  "status": "draft",
  "plan_id": "660f9511-f40c-52e5-b827-557766551111",
  "quote_id": "550e8400-e29b-41d4-a716-446655440000",
  "routing_strategy": "dex_aggregator",
  "privacy_level": 3,
  "intermediate_addresses": ["0xAAAA...", "0xBBBB...", "0xCCCC..."],
  "steps": [
    {
      "step_id": 1,
      "step_type": "approve_token",
      "target_address": "0x68b3465833fb72B5A828cCEBF2B67fa51006aD00",
      "function_name": "approve",
      ...
    },
    {
      "step_id": 2,
      "step_type": "execute_swap",
      ...
    }
  ],
  "custody_proofs": [...],
  "custody_boundaries": "No signatures are applied; no funds are moved; user retains full control; plan is reversible until user authorization",
  "estimated_gas_cost": "0.0125",
  "estimated_fee_percentage": "0.2",
  "execution_window": "2026-02-14T10:30:00Z"
}
```

**Key observations**:
- ✅ `status`: "draft" (ready for user approval, not yet executed)
- ✅ `steps`: Contains NO private keys, NO signatures
- ✅ `custody_boundaries`: Required statement present
- ✅ `custody_proofs`: Cryptographic proof of user control

---

## Testing Threat Rejection

### Test Case 1: Token Spoofing

Create `test_spoofing.json` (token address differs by 1 char):
```json
{
  "action": "validate_quote",
  "quote_id": "...",
  "from_token": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc3",
  "to_token": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
  "from_amount": "1.0",
  "to_amount": "2000.0",
  "slippage_tolerance": 0.5,
  "market_confidence": 0.95,
  "quote_expiry": "2026-02-13T12:00:00Z",
  "created_at": "2026-02-13T10:30:00Z"
}
```

**Expected output**:
```json
{
  "status": "rejected",
  "quote_id": "...",
  "rejection_code": "THREAT_TOKEN_SPOOFING",
  "rejection_message": "Token address mismatch detected. 'from_token' differs by 1 character from authorized token.",
  "threat_level": "CRITICAL"
}
```

**Exit code**: 1 (rejection)

### Test Case 2: Excessive Slippage

Create `test_slippage.json` (slippage 50% > 10% cap):
```json
{
  ...
  "slippage_tolerance": 50
  ...
}
```

**Expected output**:
```json
{
  "status": "rejected",
  "rejection_code": "QUOTE_EXCESSIVE_SLIPPAGE",
  "rejection_message": "Slippage tolerance exceeds maximum allowed threshold (50% > 10%)",
  "gate_failed": "slippage_tolerance_check"
}
```

---

## Logs and Audit Trail

### Viewing Audit Logs

All security events logged to stderr in structured JSON format:

```bash
python src/main.py < test_quote.json 2> audit.log
```

**Examining the audit log**:
```bash
cat audit.log | python -m json.tool

# Output:
[
  {
    "timestamp": "2026-02-13T10:30:45.123Z",
    "event_type": "quote_validated",
    "threat_detected": false,
    "event_layer": "L2_VALIDATION",
    "gate_name": "token_whitelist_check",
    "gate_result": true
  },
  ...
]
```

### Log Filtering

**Find all rejections**:
```bash
cat audit.log | grep '"threat_detected": true'
```

**Find specific threat type**:
```bash
cat audit.log | grep 'THREAT_TOKEN_SPOOFING'
```

---

## Configuration

### Policy Configuration (config/policy.yaml)

Controls L2 validation gates:
```yaml
slippage_tolerance:
  max_percentage: 10.0  # L2 policy cap

market_confidence:
  min_threshold: 0.8    # Minimum market confidence

price_sanity:
  max_impact: 15.0      # Reject if price impact > this %

router_allowlist:
  addresses:
    - "0x68b3465833fb72B5A828cCEBF2B67fa51006aD00"  # Uniswap V3 Router
    - "0x1111111254fb6c44bac0bed2854e76f90643097d"  # 1Inch Router

supported_tokens:
  - address: "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"
    name: "WETH"
    decimals: 18
  - address: "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"
    name: "USDC"
    decimals: 6
```

### Threat Rules Configuration (config/threat_rules.yaml)

Defines adversarial threat patterns:
```yaml
threats:
  THREAT_TOKEN_SPOOFING:
    rule: "edit_distance(from_token, authorized) == 1 OR (first_39_chars_match AND last_char_different)"
    level: CRITICAL

  THREAT_DECIMAL_EXPLOIT:
    rule: "precision(amount) > 18 OR (precision == 0.00000001)"
    level: CRITICAL

  THREAT_UNUSUAL_PARAMETERS:
    rule: "slippage_tolerance > 90 OR price_impact > 50"
    level: WARNING
```

---

## Next Steps: From Plan to Execution

### Step 1: User Reviews Plan

Plan generated with status "DRAFT". User Reviews:
1. Routing strategy (`dex_aggregator`, etc.)
2. Privacy level (1=none, 2=minimal, 3=high)
3. Estimated gas cost and fees
4. Custody boundaries statement

### Step 2: User Approves and Signs

Plan transitions to `PENDING_APPROVAL` status. User:
1. Saves plan to file (e.g., `plan_results.json`)
2. Moves plan to signing layer (external tool/service)
3. Signs transactions with private key (signing layer responsibility, NOT agent)

### Step 3: Execution

Signed transactions are broadcast to blockchain (execution layer responsibility, NOT agent).

---

## Development Setup

### Running Tests

```bash
# All tests
pytest tests/ -v

# Unit tests only
pytest tests/unit/ -v

# Coverage report
pytest tests/ --cov=src --cov-report=html

# Performance tests
pytest tests/performance/ -v --benchmark-only
```

### Local Development with Testnet

**Override Sepolia RPC for local testnet**:
```bash
export WEB3_PROVIDER_URI="http://localhost:8545"
```

**Using Ganache (local Ethereum simulator)**:
```bash
npm install -g ganache-cli
ganache-cli --fork https://1rpc.io/sep  # Fork from Sepolia
```

### Running Agent in Debug Mode

```bash
export LOG_LEVEL="DEBUG"
python src/main.py < test_quote.json 2>&1 | grep "DEBUG"
```

---

## Troubleshooting

### Issue: "Invalid API Key"

**Solution**: Verify ANTHROPIC_API_KEY environment variable:
```bash
echo $ANTHROPIC_API_KEY
```

Should output your API key (not empty). If empty, set it:
```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```

### Issue: "Connection refused" error

**Problem**: Cannot reach RPC endpoint  
**Solution**: Verify WEB3_PROVIDER_URI:
```bash
curl https://1rpc.io/sep -H "Content-Type: application/json" -d '{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}'
```

Should return a valid response. If fails, try different RPC:
```bash
export WEB3_PROVIDER_URI="https://sepolia-rpc.publicnode.com"
```

### Issue: Tests failing locally

**Problem**: Determinism test fails (byte-identical output)  
**Reason**: Environment differences (Python version, numeric precision)  
**Solution**: Run tests in Docker:
```bash
docker build -t test-swap . && docker run test-swap pytest tests/
```

---

## Key Differences from Previous Versions

This is **Phase 1 implementation** of the Secure Cryptocurrency Swap Planning Agent. Key guardrails:

- ✅ **No Private Keys Ever**: Agent never touches signing material
- ✅ **Deterministic Validation**: Quote gates cannot be overridden by LLM
- ✅ **Layered Defenses**: L1 pre-filter + L2 deterministic + L3 post-gate
- ✅ **Privacy by Default**: Plans route through intermediary addresses (N>3) or ZKP
- ✅ **Audit Trail**: All security events logged; no plaintext transaction content
- ✅ **Human Approval Required**: Plans are DRAFT; user must approve before signing

---

## Further Documentation

- **Technical Details**: See `plan.md` (Technical Context, Constitution Check)
- **Data Model**: See `data-model.md` (Entity definitions, validation rules)
- **API Contract**: See `contracts/cli-interface.md` (Request/response schemas)
- **Specification**: See `spec.md` (User stories, requirements, success criteria)

---

**Quickstart Complete!** 🚀

Next: Move to Phase 2 (Implementation) once you're familiar with the architecture.

