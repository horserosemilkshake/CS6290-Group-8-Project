# Implementation Plan: Secure Cryptocurrency Swap Planning Agent

**Branch**: `001-swap-plan` | **Date**: 2026-02-13 | **Spec**: [specs/001-swap-plan/spec.md](spec.md)  
**Input**: Feature specification from `/specs/001-swap-plan/spec.md`

## Summary

Build a deterministic LLM agent that generates unsigned cryptocurrency swap transaction plans with layered security guardrails. The system enforces non-overridable L2 policy checks (validation gates for slippage ≤10%, router allowlisting, transaction caps), routes all interactions through stateless CLI I/O with structured JSON logs, implements L1 pre/post-LLM adversarial filtering, manages optional L3 on-chain execution permissions (out of scope for this phase), and maintains human-in-the-loop approval boundaries at signing. No private keys are provided to the agent; plans contain only unsigned routing decisions and custody proofs. Performance targets: agent response <3s; market data + DEX quote lookup <2s. Ethereum is the primary supported chain; additional chain support TBD in Phase 2.

## Technical Context

**Language/Version**: Python 3.11+ with type hints and async I/O support  
**Primary Dependencies**: 
- LLM Framework: Claude SDK (via Anthropic API) for deterministic agent logic
- Ethereum: web3.py 6.0+ for Ethereum RPC interaction (quote lookups, balance verification)
- Validation: pydantic 2.0+ for structured data validation and deterministic schema enforcement
- Cryptography: eth-keys for custody proof generation; hashlib for deterministic hashing
- Logging: python-json-logger for structured JSON audit trails
- Async: aiohttp or httpx for concurrent market/DEX lookups

**Storage**: File-based configuration (JSON/YAML) + in-memory caching; no database required for Phase 1  
**Testing**: pytest 7.0+ with fixtures; hypothesis for property-based testing on validation gates  
**Target Platform**: Linux servers (x86-64) or Docker containers; cloud-ready (AWS Lambda, GCP Cloud Run)  
**Project Type**: Single project with CLI interface (no separate frontend/backend)  
**Performance Goals**: 
- Agent response time: <3s (includes quote lookup, validation, planning)
- Market data API call: <2s (cached when possible; refresh window 10 minutes for quotes)
- Validation gate execution: <100ms per gate (from spec FR-009)
- Determinism verification: identical input → byte-identical output in <500ms

**Constraints**: 
- Deterministic execution: all validation gates MUST produce identical results for identical inputs
- No private keys: agent NEVER handles, stores, or requests private keys
- No signing: transaction plans contain no signatures; signing delegated to downstream execution layer
- No broadcasting: agent MUST NOT directly send transactions to blockchain
- No randomness in core logic: only use cryptographically-secure RNG for nonce generation (documented)
- CLI-only interaction: JSON in/out via stdin/stdout; structured event logs to stderr
- Ethereum mainnet priority: testnet support optional; other chains in Phase 2

**Scale/Scope**: 
- Single agent instance processing swap requests from trusted client
- Support for 10M+ Ethereum token pairs (via DEX routing aggregator)
- Plan storage: file system (plans are ephemeral; user-managed persistence)
- Audit logs: rotating JSON files; operator must configure retention policy
- Availability: <99.5% SLA (human-in-the-loop approval gate acceptable delay source)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Principle I: Privacy Preservation ✅ **PASS**
- **Gate**: Transaction intent cryptographically masked; no plaintext content in logs
- **Implementation**: Plans use cryptographic commitments (hash digests); logs record only structured metadata (threat classifications, gate results, not quote details)
- **Requirement**: FR-002, FR-006 from spec; all operational logs use JSON with no plaintext token addresses or amounts
- **Verification**: Code review + automated log audit in CI/CD pipeline

### Principle II: Deterministic Security Enforcement ✅ **PASS**
- **Gate**: Validation gates produce identical results for identical inputs; no override capability
- **Implementation**: All L2 policy checks (slippage gates, router allowlist, decimal validation) are deterministic functions with zero randomness in decision logic
- **Requirement**: FR-001, FR-005, FR-008 from spec; <100ms validation latency ensures timing consistency
- **Verification**: Determinism property tests using hypothesis; byte-hash comparison of generated plans

