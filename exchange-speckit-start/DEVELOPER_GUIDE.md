# Phase 2 Foundation Developer Guide

## Quick Start for Phase 3+ Development

This guide helps developers understand the Phase 2 foundation and extend it for User Stories.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     CLI (main.py)                           │
│                JSON Input → JSON Output                     │
└──────────────────────┬──────────────────────────────────────┘
                       │
        ┌──────────────┴──────────────┐
        │                             │
   ┌────▼────┐                ┌──────▼──────┐
   │ L1 Filter│                │ L2 Gates    │
   │(Threats) │                │(Validation) │
   └────┬─────┘                └──────┬──────┘
        │                             │
   ┌────▼──────────────────────────────▼────┐
   │         Logging Infrastructure         │
   │  (StructuredLogger + ThreatReporter)   │
   └─────────────────────────────────────────┘
```

### Data Flow

1. **Input**: JSON with quote data
2. **L1 Pre-Filter**: `detect_threats()` checks against threat catalog
   - If threat detected → log + reject
3. **L2 Gates**: `validate_quote()` applies 6 policy gates
   - If validation fails → log + reject code
4. **Output**: JSON with acceptance/rejection + audit log to stderr

---

## Key Concepts for Developers

### 1. Immutable Entities (frozen dataclasses)

All entities use `@dataclass(frozen=True)`:
```python
from dataclasses import dataclass
from typing import Optional
from datetime import datetime
from decimal import Decimal

@dataclass(frozen=True)
class SwapQuote:
    quote_id: str
    from_token: str
    to_token: str
    from_amount: Decimal
    # ... more fields
    
    # Validation happens in __post_init__
    def __post_init__(self):
        if self.from_amount <= 0:
            raise ValueError("Amount must be positive")
```

**Why frozen?**
- Prevents accidental modification
- Enables use as dict keys / in sets
- Guarantees state immutability
- Simplifies parallel processing

### 2. Deterministic Functions

All validation functions must be **pure** (no side effects):

```python
# ✅ GOOD: Pure function, deterministic output
def validate_quote_slippage(quote: SwapQuote, max_slippage: Decimal) -> tuple[bool, Optional[str]]:
    if quote.slippage_tolerance <= max_slippage:
        return (True, None)
    return (False, "QUOTE_EXCESSIVE_SLIPPAGE")

# ❌ BAD: Mutable state, non-deterministic
def validate_quote_slippage_bad(quote: SwapQuote, cache: dict):
    cache[quote.quote_id] = True  # Side effect!
    return (True, None)
```

Test determinism with hashing:
```python
hash1 = SwapQuote(...).get_hash()
hash2 = SwapQuote(...).get_hash()
assert hash1 == hash2  # Must be identical
```

### 3. Validation Gate Pattern

Every gate follows this pattern:

```python
def validate_something(entity, config) -> tuple[bool, Optional[str]]:
    """
    Validate a security property.
    
    Returns:
        (True, None) if validation passes
        (False, REJECTION_CODE) if validation fails
    """
    if not meets_requirement(entity, config):
        return (False, "REJECTION_CODE")
    return (True, None)
```

Example gates in `src/validation/quote_validator.py`:
1. `validate_quote_slippage` - tolerance ≤ 10%
2. `validate_quote_confidence` - confidence ≥ 0.8
3. `validate_quote_expiry` - not expired
4. `validate_quote_required_fields` - all required present
5. `validate_quote_tokens_distinct` - from ≠ to
6. `validate_quote_token_whitelist` - both on whitelist

### 4. Threat Detection Pattern

All threat detectors follow this pattern:

```python
def detect_threat_type(quote: SwapQuote, configs: dict) -> list[AdversarialThreat]:
    """
    Detect specific threat pattern.
    
    Returns:
        List of AdversarialThreat objects (empty if no threats)
    """
    threats = []
    if shows_threat_pattern(quote, configs):
        threats.append(AdversarialThreat(
            threat_id=str(uuid.uuid4()),
            threat_type="THREAT_NAME",
            threat_code="THREAT_CODE",
            detected_field="field_name",
            actual_value=quote.field,
            policy_threshold=config_value,
            severity="CRITICAL" or "WARNING" or "INFO",
            detection_layer="L1_PRE_FILTER" or "L3_POST_GATE",
        ))
    return threats
