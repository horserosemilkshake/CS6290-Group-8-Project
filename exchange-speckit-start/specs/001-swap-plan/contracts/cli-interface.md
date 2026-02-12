# API Contract: CLI Interface for Swap Planning Agent

**Version**: 1.0.0  
**Date**: 2026-02-13  
**Protocol**: JSON-based stdin/stdout text interface  
**Error Stream**: stderr (structured JSON logs)

---

## Overview

The agent operates as a stateless CLI tool:
- **Input**: JSON via stdin
- **Output**: JSON via stdout (plan or rejection)
- **Logs**: Structured JSON via stderr (audit trail, threat classification)
- **Exit Code**: 0 (success) or 1 (error/rejection)

---

## Request Format

### Request Type: Quote Validation

**Endpoint**: `submit_quote`  
**Purpose**: Submit a swap quote for validation 

**Input Schema**:
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "properties": {
    "action": {
      "type": "string",
      "enum": ["validate_quote"],
      "description": "Action type"
    },
    "quote_id": {
      "type": "string",
      "pattern": "^[a-f0-9-]{36}$",
      "description": "UUID for this quote"
    },
    "from_token": {
      "type": "string",
      "pattern": "^0x[a-fA-F0-9]{40}$",
      "description": "Ethereum token address (checksummed)"
    },
    "to_token": {
      "type": "string",
      "pattern": "^0x[a-fA-F0-9]{40}$",
      "description": "Ethereum token address (checksummed)"
    },
    "from_amount": {
      "type": "string",
      "pattern": "^[0-9]+(\\.[0-9]+)?$",
      "description": "Amount in from_token (as string to preserve precision)"
    },
    "to_amount": {
      "type": "string",
      "pattern": "^[0-9]+(\\.[0-9]+)?$",
      "description": "Quoted amount in to_token"
    },
    "slippage_tolerance": {
      "type": "number",
      "minimum": 0,
      "maximum": 100,
      "description": "Acceptable slippage as percentage"
    },
    "market_confidence": {
      "type": "number",
      "minimum": 0.0,
      "maximum": 1.0,
      "description": "Confidence level of quote (0.0-1.0)"
    },
    "price_impact": {
      "type": "string",
      "pattern": "^[0-9]+(\\.[0-9]+)?$",
      "description": "Estimated price impact as percentage"
    },
    "quote_expiry": {
      "type": "string",
      "format": "date-time",
      "description": "ISO 8601 datetime when quote expires"
    },
    "created_at": {
      "type": "string",
      "format": "date-time",
      "description": "ISO 8601 datetime when quote was created"
    }
  },
  "required": ["action", "quote_id", "from_token", "to_token", "from_amount", "to_amount", "slippage_tolerance", "market_confidence", "quote_expiry"],
  "additionalProperties": false
}
```

**Example Request**:
```json
{
  "action": "validate_quote",
  "quote_id": "550e8400-e29b-41d4-a716-446655440000",
  "from_token": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
  "to_token": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
  "from_amount": "10.5",
  "to_amount": "21000.00",
  "slippage_tolerance": 0.5,
  "market_confidence": 0.95,
  "price_impact": "0.2",
  "quote_expiry": "2026-02-13T11:00:00Z",
  "created_at": "2026-02-13T10:30:00Z"
}
```

---

### Request Type: Plan Generation

**Endpoint**: `generate_plan`  
**Purpose**: Generate a transaction plan from a validated quote

**Input Schema** (extends SwapQuote + adds planning parameters):
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "properties": {
    "action": {
      "type": "string",
      "enum": ["generate_plan"],
      "description": "Action type"
    },
    "quote": {
      "type": "object",
      "description": "Validated SwapQuote (same schema as validate_quote)"
      // ... (SwapQuote schema fields)
    },
    "user_address": {
      "type": "string",
      "pattern": "^0x[a-fA-F0-9]{40}$",
      "description": "User's Ethereum address (for custody proof)"
    },
    "preferred_routing": {
      "type": "array",
      "items": {
        "type": "string",
        "enum": ["direct_swap", "liquidity_pool", "dex_aggregator", "bridge_assisted"]
      },
      "description": "Preferred routing strategies in priority order"
    },
    "execution_window_hours": {
      "type": "integer",
      "minimum": 1,
      "maximum": 72,
      "default": 24,
      "description": "How many hours until plan expires"
    }
  },
  "required": ["action", "quote", "user_address"],
  "additionalProperties": false
}
```