### Principle III: Adversarial Robustness ✅ **PASS**
- **Gate**: L1 pre/post-LLM filters detect and reject threat patterns with structured classification
- **Implementation**: Threat catalog (token spoofing, decimal exploits, replay attacks) enforced pre-agent and post-agent; no heuristic overrides
- **Requirement**: FR-004 from spec; threat classification codes enable structured audit trails
- **Verification**: Security researcher-provided threat catalogs; >90% detection accuracy required (SC-007)

### Principle IV: Custody-Safe Transaction Planning ✅ **PASS**
- **Gate**: Plans contain no signatures; funds never move during planning; custody proofs cryptographically verifiable
- **Implementation**: TransactionPlan entity includes CustodyProof with verification method; no private keys loaded into agent memory
- **Requirement**: FR-003, FR-007 from spec; explicit "no signatures, no funds moved" statement in every plan
- **Verification**: Static analysis: grep -r "sign" src/ to ensure no signing operations in planning layer

### Principle V: Strict Development and Governance Standards ✅ **PASS**
- **Gate**: Security events logged with audit trail; code review required for validation gates; test coverage >95% for security code
- **Implementation**: All L2 policy checks, threat filter rules, and custody proof generation require security expert code review; pytest coverage thresholds automated in CI
- **Requirement**: FR-006 from spec; structured JSON logging with timestamp, threat code, rejection reason
- **Verification**: GitHub Actions CI gate: pytest coverage report >95% for validation/threat modules; mandatory security-team review on PRs touching validation.py or threat_filters.py

### Summary
**Constitution Status**: ✅ **ALL GATES PASS**

No constitutional violations identified. This implementation maintains:
- ✅ Privacy boundaries: transaction intent masked, no PII in logs
- ✅ Determinism requirement: all gates produce identical outputs
- ✅ Adversarial posture: layered pre/post-filter threat detection
- ✅ Custody safety: no signatures, no fund movement, cryptographic proofs
- ✅ Governance rigor: structured logging, mandatory reviews, automated test gates

## Project Structure

### Documentation (this feature)

```text
specs/001-swap-plan/
├── plan.md                      # This file (implementation plan)
├── spec.md                      # Feature specification
├── research.md                  # Phase 0: Research findings (PHASE 0 OUTPUT)
├── data-model.md                # Phase 1: Entity definitions & data flows (PHASE 1 OUTPUT)
├── quickstart.md                # Phase 1: Quick start guide for users (PHASE 1 OUTPUT)
├── contracts/                   # Phase 1: API/agent interface specs (PHASE 1 OUTPUT)
│   ├── cli-interface.md         # CLI input/output specification
│   ├── swap-request-schema.json # Request JSON schema
│   └── plan-response-schema.json # Plan response JSON schema
├── checklists/
│   └── requirements.md          # Spec quality validation checklist
└── tasks.md                     # Phase 2: Implementation tasks (PHASE 2 OUTPUT)
```

### Source Code (repository root)