```

Current threats (in `src/validation/threat_filters.py`):
1. `detect_token_spoofing` - L1 pre-filter
2. `detect_decimal_exploit` - L1 pre-filter
3. `detect_unusual_parameters` - L1 pre-filter
4. `detect_replay_attempt` - L1 pre-filter

### 5. Logging Pattern

All logging to stderr (JSONL format):

```python
import json
import sys
from datetime import datetime

# Log event
event = {
    "timestamp": datetime.utcnow().isoformat(),
    "event_type": "quote_validated",
    "quote_id": quote.quote_id,
    "status": "accepted",
    "gates_passed": 6,
    "gates_failed": 0,
    "threat_detected": False,
}
print(json.dumps(event), file=sys.stderr)
```

Available in `src/logging/audit_logger.py`:
- `log_quote_validation(quote_id, status, gates_passed, gates_failed, threat_detected)`
- `log_threat_detection(threat_id, threat_code, severity, detection_layer)`
- `log_plan_generation(plan_id, routing_strategy, privacy_level, plan_hash)`

---

## Development Workflow for Phase 3+

### Step 1: Write Contract Tests First

Create test in `tests/contract/test_user_story_X.py`:

```python
import pytest
from src.models import SwapQuote
from src.validation import validate_quote

@pytest.mark.contract
class TestUserStory1:
    def test_valid_quote_acceptance(self, sample_swap_quote):
        """Contract: Valid quotes must pass all gates."""
        is_valid, code = validate_quote(
            sample_swap_quote, 
            policy_config={...}
        )
        assert is_valid == True
        assert code is None
    
    def test_invalid_quote_rejection(self, invalid_quote_excessive_slippage):
        """Contract: Invalid quotes must be rejected with code."""
        is_valid, code = validate_quote(
            invalid_quote_excessive_slippage,
            policy_config={...}
        )
        assert is_valid == False
        assert code == "QUOTE_EXCESSIVE_SLIPPAGE"
```

Run tests: `pytest tests/contract/test_user_story_X.py::TestUserStory1 -v`

### Step 2: Implement Functions to Pass Tests

Implement in `src/` modules:

```python
def validate_quote(quote: SwapQuote, policy_config: dict) -> tuple[bool, Optional[str]]:
    """Apply all validation gates."""
    gates = [
        validate_quote_slippage,
        validate_quote_confidence,
        validate_quote_expiry,
        validate_quote_required_fields,
        validate_quote_tokens_distinct,
        validate_quote_token_whitelist,
    ]
    
    for gate in gates:
        is_valid, code = gate(quote, policy_config)
        if not is_valid:
            return (False, code)
    
    return (True, None)
```

### Step 3: Add Integration Tests

Create in `tests/integration/`:

```python
@pytest.mark.integration
def test_quote_validation_workflow_end_to_end():
    """Integration: CLI validates quote end-to-end."""
    input_json = json.dumps({
        "action": "validate_quote",
        "quote": {...}
    })
    
    output = run_cli(input_json)
    result = json.loads(output)
    
    assert result["status"] in ["accepted", "rejected"]
    assert "quote_id" in result
```

### Step 4: Performance Tests

Create in `tests/performance/`:

```python
@pytest.mark.performance
def test_quote_validation_latency(benchmark, sample_swap_quote):
    """Performance Contract: Quote validation <100ms."""
    def validate():
        validate_quote(sample_swap_quote, policy_config)
    
    latency_ms = benchmark.timeit(validate, iterations=1) * 1000
    assert latency_ms < 100, f"Validation took {latency_ms}ms"