**Example Request**:
```json
{
  "action": "generate_plan",
  "quote": {
    "action": "validate_quote",
    "quote_id": "550e8400-e29b-41d4-a716-446655440000",
    "from_token": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
    "to_token": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
    "from_amount": "10.5",
    "to_amount": "21000.00",
    "slippage_tolerance": 0.5,
    "market_confidence": 0.95,
    "quote_expiry": "2026-02-13T11:00:00Z",
    "created_at": "2026-02-13T10:30:00Z"
  },
  "user_address": "0x1234567890123456789012345678901234567890",
  "preferred_routing": ["dex_aggregator", "liquidity_pool"],
  "execution_window_hours": 24
}
```

---

## Response Format

### Success Response: Quote Accepted

**Endpoint**: `validate_quote` (success)  
**HTTP Equivalent**: 200 OK

**Output Schema**:
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "properties": {
    "status": {
      "type": "string",
      "enum": ["accepted"],
      "description": "Quote validation result"
    },
    "quote_id": {
      "type": "string",
      "description": "Echo of input quote_id"
    },
    "gates_passed": {
      "type": "array",
      "items": {"type": "string"},
      "description": "List of passed validation gates"
    },
    "ready_for_planning": {
      "type": "boolean",
      "const": true,
      "description": "Quote is ready for plan generation"
    }
  },
  "required": ["status", "quote_id", "gates_passed"]
}
```

**Example Response**:
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

---

### Success Response: Plan Generated

**Endpoint**: `generate_plan` (success)  
**HTTP Equivalent**: 200 OK

**Output Schema**:
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "properties": {
    "status": {
      "type": "string",
      "enum": ["draft"],
      "description": "Plan status"
    },
    "plan_id": {
      "type": "string",
      "pattern": "^[a-f0-9-]{36}$",
      "description": "UUID for this plan"
    },
    "quote_id": {
      "type": "string",
      "description": "Reference to validat ed quote"
    },
    "routing_strategy": {
      "type": "string",
      "enum": ["direct_swap", "liquidity_pool", "dex_aggregator", "bridge_assisted"],
      "description": "Selected routing strategy"
    },
    "privacy_level": {
      "type": "integer",
      "enum": [1, 2, 3],
      "description": "1=none, 2=minimal, 3=high"
    },
    "intermediate_addresses": {
      "type": "array",
      "items": {"type": "string"},
      "description": "Privacy routing addresses"
    },
    "steps": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "step_id": {"type": "integer"},
          "step_type": {
            "type": "string",
            "enum": ["approve_token", "execute_swap", "verify_receipt", "custody_proof_verify"]
          },
          "target_address": {"type": "string"},
          "function_name": {"type": "string"},
          "parameters": {"type": "object"},
          "gas_budget": {"type": "integer"}
        },
        "required": ["step_id", "step_type", "target_address"]
      },
      "description": "Ordered execution steps (NO SIGNATURES)"
    },
    "custody_proofs": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "proof_id": {"type": "string"},
          "proof_type": {
            "type": "string",
            "enum": ["balance_merkle", "commitment_preimage", "multisig_requirement", "zero_knowledge_proof"]
          },
          "proof_content": {"type": "object"},
          "verification_method": {"type": "string"}
        }
      },
      "description": "Cryptographic custody proofs"
    },
    "custody_boundaries": {
      "type": "string",
      "const": "No signatures are applied; no funds are moved; user retains full control; plan is reversible until user authorization",
      "description": "Custody boundary statement (REQUIRED, IMMUTABLE TEXT)"
    },
    "estimated_gas_cost": {
      "type": "string",
      "pattern": "^[0-9]+(\\.[0-9]+)?$",
      "description": "Estimated gas cost in ETH"
    },
    "estimated_fee_percentage": {
      "type": "string",
      "pattern": "^[0-9]+(\\.[0-9]+)?$",
      "description": "Total fee as % of swap value"
    },
    "execution_window": {
      "type": "string",
      "format": "date-time",
      "description": "ISO 8601 deadline for execution"
    },
    "timing_sequence": {
      "type": "object",
      "description": "Timing constraints per step"
    }
  },
  "required": ["status", "plan_id", "routing_strategy", "steps", "custody_proofs", "custody_boundaries"],
  "additionalProperties": false
}
```