```text
src/
├── __init__.py
├── main.py                      # CLI entry point; parses stdin JSON, calls agent
├── models/
│   ├── __init__.py
│   ├── swap_quote.py            # SwapQuote entity
│   ├── validation_gate.py       # ValidationGate entity & policy definitions
│   ├── transaction_plan.py      # TransactionPlan entity
│   ├── adversarial_threat.py    # AdversarialThreat entity & threat catalog
│   └── custody_proof.py         # CustodyProof entity & verification methods
├── agent/
│   ├── __init__.py
│   ├── swap_planning_agent.py   # Main agent logic (uses Claude SDK + deterministic gates)
│   ├── l1_filter.py             # Pre-LLM adversarial filtering
│   └── l3_filter.py             # Post-LLM safety gate (optional; delegates to on-chain)
├── validation/
│   ├── __init__.py
│   ├── quote_validator.py       # L2 policy: quote validation gates
│   ├── threat_filters.py        # L2 policy: threat pattern detection & rejection
│   ├── threat_catalog.py        # Threat pattern definitions (token spoofing, etc.)
│   └── custody_validators.py    # Custody proof generation & verification
├── routing/
│   ├── __init__.py
│   ├── router_allowlist.py      # L2 policy: router whitelist enforcement
│   ├── privacy_strategies.py    # Privacy routing mechanism selection
│   └── dex_aggregator.py        # DEX quote aggregation (Uniswap, SushiSwap, etc.)
├── market/
│   ├── __init__.py
│   ├── oracle.py                # Market data provider (external oracle interface)
│   ├── eth_rpc.py               # Ethereum RPC client (balance, gas lookup)
│   └── quote_cache.py           # Caching layer for DEX quotes (10m window)
├── logging/
│   ├── __init__.py
│   ├── audit_logger.py          # Structured JSON audit trail logger
│   └── threat_reporter.py       # Threat classification + audit formatting
└── config/
    ├── __init__.py
    ├── policy.yaml              # L2 policy configuration (slippage caps, router allowlist, gas caps)
    ├── threat_rules.yaml        # Threat pattern catalog
    └── routes.yaml              # Supported routing strategies

tests/
├── __init__.py
├── conftest.py                  # pytest fixtures for mocking oracle, RPC, LLM
├── unit/
│   ├── test_quote_validator.py  # Unit tests for FR-001 (validation gates)
│   ├── test_threat_filters.py   # Unit tests for FR-004 (threat detection)
│   ├── test_custody_proof.py    # Unit tests for FR-003 (custody proofs)
│   ├── test_determinism.py      # Determinism verification tests for FR-005
│   ├── test_logging.py          # Verify FR-006 (structured logging, no plaintext content)
│   └── test_routing.py          # Test privacy routing strategy selection
├── contract/
│   ├── test_cli_interface.py    # Contract tests: CLI I/O schema compliance
│   ├── test_plan_format.py      # Contract tests: generated plans match schema
│   └── test_threat_classification.py # Contract tests: threat codes & messages
├── integration/
│   ├── test_user_story_1.py     # End-to-end: quote validation flow (US1)
│   ├── test_user_story_2.py     # End-to-end: privacy plan generation (US2)
│   ├── test_user_story_3.py     # End-to-end: adversarial rejection (US3)
│   ├── test_edge_cases.py       # Edge case handling per spec
│   └── test_ethereum_mainnet.py # Integration with testnet (Sepolia or Goerli)
└── performance/
    ├── test_validation_latency.py   # Verify <100ms gate execution (FR-009)
    ├── test_agent_response_time.py  # Verify <3s end-to-end response
    └── test_quote_lookup_time.py    # Verify <2s market+DEX quote lookup

pyproject.toml                  # Python package dependencies, pytest config, coverage thresholds
README.md                       # Setup, development, deployment instructions
.github/workflows/
├── test.yml                    # Run tests + coverage gate (>95% security modules)
├── lint.yml                    # Pylint + type checking (mypy)
└── security-review.yml         # Require manual approval for validation.py, threat_filters.py changes

docker/
├── Dockerfile                  # Multi-stage: build + runtime image
└── docker-compose.yml          # Local development environment
```

**Structure Decision**: 
Single project structure with CLI interface (no web/mobile frontend). Agent runs as stateless process: reads JSON from stdin, writes plan JSON to stdout, logs structured events to stderr. All L2 policy validation happens deterministically before/after LLM call. This aligns with Principles II (deterministic) and V (structured governance).

## Complexity Tracking

> **No constitutional violations identified** — all implementation choices align with Secure Exchange Constitution principles.

No table entries required. This feature maintains clean separation of concerns:
- L1 pre/post-LLM filtering enforces adversarial robustness without requiring multiple services
- Deterministic L2 policy checks (validation gates) replace heuristic decision-making
- Custody-safe design (no signing, no keys) is simpler than alternatives requiring key management
- CLI-only interface eliminates web/API complexity while maintaining structured I/O compliance