```

Run: `pytest tests/performance/ -v`

---

## Common Extension Points

### Adding a New Validation Gate

1. Create function in `src/validation/quote_validator.py`:
```python
def validate_new_property(quote: SwapQuote, config: dict) -> tuple[bool, Optional[str]]:
    if not meets_requirement(quote, config.get("new_property_threshold")):
        return (False, "NEW_REJECTION_CODE")
    return (True, None)
```

2. Add to gate chain in `validate_quote()`:
```python
gates = [
    ...,
    validate_new_property,  # Add here
]
```

3. Add to conftest.py if needed:
```python
@pytest.fixture
def invalid_quote_new_issue():
    return SwapQuote(..., new_property=invalid_value)
```

4. Add test to `tests/contract/`:
```python
def test_new_property_rejected(self, invalid_quote_new_issue):
    is_valid, code = validate_quote(invalid_quote_new_issue, config)
    assert code == "NEW_REJECTION_CODE"
```

### Adding a New Threat Type

1. Add to `src/validation/threat_catalog.py`:
```python
class ThreatCatalog:
    THREAT_NEW_ATTACK = {
        "name": "New Attack Type",
        "description": "...",
        "detection_method": "method_name",
        "severity": "CRITICAL",
        "test_patterns": [
            {"legitimate": {...}, "attack": {...}},
        ]
    }
```

2. Create detector in `src/validation/threat_filters.py`:
```python
def detect_new_attack(quote: SwapQuote, configs: dict) -> list[AdversarialThreat]:
    threats = []
    if shows_pattern(quote, configs):
        threats.append(AdversarialThreat(
            threat_type="THREAT_NEW_ATTACK",
            threat_code="NEW_ATTACK_CODE",
            ...
        ))
    return threats
```

3. Register in `detect_threats()`:
```python
def detect_threats(quote: SwapQuote, approved_tokens: dict) -> list[AdversarialThreat]:
    all_threats = []
    all_threats.extend(detect_token_spoofing(quote))
    all_threats.extend(detect_decimal_exploit(quote))
    all_threats.extend(detect_unusual_parameters(quote))
    all_threats.extend(detect_replay_attempt(quote))
    all_threats.extend(detect_new_attack(quote))  # Add here
    return all_threats
```

4. Add contract test:
```python
def test_new_attack_detection(self):
    quote = SwapQuote(..., triggered_by_new_attack=True)
    threats = detect_threats(quote)
    assert len(threats) > 0
    assert threats[0].threat_type == "THREAT_NEW_ATTACK"
```

---

## Testing Utilities

### Using Fixtures from conftest.py

```python
# Valid quotes
@pytest.fixture
def sample_swap_quote():
    """Standard valid WETH→USDC swap."""
    return SwapQuote(
        quote_id=str(uuid.uuid4()),
        from_token="0xfFf9976782d46CC05630D92EE39253E4423ACFB9",  # WETH Sepolia
        to_token="0xd5c6C8169A95bA8Af4D1ee8B47EaF3e2Ce68A4b2",  # USDC Sepolia
        from_amount=Decimal("1.0"),
        to_amount=Decimal("2700.0"),
        slippage_tolerance=Decimal("0.5"),
        market_confidence=0.95,
        price_impact=Decimal("0.3"),
        execution_fees=Decimal("5.0"),
        quote_expiry="2026-02-14T00:00:00Z",
        created_at=datetime.utcnow().isoformat(),
        source="mock_oracle",
    )

# Invalid quotes
@pytest.fixture
def invalid_quote_excessive_slippage():
    """Quote with 50% slippage (exceeds 10% limit)."""
    return SwapQuote(..., slippage_tolerance=Decimal("50.0"))
```

Usage in tests:
```python
def test_something(self, sample_swap_quote, invalid_quote_excessive_slippage):
    # Use fixtures in your test
    pass
