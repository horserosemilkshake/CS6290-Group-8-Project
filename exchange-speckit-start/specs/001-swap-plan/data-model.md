# Phase 1: Data Model - Swap Planning Agent

**Created**: 2026-02-13  
**Phase**: Design  
**Purpose**: Define entities, relationships, validation rules, and state transitions

---

## Core Entities

### 1. SwapQuote

**Purpose**: Represents the published swap offer from another party (does not require signature)

**Fields**:
```python
class SwapQuote:
    # Primary identifiers
    quote_id: str                    # UUID; unique per quote instance
    timestamp: datetime              # UTC timestamp when quote created
    source: Literal["dex", "mm", "user"]  # Source: DEX aggregator, market maker, or user-entered
    
    # Token pair
    from_token: str                  # Ethereum address (lowercase, checksum verified)
    to_token: str                    # Ethereum address (lowercase, checksum verified)
    
    # Amounts
    from_amount: Decimal             # Amount to swap (18+ decimals precision)
    to_amount: Decimal               # Quoted receive amount
    slippage_tolerance: Decimal      # User's acceptable slippage (0-100%, typical 0.5-2%)
    
    # Quality metrics
    market_confidence: float         # [0.0, 1.0] confidence in this quote
    price_impact: Decimal            # Estimated % price impact on market
    execution_fees: Decimal          # Estimated total fees (gas, swap fee, etc.)
    
    # Timing
    quote_expiry: datetime           # When quote becomes invalid
    created_at: datetime             # When this quote was created
```

**Validation Rules**:
- ✅ `from_token` and `to_token` MUST be distinct Ethereum addresses
- ✅ `from_token` and `to_token` MUST be on approved token whitelist (config/routes.yaml)
- ✅ `from_amount` MUST be >0.0 and ≤user's verified balance
- ✅ `to_amount` MUST be >0.0
- ✅ `slippage_tolerance` MUST be 0 < x ≤ 10% (L2 policy cap from user request)
- ✅ `price_impact` MUST be ≤`slippage_tolerance` (sanity check)
- ✅ `market_confidence` MUST be >0.8 (reject low-confidence quotes per spec edge case)
- ✅ `quote_expiry` MUST be >current_time (reject expired quotes)

**State Machine**:
```
┌──────────────┐
│  CREATED     │  Quote object instantiated
└──────┬───────┘
       │
       ├─→ VALIDATED ──→ Passes all L1 + L2 gates ──→ ACCEPTED
       │
       └─→ REJECTED  ──→ Fails any gate (field validation, threat detected)
```

**Rejection Codes** (for REJECTED state):
- `QUOTE_INVALID_TOKENS`: Token address not on whitelist
- `QUOTE_INSUFFICIENT_AMOUNT`: from_amount > user balance
- `QUOTE_EXCESSIVE_SLIPPAGE`: slippage_tolerance > 10%
- `QUOTE_LOW_CONFIDENCE`: market_confidence < 0.8
- `QUOTE_EXPIRED`: quote_expiry < current_time
- `THREAT_TOKEN_SPOOFING`: Token address mismatch detected
- `THREAT_UNUSUAL_PARAMETERS`: Quote parameters match known attack pattern
- `UNKNOWN_MARKET_STATE`: Cannot validate against market rates

**Constraint**: SwapQuote instances are IMMUTABLE. Once created, cannot be modified; rejected quotes are discarded and new quote must be submitted.

---

### 2. ValidationGate

**Purpose**: Represents a deterministic security policy check that cannot be overridden

**Fields**:
```python
class ValidationGate:
    gate_id: str                     # Unique identifier (e.g., "max_slippage_check")
    gate_name: str                   # Human-readable name
    description: str                 # What this gate enforces
    
    # Policy definition
    threshold: Union[float, Decimal, str]  # Policy threshold value
    operator: Literal["<=", ">=", "<", ">", "==", "!=", "in", "not_in"]  # Comparison
    parameter_path: str              # e.g., "slippage_tolerance" (path into SwapQuote)
    
    # Enforcement
    enforcement_level: Literal["REJECT_NO_OVERRIDE"] = "REJECT_NO_OVERRIDE"  # Non-negotiable
    rejection_code: str              # Code returned if gate fails (e.g., "QUOTE_EXCESSIVE_SLIPPAGE")
    
    # Testing
    test_function: Callable          # Pure function: (quote: SwapQuote) -> bool
    
    # Audit
    created_at: datetime             # When this gate was defined
    modified_at: datetime            # Last modification
    modified_by: str                 # Security team member who last modified
```