**Example Response**:
```json
{
  "status": "draft",
  "plan_id": "660f9511-f40c-52e5-b827-557766551111",
  "quote_id": "550e8400-e29b-41d4-a716-446655440000",
  "routing_strategy": "dex_aggregator",
  "privacy_level": 3,
  "intermediate_addresses": [
    "0xAAAA...",
    "0xBBBB...",
    "0xCCCC..."
  ],
  "steps": [
    {
      "step_id": 1,
      "step_type": "approve_token",
      "target_address": "0x68b3465833fb72B5A828cCEBF2B67fa51006aD00",
      "function_name": "approve",
      "parameters": {
        "token": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
        "amount": "10.5"
      },
      "gas_budget": 100000
    },
    {
      "step_id": 2,
      "step_type": "execute_swap",
      "target_address": "0x68b3465833fb72B5A828cCEBF2B67fa51006aD00",
      "function_name": "swapExactTokensForTokens",
      "parameters": {
        "amountIn": "10500000000000000000",
        "amountOutMin": "20790000000000",
        "path": ["0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2", "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"],
        "to": "0xAAAA...",
        "deadline": 1707829800
      },
      "gas_budget": 250000
    }
  ],
  "custody_proofs": [
    {
      "proof_id": "770g0622-g51d-63f6-c938-668877662222",
      "proof_type": "balance_merkle",
      "proof_content": {
        "user_address": "0x1234567890123456789012345678901234567890",
        "balance_before": "10.5",
        "balance_root": "0xabcdefabcdefabcdefabcdefabcdefabcdefabcd",
        "merkle_path": ["0xffff...", "0xeeee..."],
        "nonce": "0c7f2a1b"
      },
      "verification_method": "merkle_verify(balance_before, merkle_path, balance_root)"
    }
  ],
  "custody_boundaries": "No signatures are applied; no funds are moved; user retains full control; plan is reversible until user authorization",
  "estimated_gas_cost": "0.0125",
  "estimated_fee_percentage": "0.2",
  "execution_window": "2026-02-14T10:30:00Z"
}
```

---

### Error Response: Quote Rejected

**Endpoint**: `validate_quote` (failure)  
**HTTP Equivalent**: 200 OK (still 200; rejection is a valid business outcome)  
**Exit Code**: 1 (request rejection)

**Output Schema**:
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "properties": {
    "status": {
      "type": "string",
      "enum": ["rejected"],
      "description": "Validation failed"
    },
    "quote_id": {
      "type": "string",
      "description": "UUID of rejected quote"
    },
    "rejection_code": {
      "type": "string",
      "enum": [
        "QUOTE_INVALID_TOKENS",
        "QUOTE_INSUFFICIENT_AMOUNT",
        "QUOTE_EXCESSIVE_SLIPPAGE",
        "QUOTE_LOW_CONFIDENCE",
        "QUOTE_EXPIRED",
        "THREAT_TOKEN_SPOOFING",
        "THREAT_UNUSUAL_PARAMETERS",
        "THREAT_REPLAY_ATTEMPT",
        "THREAT_DECIMAL_EXPLOIT",
        "UNKNOWN_MARKET_STATE"
      ],
      "description": "Specific rejection reason"
    },
    "rejection_message": {
      "type": "string",
      "description": "User-facing rejection explanation"
    },
    "gate_failed": {
      "type": "string",
      "description": "Name of validation gate that failed"
    },
    "threat_level": {
      "type": "string",
      "enum": ["INFO", "WARNING", "CRITICAL"],
      "description": "Severity of threat (if applicable)"
    }
  },
  "required": ["status", "quote_id", "rejection_code"],
  "additionalProperties": false
}
```

**Example Response**:
```json
{
  "status": "rejected",
  "quote_id": "550e8400-e29b-41d4-a716-446655440000",
  "rejection_code": "THREAT_TOKEN_SPOOFING",
  "rejection_message": "Token address mismatch detected. 'from_token' differs by 1 character from authorized token.",
  "gate_failed": "token_whitelist_check",
  "threat_level": "CRITICAL"
}
```

---

## Stderr: Audit Log Format

All security events (validations, threats, plan generation) logged structured JSON via stderr.

**Audit Log Schema**:
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "properties": {
    "timestamp": {
      "type": "string",
      "format": "date-time",
      "description": "ISO 8601 UTC timestamp"
    },
    "event_type": {
      "type": "string",
      "enum": [
        "quote_validated",
        "quote_rejected",
        "plan_generated",
        "plan_validation_failed",
        "threat_detected",
        "custody_proof_verified"
      ]
    },
    "threat_detected": {
      "type": "boolean",
      "description": "Whether this event involves a threat"
    },
    "threat_code": {
      "type": "string",
      "description": "Threat classification (if applicable)"
    },
    "event_layer": {
      "type": "string",
      "enum": ["L1_PRE_FILTER", "L2_VALIDATION", "L3_POST_GATE"],
      "description": "Which layer detected/processed this"
    },
    "gate_name": {
      "type": "string",
      "description": "Validation gate name (if applicable)"
    },
    "gate_result": {
      "type": "boolean",
      "description": "True if gate passed, false if failed"
    },
    "user_context": {
      "type": "string",
      "description": "Encrypted user identifier (if available)"
    }
  },
  "required": ["timestamp", "event_type"],
  "additionalProperties": false
}
```