```

### Mocking External Services

```python
# Mock oracle
@pytest.fixture
def mock_market_oracle():
    oracle = MarketOracle(use_mock=True)
    return oracle

# Mock RPC
@pytest.fixture
def mock_eth_rpc():
    rpc = EthereumRPC(use_mock=True)
    return rpc

# Usage
def test_with_mocks(self, mock_market_oracle, mock_eth_rpc):
    price = mock_market_oracle.get_price("WETH/USDC")
    assert price == Decimal("2700")
```

---

## Debugging Tips

### 1. Enable Debug Logging

```python
import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

logger.debug(f"Quote validation starting for {quote.quote_id}")
```

### 2. Inspect Frozen Objects

Frozen dataclasses cannot be modified after creation:
```python
quote = SwapQuote(...)
quote.from_amount = Decimal("5.0")  # ❌ Raises FrozenInstanceError
```

To modify, create new instance:
```python
new_quote = SwapQuote(
    **{**quote.__dict__, "from_amount": Decimal("5.0")}
)
```

### 3. Test Determinism

```python
# Should produce identical hashes for identical inputs
quote1 = SwapQuote(...)
quote2 = SwapQuote(...)

assert quote1.get_hash() == quote2.get_hash()
```

### 4. Check Audit Logs

Audit logs go to stderr:
```bash
python -m src.main 2> audit.log <<< '{"action": "validate_quote", ...}'
cat audit.log
```

---

## Checklist for Phase 3+ Tasks

### Before Starting a New Phase:

- [ ] Read [plans.md](specs/001-swap-plan/plan.md) for architecture
- [ ] Review [data-model.md](specs/001-swap-plan/data-model.md) for entities
- [ ] Check [tasks.md](specs/001-swap-plan/tasks.md) for task breakdown
- [ ] Review Phase 2 foundational code in `src/`
- [ ] Understand test fixtures in `tests/conftest.py`

### Before Implementing a Feature:

- [ ] Create contract tests FIRST (test-driven development)
- [ ] Verify tests FAIL before implementation
- [ ] Implement code to PASS tests
- [ ] Add integration tests if needed
- [ ] Run full test suite: `pytest tests/ -v`
- [ ] Verify no regressions in Phase 2 tests
- [ ] Commit code: `git add -A && git commit -m "Phase X: description"`

### Before Phase Completion:

- [ ] All contract tests pass
- [ ] All integration tests pass
- [ ] Performance benchmarks met (<100ms for validation)
- [ ] Determinism verified (identical inputs → identical outputs)
- [ ] Audit logging verified (no plaintext content)
- [ ] No breaking changes to Phase 2 foundation
- [ ] All code committed to feature branch

---

## Useful Commands

```bash
# Run all tests
pytest tests/ -v

# Run specific test class
pytest tests/contract/test_models.py::TestQuoteValidationContracts -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html

# Run performance tests
pytest tests/performance/ -v

# Run integration tests
pytest tests/integration/ -v

# Run determinism verification
pytest tests/ -m determinism -v

# Check code style
black --check src/
flake8 src/
isort --check-only src/

# Run pre-commit hooks
pre-commit run --all-files

# Run CLI test
python -m src.main <<< '{"action": "validate_quote", "quote": {...}}'

# Debug with logging
LOGLEVEL=DEBUG pytest tests/contract/test_models.py -v -s
```

---

## References

- **Specification**: [spec.md](specs/001-swap-plan/spec.md)
- **Architecture**: [plan.md](specs/001-swap-plan/plan.md)
- **Data Model**: [data-model.md](specs/001-swap-plan/data-model.md)
- **Tasks**: [tasks.md](specs/001-swap-plan/tasks.md)
- **Code**: [src/](src/)
- **Tests**: [tests/](tests/)

---

*For questions, refer to Phase 2 implementation in IMPLEMENTATION_STATUS.md*
