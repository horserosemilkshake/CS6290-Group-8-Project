# Tasks: Secure Cryptocurrency Swap Planning Agent

**Feature**: `001-swap-plan` | **Branch**: `001-swap-plan` | **Status**: Ready for Phase 2 Implementation  
**Input Spec**: [spec.md](spec.md) (3 user stories, 10 FRs, 5 entities)  
**Implementation Plan**: [plan.md](plan.md) | **Data Model**: [data-model.md](data-model.md)  
**API Contract**: [contracts/cli-interface.md](contracts/cli-interface.md)

---

## Format Overview

- **[ ] T[ID]** = Checkbox + Task ID (sequential: T001, T002, ...)
- **[P]** = Parallelizable (different files, no task dependencies)
- **[US#]** = User story label (US1, US2, US3) for traceability
- **File paths** = Exact locations where implementation occurs

### Execution Model

- All tasks within Phase 1 Setup must complete before Phase 2 Foundational begins
- Phase 2 Foundational is BLOCKING: must 100% complete before ANY user story work begins
- User stories (Phase 3+) can be worked in parallel after Foundational is done
- Tests marked [P] can run in parallel within a user story

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization, dependency management, and repository structure

**Duration**: ~4 hours | **Blockers**: None

- [ ] T001 Create project directory structure per plan.md layout: `src/`, `tests/`, `config/`, `docs/` directories
- [ ] T002 [P] Initialize Python 3.11+ project with pyproject.toml or requirements.txt: anthropic, web3.py, pydantic, eth-keys, python-json-logger, aiohttp, pytest, hypothesis
- [ ] T003 [P] Setup Git hooks and pre-commit configuration for code linting (flake8, black formatting)
- [ ] T004 Configure pytest.ini and conftest.py with test discovery patterns for unit/contract/integration/performance tests
- [ ] T005 [P] Create src/__init__.py package structure and module imports
- [ ] T006 Setup .env.example template with ANTHROPIC_API_KEY, WEB3_PROVIDER_URI, LOG_LEVEL placeholders
- [ ] T007 [P] Create config/default_policy.yaml template with slippage max (10%), confidence min (0.8), router whitelist structure
- [ ] T008 [P] Create config/threat_rules.yaml template with threat catalog (THREAT_TOKEN_SPOOFING, THREAT_DECIMAL_EXPLOIT, THREAT_UNUSUAL_PARAMETERS, THREAT_REPLAY_ATTEMPT)
- [ ] T009 Create README.md with project overview, quick start link, and prerequisites

**Checkpoint**: Project structure initialized, all dependencies specified, ready for foundational architecture

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story implementation

**Duration**: ~12 hours | **Blockers**: None (depends only on Phase 1)

**⚠️ CRITICAL**: This phase BLOCKS all user story work. Cannot begin user stories until this phase is 100% complete.

### Configuration & Logging Infrastructure

- [ ] T010 [P] Create src/logging/audit_logger.py with StructuredLogger class: JSON-formatted output, timestamp, event_type, threat_detected, threat_code fields
- [ ] T011 [P] Create src/logging/threat_reporter.py with format_threat_report(threat: AdversarialThreat) → structured JSON dict
- [ ] T012 [P] Implement src/logging/__init__.py with centralized log sink configuration for stdout (results) and stderr (events)
- [ ] T013 Create src/config/__init__.py with load_policy_yaml(path) and load_threat_rules_yaml(path) functions; validate schema

### Data Model Entities (5 Core Models - Immutable Design)

**Note**: These 5 models are independent and can be parallelized:

- [ ] T014 [P] Create src/models/swap_quote.py: SwapQuote dataclass with fields (quote_id, timestamp, from_token, to_token, from_amount, to_amount, slippage_tolerance, market_confidence, price_impact, execution_fees, quote_expiry); use Decimal for precision
- [ ] T015 [P] Create src/models/validation_gate.py: ValidationGate dataclass with fields (gate_id, gate_name, threshold, operator, parameter_path, enforcement_level, rejection_code); add test_function stub
- [ ] T016 [P] Create src/models/transaction_plan.py: TransactionPlan dataclass with fields (plan_id, quote_reference, routing_strategy, intermediate_addresses, custody_proofs, privacy_level, execution_window, steps, boundaries_statement); ensure NO signatures
- [ ] T017 [P] Create src/models/adversarial_threat.py: AdversarialThreat dataclass with fields (threat_id, threat_type, threat_code, detected_field, actual_value, policy_threshold, rejection_reason, detected_at)
- [ ] T018 [P] Create src/models/custody_proof.py: CustodyProof dataclass with fields (proof_type, proof_content, verification_method); support types=[balance_merkle, commitment_preimage, multisig_requirement, zero_knowledge_proof]
- [ ] T019 Create src/models/__init__.py with imports for all 5 entities

### Validation Framework (L2 Policy Layer - Immutable + Non-Bypassable)

- [ ] T020 [P] Create src/validation/quote_validator.py with validate_quote(quote: SwapQuote, policy: dict) → (bool, Optional[rejection_code]); implement Decimal precision checks
- [ ] T021 [P] Create src/validation/threat_filters.py with detect_threats(quote: SwapQuote, threat_rules: dict) → List[AdversarialThreat]; implement pattern matching for 4 threat types
- [ ] T022 [P] Create src/validation/threat_catalog.py with threat pattern definitions: THREAT_TOKEN_SPOOFING, THREAT_DECIMAL_EXPLOIT, THREAT_UNUSUAL_PARAMETERS, THREAT_REPLAY_ATTEMPT; include test patterns
- [ ] T023 Create src/validation/custody_validators.py with generate_custody_proof(plan: TransactionPlan) → CustodyProof; implement merkle tree stub
- [ ] T024 Create src/validation/__init__.py with centralized validation exports

### Market Data & Ethereum Integration (External I/O - Cached)

- [ ] T025 [P] Create src/market/oracle.py with MarketOracle interface for external price data; include mock implementation for testing
- [ ] T026 [P] Create src/market/eth_rpc.py with EthereumRPC class: balance_of(address, token), gas_estimate(), token_allowlist_check(token_address)
- [ ] T027 Create src/market/quote_cache.py with QuoteCache: 10-minute TTL, fallback to live quote if expired; implement with simple dict + timestamp
- [ ] T028 Create src/market/__init__.py with exports

### Storage & Configuration Management

- [ ] T029 Create config/ directory placeholder with default_policy.yaml, threat_rules.yaml, token_whitelist.yaml (static reference data)
- [ ] T030 Create src/config/__init__.py with PolicyManager class: load_policy(), get_gate(gate_id), get_threat_rules()

### CLI Infrastructure (Entry Point)

- [ ] T031 Create src/main.py with CLI entry point: parse JSON from stdin, dispatch to agent, return JSON on stdout (action and result), structured logs to stderr
- [ ] T032 Create src/__init__.py with package-level version and exports

### Tests for Foundational Layer (Contract Tests - Inputs/Outputs)

**Note: Write tests FIRST, ensure they FAIL, then implement**

- [ ] T033 [P] Create tests/contract/test_models.py: verify SwapQuote fields, ValidationGate immutability, TransactionPlan no-signatures constraint, AdversarialThreat structure, CustodyProof types
- [ ] T034 [P] Create tests/contract/test_validation.py: test quote_validator() with valid/invalid quotes; verify rejection_code returned
- [ ] T035 [P] Create tests/contract/test_threat_patterns.py: test detect_threats() against 4 threat types; verify 100% accuracy on test catalog
- [ ] T036 Create tests/contract/test_cli_interface.py: verify JSON in/out, verify "No signatures" text in responses, verify stderr logging

**Checkpoint**: All foundational infrastructure in place. All 5 entities exist. Validation framework immutable. Market integration stubs ready. CLI skeleton complete. Ready to implement user stories in parallel.

---

## Phase 3: User Story 1 - Deterministic Quote Validation (Priority: P1) 🎯 MVP

**Goal**: System MUST validate swap quotes against deterministic security gates with explicit rejection if unsafe. All validation is non-overridable and deterministic. Identical quotes produce identical results.

**Independent Test**: Submit test quotes (favorable, unfavorable, extreme, malformed) and verify explicit rejections with clear reasoning. Confirm no override capability exists.

**Success Criteria** (from spec):
- SC-001: Validate + decide in <100ms, 100% consistency (determinism)
- SC-002: Zero bypasses of validation gates; all overrides rejected
- SC-004: All threat patterns detected with 100% accuracy
- SC-005: Identical requests → byte-identical outputs

### Tests for User Story 1 (Contract & Integration)

**Write tests FIRST - ensure they FAIL before implementation**

- [ ] T037 [P] [US1] Create tests/contract/test_quote_validation_gates.py: test each L2 gate individually (slippage cap, confidence min, token whitelist, field presence); verify determinism across 10 identical runs
- [ ] T038 [P] [US1] Create tests/integration/test_quote_validation_workflow.py: end-to-end test validate_quote() from async stdin; test favorable quote (accepted), unfavorable quote (rejected with code), malformed quote (field error)
- [ ] T039 [P] [US1] Create tests/integration/test_determinism.py: property-based test using hypothesis; identical quote → identical output hash for 100 iterations
- [ ] T040 [US1] Create tests/contract/test_quote_threat_detection.py: test threat detection on quotes with token spoofing, decimal exploits, unusual parameters, replay attempts

### Implementation for User Story 1

- [ ] T041 [P] [US1] Expand src/validation/quote_validator.py: implement slippage gate (slippage_tolerance ≤ 10%), market_confidence gate (>0.8), token_whitelist gate, required_fields gate; all deterministic, no overrides
- [ ] T042 [P] [US1] Expand src/validation/threat_filters.py: implement token spoofing detection (address whitelist check), decimal exploit detection (amount range validation), unusual parameters detection (slippage 100% = attack), replay detection (timestamp + hash cache)
- [ ] T043 [P] [US1] Expand src/validation/threat_catalog.py: add test patterns and rule definitions for all 4 threat types; make patterns editable in YAML
- [ ] T044 [US1] Create src/agent/quote_validator_service.py with orchestrate_quote_validation(quote: SwapQuote) → (Status, Optional[RejectionReason]); chain L1 + L2 + L3 gates
- [ ] T045 [US1] Implement src/market/oracle.py with working market data lookup for WETH/USDC pair; use mock until Phase 2 upstream API integration
- [ ] T046 [US1] Extend src/main.py to handle "validate_quote" action: parse quote from JSON, call orchestrate_quote_validation(), return {"status": "accepted|rejected", "rejection_code": "...", "gates_passed": [...]}
- [ ] T047 [US1] Add structured logging to validation flow: log each gate result, threat detection, final decision to audit_logger; ensure no quote details in plaintext
- [ ] T048 [US1] Create src/validation/determinism_verifier.py with verify_determinism(quote: SwapQuote) → bool; hash plan output and verify identical for repeated inputs

**Checkpoint**: User Story 1 complete. Quote validation is deterministic, non-overridable, <100ms, and rejects threats. Can be tested independently. Ready for User Story 2.

---

## Phase 4: User Story 2 - Privacy-Preserving Swap Plan Generation (Priority: P1)

**Goal**: Agent generates transaction plans that route swaps through privacy-safe mechanisms without exposing transaction intent in logs or requiring signatures. Plans include custody proofs and explicit privacy boundaries. Output is deterministic.

**Independent Test**: Submit validated quotes and verify (1) privacy routing decisions in output, (2) no transaction intent in plaintext logs, (3) custody proofs present, (4) "no signatures; no funds moved" statement included, (5) byte-identical output for identical inputs.

**Success Criteria** (from spec):
- SC-002: Zero plaintext transaction content in logs
- SC-003: 100% of plans include custody boundary statement + custody proof
- SC-005: Identical inputs → byte-identical outputs
- SC-008: Privacy level ≥N>3 intermediate addresses or ZKP

### Tests for User Story 2 (Contract & Integration)

**Write tests FIRST - ensure they FAIL before implementation**

- [ ] T049 [P] [US2] Create tests/contract/test_plan_generation_contracts.py: verify TransactionPlan structure, no signatures present, custody proof format, expected boundary statement
- [ ] T050 [P] [US2] Create tests/integration/test_privacy_routing.py: submit validated quote, verify plan includes routing strategy, intermediate addresses, privacy_level, timing spec
- [ ] T051 [P] [US2] Create tests/integration/test_plan_determinism.py: identical validated quote → byte-identical plan for 10 iterations; hash comparison
- [ ] T052 [US2] Create tests/integration/test_privacy_boundaries.py: verify plan response includes exact text: "No signatures are applied; no funds are moved; user retains full control; plan is reversible until user authorization"

### Implementation for User Story 2

- [ ] T053 [P] [US2] Create src/routing/privacy_strategies.py with privacy routing selector: select_privacy_strategy(quote: SwapQuote, config: dict) → RoutingStrategy; implement 3 strategies (direct, intermediate, bridge-assisted)
- [ ] T054 [P] [US2] Create src/routing/router_allowlist.py with validate_router(route: RoutingStrategy) → bool; check against config/routes.yaml whitelist
- [ ] T055 [P] [US2] Create src/routing/dex_aggregator.py stub: aggregate DEX quotes for intermediate swaps; name DEX sources (Uniswap v3, SushiSwap, etc.); actual aggregation in Phase 2
- [ ] T056 [US2] Create src/agent/swap_planning_agent.py with main agent logic: async orchestrate_plan_generation(quote: SwapQuote) → TransactionPlan; use Claude SDK with temperature=0 for determinism
- [ ] T057 [US2] Implement src/validation/custody_validators.py: generate_custody_proof_for_plan(plan: TransactionPlan) → CustodyProof; create merkle proof structure and commitment preimage
- [ ] T058 [US2] Extend src/main.py to handle "generate_plan" action: parse validated quote, call orchestrate_plan_generation(), return plan JSON with routing, proofs, custody boundaries
- [ ] T059 [US2] Implement privacy_level calculation in TransactionPlan: count intermediate_addresses or verify ZKP presence; ensure ≥3 intermediaries
- [ ] T060 [US2] Create src/logging/plan_logger.py with log_plan_generation(quote, plan, result) ensuring zero plaintext amounts/addresses; only log hashes, threat detections, gate results
- [ ] T061 [US2] Add determinism verification: hash final plan output and log hash; allow re-verification of determinism property

**Checkpoint**: User Story 2 complete. Plans are privacy-preserving, include custody proofs, deterministic output, no plaintext logging. Pass independent test. Ready for User Story 3.

---

## Phase 5: User Story 3 - Adversarial Input Rejection via Structured Policies (Priority: P2)

**Goal**: Implement comprehensive layered filtering that detects and rejects threat patterns before L2 validation and after LLM planning. All rejections structured for audit. Threat catalog covers: token spoofing, decimal exploits, unusual parameters, replay attacks.

**Independent Test**: Submit known threat patterns and verify (1) each threat rejected, (2) rejection reason specific and traceable, (3) threat classification codes logged, (4) >90% detection accuracy on security researcher test catalog.

**Success Criteria** (from spec):
- SC-004: 100% accuracy on defined threats; <1% false positives
- SC-007: >90% detection on real-world threat catalogs (first 3 iterations)

### Tests for User Story 3 (Contract & Integration)

**Write tests FIRST - ensure they FAIL before implementation**

- [ ] T062 [P] [US3] Create tests/contract/test_threat_spoofing.py: test token address 1-char mutations against spoofing detector; verify THREAT_TOKEN_SPOOFING rejection
- [ ] T063 [P] [US3] Create tests/contract/test_threat_decimal.py: test decimal precision exploits (0.00000001, rounding attacks) against decimal validator; verify THREAT_DECIMAL_EXPLOIT rejection
- [ ] T064 [P] [US3] Create tests/contract/test_threat_unusual_params.py: test unusual parameters (slippage 100%, extreme amounts) against policy; verify THREAT_UNUSUAL_PARAMETERS rejection
- [ ] T065 [US3] Create tests/integration/test_threat_replay.py: submit identical requests <100ms apart; verify second rejected with THREAT_REPLAY_ATTEMPT
- [ ] T066 [US3] Create tests/integration/test_threat_catalog.py: provide security researcher threat patterns; verify >90% detection accuracy

### Implementation for User Story 3

- [ ] T067 [P] [US3] Expand src/validation/threat_catalog.py: add comprehensive threat pattern definitions with regex/matching logic for each threat type; enable YAML-based policy updates
- [ ] T068 [P] [US3] Create src/agent/l1_filter.py with pre_planning_threat_check(quote: SwapQuote) → Optional[AdversarialThreat]; detect spoofing, decimals, replay before agent
- [ ] T069 [P] [US3] Create src/agent/l3_filter.py with post_planning_threat_check(plan: TransactionPlan) → Optional[AdversarialThreat]; verify plan doesn't violate custody/privacy after agent
- [ ] T070 [US3] Implement threat detection replay cache in src/market/quote_cache.py: track recent quote hashes (100ms window); detect and reject duplicates
- [ ] T071 [US3] Extend src/logging/threat_reporter.py with structured threat classification: threat_code, threat_type, detected_field, rejection_reason, timestamp; ensure audit-ready format
- [ ] T072 [US3] Create src/validation/threat_severity.py with classify_threat_severity(threat: AdversarialThreat) → ("INFO" | "WARNING" | "CRITICAL"); configure thresholds per threat type
- [ ] T073 [US3] Extend src/main.py to invoke L1 filter before planning and L3 filter after planning; return threat rejection if detected
- [ ] T074 [US3] Add comprehensive threat logging: log each threat detected (L1 pre/L3 post); include threat code, field, policy threshold, rejection reason

**Checkpoint**: User Story 3 complete. Adversarial detection comprehensive. >90% threat detection verified. All threat patterns structured for audit. All 3 user stories now independently functional.

---

## Phase 6: Integration & End-to-End Testing

**Purpose**: Verify all user stories work together; validate performance targets; integration testing

**Duration**: ~6 hours

- [ ] T075 [P] Create tests/integration/test_full_workflow.py: end-to-end test from quote validation → planning → adversarial filtering with realistic inputs (WETH→USDC, 10 ETH)
- [ ] T076 [P] Create tests/integration/test_performance.py: measure response times (validate_quote <100ms, plan generation <3s, full flow <5s); set pytest markers for performance gates
- [ ] T077 Create tests/integration/test_error_handling.py: test error paths (missing market data, invalid RPC, malformed JSON input); verify graceful rejection
- [ ] T078 Write tests/performance/benchmark.py: benchmark determinism verifier, threat detection, custody proof generation; profile hot paths
- [ ] T079 Create integration test report documenting all stories working correctly, performance metrics, threat detection stats

**Checkpoint**: All user stories integrated. Performance targets validated. End-to-end workflows tested.

---

## Phase 7: Documentation & Deployment

**Purpose**: Complete user-facing documentation, deployment, and operational guidance

**Duration**: ~5 hours

- [ ] T080 [P] Verify docs/ARCHITECTURE.md: diagrams showing L1 filter → L2 gates → agent → L3 filter → outputs
- [ ] T081 [P] Verify docs/THREAT_CATALOG.md: document all threat patterns with examples and rejection codes
- [ ] T082 [P] Create docs/OPERATIONAL_RUNBOOK.md: configuration, monitoring, alert rules for threat detection
- [ ] T083 Create docs/DEPLOYMENT.md: Docker setup (Dockerfile, compose), environment variables, API endpoint documentation
- [ ] T084 Validate quickstart.md walkthrough: run installation steps, first run, second run, threat test scenarios; document any gaps
- [ ] T085 Create CHANGELOG.md documenting Phase 2 completion, all features, breaking changes (none expected)

**Checkpoint**: Documentation complete. Deployment ready.

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Final code quality, security hardening, test coverage, and release preparation

**Duration**: ~4 hours

- [ ] T086 [P] Run pytest with coverage report; ensure >95% coverage on src/validation/, src/agent/, src/models/
- [ ] T087 [P] Run security linting: bandit for security issues, safety for dependency vulnerabilities
- [ ] T088 [P] Code formatting: black src/ tests/, flake8 compliance
- [ ] T089 Run determinism verification suite: hash comparison on 100 identical runs; verify zero variance
- [ ] T090 Conduct security code review: manual review of validation gates, threat filters, custody proofs for bypass opportunities
- [ ] T091 Verify all threat patterns covered: cross-check threat_catalog.py against spec threats + researcher-provided patterns
- [ ] T092 Update README.md with security features, threat detection capabilities, determinism guarantees
- [ ] T093 Final commit: "Feature 001 Phase 2 Complete: All user stories + integration + documentation + security review"

**Checkpoint**: Code quality verified. Security review complete. All gates passing. Release-ready.

---

## Dependencies & Execution Order

### Phase Dependencies

```
Phase 1: Setup
    ↓
Phase 2: Foundational (BLOCKING - no user stories until 100% complete)
    ├→ Phase 3: User Story 1 (P1)
    ├→ Phase 4: User Story 2 (P1) [depends on US1 code patterns, not blocking]
    └→ Phase 5: User Story 3 (P2) [depends on US1/US2 code patterns, not blocking]
    ↓
Phase 6: Integration & E2E Testing
    ↓
Phase 7: Documentation & Deployment
    ↓
Phase 8: Polish & Security Review
```

### Critical Path

**Minimum viable implementation (MVP)**:
1. ✅ Phase 1: Setup (required foundation)
2. ✅ Phase 2: Foundational (BLOCKING - required for any user story)
3. ✅ Phase 3: User Story 1 (P1 - MVP delivers quote validation)
4. ⏹️ **STOP and VALIDATE** - Test US1 independently
5. Deploy/demo User Story 1 MVP if ready

**For full feature release add**:
1. Phase 4: User Story 2 (P1 - adds plan generation)
2. Phase 5: User Story 3 (P2 - adds adversarial hardening)
3. Phase 6-8: Integration, docs, security review

### User Story Dependencies

- **US1 (Quote Validation)**: None - can start after Phase 2 foundational
- **US2 (Plan Generation)**: Logically depends on US1 (need validated quote before planning), but code-independent for parallel work
- **US3 (Adversarial Rejection)**: Logically feeds into US1/US2 filtering layers, but can be developed in parallel

### Parallelizable Opportunities

**Within Phase 2 Foundational**:
- T010-T012: All logging tasks [P] can run in parallel
- T014-T018: All 5 entity models [P] can be parallelized
- T020-T023: Validation framework [P] tasks can run parallel
- T025-T026: Market integration [P] can run parallel
- T033-T035: Contract tests [P] can run parallel

**Within Phase 3 US1**:
- T037-T040: All US1 tests [P] can run parallel
- T041-T043: All validation expansion [P] can run parallel
- After tests pass: T044-T048 sequential (dependencies on test outcomes)

**Within Phase 4 US2**:
- T049-T052: All US2 tests [P] can run parallel
- T053-T055: All routing tasks [P] can run parallel
- After tests: T056-T061 sequential

**Within Phase 5 US3**:
- T062-T066: All US3 tests [P] can run parallel
- T067-T069: Threat catalog/filters [P] can run parallel
- After tests: T070-T074 sequential

**Phase 6+ Integration**:
- T075-T076: Integration tests [P] can run parallel

### Parallel Team Strategy (3 Developers)

```
Timeline           Developer A              Developer B           Developer C
────────────────────────────────────────────────────────────────────────────────
Weeks 1-2          Phase 1 +                (assist A)            (assist A)
                   Phase 2 (all together)
                   ↓
Weeks 3-4          Phase 3: US1             Phase 4: US2          Phase 5: US3
                   Quote validation         Plan generation       Adversarial
                   (all tests [P]           (all tests [P]        (all tests [P]
                    parallelized)            parallelized)         parallelized)
                   ↓
Week 5             Phase 6: Integration     Phase 6: E2E Perf     Phase 6: Error
                   workflow test            benchmark             handling
                   ↓
Week 6             Phase 7+8: Docs, Security Review, Polish (together)
                   ↓
Week 6             RELEASE ✅
```

---

## Implementation Strategy

### MVP First (User Story 1)

The minimum viable product includes only User Story 1:

1. ✅ Complete Phase 1: Setup (4 hours)
2. ✅ Complete Phase 2: Foundational (12 hours)
3. ✅ Complete Phase 3: User Story 1 (8 hours)
4. ✅ **STOP and VALIDATE**: Submit test quotes, verify deterministic rejection, verify no overrides
5. **OPTIONAL**: Phase 7 docs + Phase 8 polish if ready to release
6. **Estimated MVP Release**: Week 2

### Incremental Delivery (All User Stories)

Full feature release adds on top of MVP:

1. MVP complete (Week 2)
2. Add Phase 4: User Story 2 (Week 3) → Test plan generation independently
3. Add Phase 5: User Story 3 (Week 4) → Test threat detection independently
4. Add Phase 6: Integration testing (Week 5) → Verify all stories work together
5. Add Phase 7: Documentation (Week 5) → User guides, runbooks
6. Add Phase 8: Polish & security review (Week 6) → Final quality gates
7. **Estimated Full Release**: Week 6

### Recommended Sequence (Single Developer)

Execute phases sequentially:

1. Phase 1 → Phase 2 → Phase 3 (US1 working) → validate independently
2. Phase 4 (US2) → Phase 5 (US3) → Phase 6 (integration)
3. Phase 7 → Phase 8 → Release

**Estimated Timeline**: 8 weeks (one developer)

---

## Task Checklist Format Reference

Every task in this document follows the required format:

```
- [ ] T[ID] [P?] [Story?] Description with exact file path
```

**Components**:
- ✅ Checkbox: `- [ ]`
- ✅ Task ID: Sequential (T001, T002, ...)
- ✅ [P] marker: Included on parallelizable tasks
- ✅ [Story] label: US1/US2/US3 for user story phases
- ✅ Description: Clear action with exact file path

**Examples from this document**:
- ✅ `- [ ] T001 Create project directory structure per plan.md layout`
- ✅ `- [ ] T014 [P] Create src/models/swap_quote.py: SwapQuote dataclass...`
- ✅ `- [ ] T037 [P] [US1] Create tests/contract/test_quote_validation_gates.py...`
- ✅ `- [ ] T075 [P] Create tests/integration/test_full_workflow.py...`

---

## Success Validation

### Per User Story

**User Story 1 (Quote Validation)** ✅ Success Validation:
- [ ] Test: Submit 10 test quotes (safe/unsafe/malformed) → verify explicit rejections
- [ ] Test: Submit identical quote 100x → verify deterministic identical outputs (hash comparison)
- [ ] Test: Attempt override of validation failure → verify system rejects override attempt
- [ ] Metric: Validation response <100ms, 100% accuracy on test cases

**User Story 2 (Plan Generation)** ✅ Success Validation:
- [ ] Test: Generate 5 plans from validated quotes → verify all include custody proofs
- [ ] Test: Verify plaintext transaction content NOT in audit logs (only hashes/metadata)
- [ ] Test: Generate identical plan 10x → verify byte-identical outputs
- [ ] Test: Verify output includes exact boundary statement: "No signatures are applied..."
- [ ] Metric: <3s response time, 100% determinism, zero logged secrets

**User Story 3 (Adversarial Rejection)** ✅ Success Validation:
- [ ] Test: Submit 20 threat patterns (spoofing, decimals, unusual, replay) → verify all rejected
- [ ] Test: Verify threat classification codes in audit logs
- [ ] Test: Verify rejection reason specific and traceable
- [ ] Test: Run security researcher threat catalog → verify >90% detection
- [ ] Metric: 100% accuracy on defined threats, <1% false positives

### Overall Release Validation

- [ ] Phase 2 Foundational: All 5 entities created, validation framework immutable, CLI skeleton functional
- [ ] Phase 3+: All user stories independently testable; can stop at any checkpoint
- [ ] Phase 6: All stories work together; performance targets met
- [ ] Phase 7: Documentation complete, deployment instructions clear
- [ ] Phase 8: Code quality >95% coverage, security review passed, no bypass opportunities

---

## Test-First Development Note

**Important**: For all tasks marked with tests (T037-T066), follow TDD approach:

1. Write the test FIRST (see test task)
2. Verify test FAILS (red state)
3. Implement minimal code to make test pass (green state)
4. Refactor for clarity (refactor state)

This ensures:
- Acceptance criteria are clear before coding
- Code covers all specified scenarios
- Determinism properties are verifiable
- Threat patterns are comprehensively tested

---

## Notes

- All task IDs are sequential (T001-T093)
- [P] tasks = parallelizable (different files, no dependencies)
- [US#] tasks = mapped to specific user story for traceability
- Each task has exact file path for implementation
- Phases build on each other; later phases unblock when earlier phases complete
- Commit after each task or logical group for audit trail
- Stop at any checkpoint to validate story independently
- No cross-story dependencies should block parallel development