**Example Stderr Logs**:
```
{"timestamp": "2026-02-13T10:30:45.123Z", "event_type": "quote_validated", "threat_detected": false, "event_layer": "L2_VALIDATION", "gate_name": "token_whitelist_check", "gate_result": true}
{"timestamp": "2026-02-13T10:30:45.156Z", "event_type": "quote_validated", "threat_detected": false, "event_layer": "L2_VALIDATION", "gate_name": "slippage_tolerance_check", "gate_result": true}
{"timestamp": "2026-02-13T10:30:46.000Z", "event_type": "plan_generated", "threat_detected": false, "event_layer": "L3_POST_GATE", "gate_result": true}
```

---

## CLI Usage Examples

### Example 1: Quote Validation

**Command**:
```bash
echo '{"action": "validate_quote", "quote_id": "...", "from_token": "...", ...}' | python src/main.py
```

**Output to stdout**:
```json
{"status": "accepted", "quote_id": "...", "gates_passed": [...]}
```

**Output to stderr**:
```
{"timestamp": "...", "event_type": "quote_validated", "threat_detected": false, ...}
```

**Exit code**: 0

---

### Example 2: Quote Rejection Due to Threat

**Command**:
```bash
echo '{"action": "validate_quote", "quote_id": "...", "from_token": "0x1111111111111111111111111111111111111112", ...}' | python src/main.py
```

**Output to stdout**:
```json
{"status": "rejected", "quote_id": "...", "rejection_code": "THREAT_TOKEN_SPOOFING", "rejection_message": "Token address mismatch detected..."}
```

**Output to stderr**:
```
{"timestamp": "...", "event_type": "threat_detected", "threat_detected": true, "threat_code": "THREAT_TOKEN_SPOOFING", "event_layer": "L1_PRE_FILTER"}
```

**Exit code**: 1

---

### Example 3: Plan Generation

**Command**:
```bash
echo '{"action": "generate_plan", "quote": {...}, "user_address": "...", ...}' | python src/main.py
```

**Output to stdout**:
```json
{"status": "draft", "plan_id": "...", "routing_strategy": "...", "steps": [...], "custody_proofs": [...]}
```

**Output to stderr**:
```
{"timestamp": "...", "event_type": "plan_generated", "threat_detected": false, ...}
```

**Exit code**: 0

---

## Contract Compliance Tests

These contract tests MUST pass before any release:

1. **Schema Validation**: All stdout responses match respective JSON schema
2. **Threat Codes**: All rejection_codes are defined in threat_rules.yaml
3. **Custody Boundary**: Generated plans contain exact custody_boundaries text
4. **No Plaintext in Logs**: stderr logs contain zero token amounts or addresses in plaintext
5. **Exit Codes**: 0 for success, 1 for rejection/error
6. **Latency**: <100ms for quote validation; <3s for plan generation

---

**API Contract Complete** ✅