**Examples**:
```python
gate_slippage = ValidationGate(
    gate_id="max_slippage_check",
    gate_name="Maximum Slippage Tolerance",
    threshold=10.0,
    operator="<=",
    parameter_path="slippage_tolerance",
    rejection_code="QUOTE_EXCESSIVE_SLIPPAGE",
    test_function=lambda q: q.slippage_tolerance <= 10.0
)

gate_token_whitelist = ValidationGate(
    gate_id="token_whitelist_check",
    gate_name="Token Whitelist Validation",
    threshold=None,
    parameter_path="from_token,to_token",
    rejection_code="QUOTE_INVALID_TOKENS",
    test_function=lambda q: q.from_token in APPROVED_TOKENS and q.to_token in APPROVED_TOKENS
)
```

**Constraint**: ValidationGate definitions stored in YAML configuration (config/policy.yaml). Changes require:
1. Git commit with security team review
2. Ratification by security lead
3. CI deployment (no runtime modification of gates)

**No Dynamic Overrides**: System MUST reject any request to bypass, modify, or skip a ValidationGate at runtime. If bypass attempted, log threat code "THREAT_OVERRIDE_ATTEMPT" and reject entire request.

---

### 3. TransactionPlan

**Purpose**: Represents the unsigned, custody-safe execution plan generated by agent

**Fields**:
```python
class TransactionPlan:
    plan_id: str                     # UUID; unique plan identifier
    
    # Reference
    quote_id: str                    # Reference to validated SwapQuote
    agent_version: str               # Version of agent that generated plan
    generated_at: datetime           # Timestamp of generation
    
    # Routing
    routing_strategy: Literal[        # Deterministic selection from available strategies
        "direct_swap", 
        "liquidity_pool",
        "dex_aggregator", 
        "bridge_assisted"
    ]
    intermediate_addresses: List[str]  # Privacy routing: list of intermediary addresses (N>3 for privacy)
    privacy_level: int                # 1=none, 2=minimal, 3=high (3=privacy routing used)
    
    # Execution sequence
    steps: List[TransactionStep]      # Ordered list of atomic operations
    timing_sequence: Dict[str, str]   # Timing requirements per step (e.g., {"step_1": "immediate", "step_2": "+1h"})
    execution_window: datetime        # Latest time this plan remains valid (default +24h)
    
    # Custody
    custody_proofs: List[CustodyProof]  # Cryptographic proofs of user control
    custody_boundaries: str            # CONSTANT TEXT: "No signatures are applied; no funds are moved; user retains full control; plan is reversible until user authorization"
    
    # Execution info
    estimated_gas_cost: Decimal       # Estimated total gas (ETH)
    estimated_fee_percentage: Decimal # Fee as % of swap value
    
    # Plan status
    status: Literal["DRAFT", "PENDING_APPROVAL", "EXECUTED", "EXPIRED"]  # See state machine below
    approval_required: bool           # MUST be True (human sign-off required)
```

**Nested: TransactionStep**:
```python
class TransactionStep:
    step_id: int                      # Sequential step number (1, 2, 3, ...)
    step_type: Literal[
        "approve_token",              # Approve spending (router allowance)
        "execute_swap",               # Execute swap via DEX
        "verify_receipt",             # Verify swap completed
        "custody_proof_verify",       # Verify custody proof still valid
    ]
    
    # Target
    target_address: str               # Contract or address to interact with (checked against router allowlist)
    function_name: str                # Function to call (e.g., "swapExactTokensForTokens")
    
    # Parameters (NO SIGNATURES)
    parameters: Dict[str, str]        # Function parameters; NO private keys in dict
    gas_budget: int                   # Gas budget for this step
    
    # Contingency
    fallback_strategy: Optional[str]  # If step fails, use fallback (e.g., "use_bridge_instead")
    depends_on: Optional[int]         # Step dependency: step_id this depends on
```

**State Machine**:
```
┌──────────────┐
│  DRAFT       │  Plan generated; ready for user review
└──────┬───────┘
       │
       ├─→ PENDING_APPROVAL ──→ User reviews + approves at signing boundary
       │                              ↓
       │                        (User provides signature via external tool)
       │                              ↓
       ├──────────────────→ EXECUTED ──→ Signed transaction broadcast
       │
       └─→ EXPIRED ──→ Execution window passed; plan invalidated
```

**Validation Rules**:
- ✅ `intermediate_addresses` MUST have length ≥3 OR plan MUST include CustodyProof with ZKP
- ✅ `routing_strategy` MUST be selected deterministically based on input (not random)
- ✅ `target_address` in each TransactionStep MUST be on router allowlist (config/routes.yaml)
- ✅ `parameters` MUST NOT contain private keys, mnemonics, or secret material
- ✅ `custody_boundaries` MUST contain exact text (no modifications)
- ✅ `approval_required` MUST always be `True` (enforced in code)
- ✅ `execution_window` MUST be >current_time; plan cannot execute outside this window

**Immutability Constraint**: TransactionPlan is immutable once generated. If plan needs modification, user must reject and request new plan from agent (forces re-validation).

**Custody Proof Requirement**: Every plan MUST include at least one CustodyProof. Examples:
- Merkle proof of balance (user retains balance hash; proves agent didn't intercept)
- Multi-sig structure (if user uses multisig, plan includes signer requirements)
- Commitment preimage (cryptographic commitment user can later prove)

---

### 4. CustodyProof

**Purpose**: Cryptographic evidence that user maintains control throughout execution

**Fields**:
```python
class CustodyProof:
    proof_id: str                    # UUID
    proof_type: Literal[
        "balance_merkle",            # Merkle proof of user balance
        "commitment_preimage",       # Preimage of commitment hash
        "multisig_requirement",      # Multi-sig authorization structure
        "zero_knowledge_proof"       # ZKP of transaction sequence
    ]
    
    # Proof content
    proof_content: Dict[str, str]    # Proof data (structure depends on type)
    
    # Verification
    verification_method: str         # How to verify: "merkle_verify()", "check_commitment()", etc.
    verification_hash: str           # SHA256 of proof_content for tampering detection
    
    # Timing
    created_at: datetime
    expiry: datetime                 # When proof becomes invalid (typically +24h)
```

**Examples**:

**Type: balance_merkle**
```json
{
  "proof_type": "balance_merkle",
  "proof_content": {
    "user_address": "0x1234...",
    "balance_before": "10.5",
    "balance_root": "0xabcd...",
    "merkle_path": "[0xffff, 0xeeee]",
    "nonce": "0c7f2a1b"
  }
}
```

**Type: commitment_preimage**
```json
{
  "proof_type": "commitment_preimage",
  "proof_content": {
    "commitment_hash": "0x9876...",
    "preimage": "plans[0x1234].json",
    "user_address": "0x1234..."
  }
}
```

**Constraint**: At least one CustodyProof MUST be present in every TransactionPlan. Agent MUST fail plan generation if unable to generate valid custody proof.

---

### 5. AdversarialThreat

**Purpose**: Represents detected threat patterns from L1 pre-filter or L3 post-gate

**Fields**:
```python
class AdversarialThreat:
    threat_id: str                   # UUID
    
    # Threat classification
    threat_type: str                 # Code: "THREAT_TOKEN_SPOOFING", "THREAT_DECIMAL_EXPLOIT", etc.
    threat_level: Literal["INFO", "WARNING", "CRITICAL"]  # Severity
    
    # Detection context
    detected_at: datetime            # When threat detected
    detected_by: Literal[
        "L1_PRE_FILTER",
        "L2_VALIDATION",
        "L3_POST_GATE"
    ]
    request_context: Dict[str, str]  # Relevant part of request (sanitized, no amounts)
    
    # Evidence
    detection_reason: str            # Human-readable explanation
    policy_threshold: str            # Which policy was violated
    actual_value: str                # Actual value detected (sanitized)
    
    # Response
    rejection_code: str              # Code returned to user (e.g., "THREAT_TOKEN_SPOOFING")
    rejection_message: str           # User-facing message (no internal details)
    
    # Audit
    user_context: Optional[str]      # User identifier (if available; encrypted in logs)
    source_ip_hash: str              # Hash of source IP (for cluster-level threat analysis)
```

**Threat Catalog** (config/threat_rules.yaml):
```yaml
threats:
  THREAT_TOKEN_SPOOFING:
    description: "Token address differs by 1 char from authorized token"
    detection_rule: "edit_distance(address, authorized) == 1"
    level: CRITICAL
  
  THREAT_DECIMAL_EXPLOIT:
    description: "Amount precision extreme (triggers rounding error)"
    detection_rule: "precision(amount) > 18 or precision(amount) == 0"
    level: CRITICAL
  
  THREAT_UNUSUAL_PARAMETERS:
    description: "Slippage tolerance designed to guarantee failure"
    detection_rule: "slippage_tolerance > 90"
    level: WARNING
  
  THREAT_REPLAY_ATTEMPT:
    description: "Identical request within 100ms window"
    detection_rule: "quote_hash(current) == quote_hash(previous) and elapsed_time < 100ms"
    level: WARNING
```

**Constraint**: Every rejected request MUST generate exactly one AdversarialThreat record. Logs MUST include threat_type, rejection_code, and timestamp. No plaintext quote details in logs.

---

## Data Flows

### Flow 1: Quote Validation (User Story 1)

```
User Input (JSON)
    ↓
L1 Pre-Filter: Threat detection
    ├─→ Pass: Continue to L2
    └─→ Fail: Log threat, return rejection
    
L2 Validation Gates
    ├─ Token whitelist check
    ├─ Slippage ≤ 10% check  
    ├─ Balance sufficiency check
    ├─ Price confidence > 0.8 check
    ├─ Quote not expired check
    └─ All gates pass? 
        ├─→ Yes: ACCEPTED (pass to planning)
        └─→ No: REJECTED (log threat code)

Output: {"quote_status": "accepted"} or {"quote_status": "rejected", "threat_code": "..."}
```

### Flow 2: Plan Generation (User Story 2)

```
Validated SwapQuote → Agent
    ↓
Agent (Claude with few-shot examples):
  - Input: SwapQuote fields + routing strategies available
  - Output: Unsigned TransactionPlan with custody proofs
    ↓
L3 Post-Gate Validation:
    ├─ Plan structure valid?
    ├─ Custody proof present?
    ├─ No signing operations detected?
    └─ All checks pass?
        ├─→ Yes: DRAFT status (return to user)
        └─→ No: REJECTED (regenerate or error)

Output: {"plan_id": "...", "status": "DRAFT", "steps": [...], "custody_proofs": [...]}
```

### Flow 3: Adversarial Rejection (User Story 3)

```
Any Request (quote or plan)
    ↓
Threat Catalog Check (Parallel):
    ├─ Token spoofing detector
    ├─ Decimal exploit detector
    ├─ Replay detector
    ├─ Unusual parameter detector
    └─ Any threat detected?
        ├─→ Yes: Log AdversarialThreat, reject with code
        └─→ No: Continue normal flow

Logging (Structured JSON):
{
  "timestamp": "2026-02-13T10:30:45Z",
  "threat_detected": true,
  "threat_type": "THREAT_TOKEN_SPOOFING",
  "threat_level": "CRITICAL",
  "detected_by": "L1_PRE_FILTER",
  "rejection_code": "THREAT_TOKEN_SPOOFING",
  "user_context": "<encrypted>"
}
```

---

## Validation Rules Summary

| Entity | Key Constraints |
|--------|-----------------|
| **SwapQuote** | Immutable; slippage ≤10%; market_confidence >0.8; tokens on whitelist |
| **ValidationGate** | REJECT_NO_OVERRIDE; git-managed config; no runtime modification |
| **TransactionPlan** | Immutable; custody_proofs required; no private keys; approval_required=True |
| **CustodyProof** | ≥1 required per plan; supporting ZKP OR ≥3 intermediary addresses |
| **AdversarialThreat** | Logged for every rejection; no plaintext details; structured JSON format |

---

## State Transitions Diagram

```
QUOTE:
  CREATED → {validate} → ACCEPTED/REJECTED

PLAN:
  DRAFT → {user approval} → PENDING_APPROVAL → {signing layer} → EXECUTED
  DRAFT → {time passes} → EXPIRED

THREAT:
  (Not a state entity; record logged for audit trail)
```

---

**Phase 1 Data Model Complete** ✅  
**Ready for API Contract specification and Quickstart.**

