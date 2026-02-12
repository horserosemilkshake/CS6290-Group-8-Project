# Feature Specification: Secure Cryptocurrency Swap Planning Agent

**Feature Branch**: `001-swap-plan`  
**Created**: 2026-02-13  
**Status**: Draft  
**Input**: User description: "Build an agent that can help me generate safe, privacy‑preserving cryptocurrency swap transaction plans using layered security guardrails. Swap requests are processed through deterministic validations that block unsafe quotes and cannot be overridden by the model. Transaction planning never involves signing or broadcasting, and all actions stay within strict custody boundaries. Within each planning flow, adversarial inputs are filtered, analyzed, and rejected using structured, testable policies."

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Deterministic Quote Validation (Priority: P1)

User receives a cryptocurrency swap request from another party and needs to validate whether the quoted price and terms are acceptable before proceeding to planning. The system MUST apply non-overridable, deterministic security gates that evaluate the quote against strict policy rules and explicitly reject unsafe proposals.

**Why this priority**: Quote validation is the critical security boundary. Unsafe quotes accepted here compromise the entire transaction plan. This validates Principle II (Deterministic Security Enforcement) from the constitution.

**Independent Test**: Can be fully tested by submitting various quote responses (favorable, unfavorable, malformed, extreme spreads) and verifying that only safe quotes pass validation gates. System MUST explicitly reject unsafe quotes with clear reasoning.

**Acceptance Scenarios**:

1. **Given** a swap quote with price within 2% of market rate, **When** system evaluates the quote, **Then** quote passes all validation gates and proceeds to planning
2. **Given** a swap quote with >5% spread from market rate, **When** system evaluates the quote, **Then** system explicitly rejects with reasoning: "Spread exceeds maximum allowed threshold"
3. **Given** a swap quote with missing required fields (slippage tolerance, token addresses), **When** system validates, **Then** system rejects with field-specific error details and cannot be overridden
4. **Given** a quote during network instability or unverifiable market conditions, **When** system evaluates confidence, **Then** system rejects proactively with uncertainty reasoning

---

### User Story 2 - Privacy-Preserving Swap Plan Generation (Priority: P1)

Agent creates a transaction plan that routes the swap through privacy-safe mechanisms—using intermediary addresses, timing delays, or multi-step choreography—that minimize transaction linkability while keeping all funds under user custody. Plan MUST never expose transaction intent in plaintext logs and MUST maintain cryptographic proof of fund control throughout.

**Why this priority**: Generates the core value—P1 because swap planning cannot proceed until both validation (US1) and plan generation (US2) work. This validates Principles I (Privacy) and IV (Custody-Safe) from the constitution.

**Independent Test**: Can be fully tested by verifying that generated plans (1) include privacy routing decisions documented in plan output, (2) never write transaction intent to logs, (3) include custody transfer proofs, (4) keep signatures out of planning phase, and (5) produce deterministic output for identical inputs.

**Acceptance Scenarios**:

1. **Given** a validated swap quote (ETH ↔ USDC, 10 ETH at market rate), **When** agent generates plan, **Then** plan includes: custody transfer proof format, privacy routing decisions, intermediate address strategy, timing specification, and all tokens remain under user control throughout sequence
2. **Given** swap plan generation initiated, **When** agent writes to logs/events, **Then** plan details never appear in plaintext—only cryptographic commitments (hash digests, zero-knowledge circuit proofs) and operation metadata appear in logs
3. **Given** a generated plan, **When** user reviews the plan, **Then** plan includes explicit statement: "No signatures required; no funds moved; plan is custody-safe and reversible until execution authorization"
4. **Given** identical input parameters submitted twice, **When** agent generates plans, **Then** both plans produce byte-for-byte identical routing decisions and cryptographic commitments (deterministic output requirement from Principle II)

---

### User Story 3 - Adversarial Input Rejection via Structured Policies (Priority: P2)

Agent implements layered filtering that detects and rejects threat patterns in swap requests: token address spoofing attempts, unusual decimal precision exploits, extreme slippage tolerances designed to fail, timing-based re-entry attacks, or requests structured to bypass validation. All rejections are logged with structured threat classification.

**Why this priority**: P2 because this hardens the P1 flows. Prevents sophisticated attacks while maintaining deterministic behavior. Validates Principle III (Adversarial Robustness) from the constitution.

**Independent Test**: Can be fully tested by submitting catalogs of known threat patterns (malformed addresses, spoofed tokens, decimal exploits, replay attempts) and verifying: (1) each threat is rejected, (2) rejection reason is specific and traceable, (3) rejection rule is policy-enforced not heuristic, (4) threat classification logs are structured for audit.

**Acceptance Scenarios**:

1. **Given** a swap request with token address that is 1 character different from authorized token, **When** system validates, **Then** system rejects with threat classification: "THREAT_TOKEN_SPOOFING: Address mismatch detected against whitelist"
2. **Given** a request with slippage tolerance set to 100% (designed to guarantee failure), **When** system evaluates, **Then** system rejects with: "THREAT_UNUSUAL_PARAMETERS: Slippage tolerance exceeds safety threshold—likely attack pattern"
3. **Given** consecutive identical requests submitted within 100ms (replay attack), **When** system processes second request, **Then** system rejects second request with threat type: "THREAT_REPLAY_ATTEMPT: Duplicate request detected within skip window"
4. **Given** a request with decimal precision manipulation (e.g., token amount 0.00000001 attempting to trigger rounding error), **When** system validates amounts, **Then** system rejects with: "THREAT_DECIMAL_EXPLOIT: Amount precision outside safe range"
5. **Given** all rejected requests, **When** audit logs are reviewed, **Then** each rejection includes: timestamp, threat classification code, user context, and reason—formatted for structured analysis without exposing transaction content

---

### Edge Cases

- What happens when market data becomes unavailable during quote validation? → System MUST reject quote with reason: "UNKNOWN_MARKET_STATE: Cannot validate against market rates"
- What happens when user submits a swap amount that exceeds their available balance? → System MUST reject before planning with: "INSUFFICIENT_CUSTODY: Swap amount exceeds verified balance"
- What happens when gas prices spike dramatically between plan generation and requested execution window? → System MUST flag in plan: "PLAN_CONDITION_CHANGED: Gas estimate outdated; re-validate before execution"
- What happens when a requested token is de-listed from available exchanges? → System MUST reject during validation: "TOKEN_UNAVAILABLE: Requested token no longer available on platform"
- What happens when swap request uses privacy-mixing addresses that are already on sanction lists? → System MUST reject proactively: "CUSTODY_RISK_DETECTED: Routing through flagged addresses violates policy"

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST validate all swap quotes against deterministic security gates (max spread %, minimum market confidence, required field presence) with explicit rejection if any gate fails
- **FR-002**: System MUST generate swap plans that route through privacy-preserving mechanisms (intermediate addresses, timing choreography, cryptographic commitments) without exposing transaction intent to logs
- **FR-003**: System MUST append custody transfer proofs to every generated plan showing that user maintains cryptographic control throughout the swap sequence
- **FR-004**: System MUST reject any quote or plan request that includes threat patterns matching adversarial policy catalog (token spoofing, decimal exploits, replay attempts, replay windows)
- **FR-005**: System MUST produce deterministic, reproducible output: identical input parameters MUST generate identical plan routing decisions and cryptographic commitments across all executions
- **FR-006**: System MUST log all security-relevant events (quote validation decisions, threat classifications, rejections) using structured, tamper-evident format without recording transaction content in plaintext
- **FR-007**: System MUST provide explicit custody boundary statements in every generated plan: "No signatures are applied; no funds are moved; user retains full control; plan is reversible until user authorization"
- **FR-008**: System MUST perform quote validation with no human override capability—validation failures MUST block progression to planning, and system MUST reject any request to bypass validation gates
- **FR-009**: System MUST implement quote validation with <100ms latency to prevent timing-based arbitrage attacks exploiting validation delays
- **FR-010**: System MUST support multiple privacy routing strategies (direct swap, liquidity pool routing, DEX aggregator routing, bridge-assisted routing) and select strategy deterministically based on custody safety and privacy properties

### Key Entities

- **SwapQuote**: Represents the published swap offer (from_token, to_token, from_amount, to_amount, slippage_tolerance, market_confidence, timestamp). Does NOT require signature; is informational only.
- **ValidationGate**: Represents a deterministic security policy (gate_name, threshold, enforcement_level="REJECT_NO_OVERRIDE", test_function). Each gate is non-bypassable.
- **TransactionPlan**: Represents the custody-safe execution plan (quote_reference, routing_strategy, intermediate_addresses, custody_proofs, timing_sequence, privacy_level, execution_window). Contains NO signatures; contains only planning information.
- **AdversarialThreat**: Represents detected threat patterns (threat_type, detected_field, actual_value, policy_threshold, rejection_reason, threat_classification_code).
- **CustodyProof**: Represents cryptographic evidence of user control (proof_type, proof_content, verification_method). Examples: preimage reveal, multi-sig authorization structure, cryptographic commitment verification.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All swap quotes are validated and decision (approve/reject) returned in <100ms with 100% consistency (deterministic validation required)
- **SC-002**: Zero swap requests bypass validation gates—any attempt to override validation results in explicit rejection with audit trail
- **SC-003**: 100% of generated plans include explicit custody boundary statement and custody proof format
- **SC-004**: All adversarial threat patterns from defined policy catalog are detected and rejected with 100% accuracy; zero false negatives; false positives <1%
- **SC-005**: Identical swap requests submitted twice produce byte-identical plan outputs (determinism requirement) in <100 executions verified by cryptographic hash comparison
- **SC-006**: 100% of security-relevant event logs use structured format (JSON or equivalent); zero plaintext transaction contents appear in logs
- **SC-007**: Agent correctly identifies and rejects at least 90% of real-world threat patterns in security researcher-provided test catalogs within first three iterations
- **SC-008**: Privacy metrics: each generated plan routes through either (a) N>3 intermediate addresses, or (b) cryptographic commitment with zero-knowledge proof, or (c) both—measured per plan
- **SC-009**: Planning fee overhead <5% of quoted swap value—ensures user incentive to use safe planning vs. unsafe direct execution
- **SC-010**: All plans remain reversal-safe for user-defined execution window (default 24 hours); after window closes, plan MUST be explicitly re-validated

---

## Assumptions & Constraints

- Market price data is provided by a verified external oracle with <10 minute staleness
- User's available balance is verified through cryptographic merkle proof before planning
- Gas price estimates are refreshed hourly; plans older than 1 hour require re-estimation
- Privacy routing assumes access to at least 3 distinct routing strategies (DEX, AMM, bridge)
- Adversarial threat definitions are established and maintained by security team (separate change process)
- Plan generation does NOT sign transactions; signing is responsibility of downstream execution layer
- System operates in deterministic execution environment; no randomness in validation or planning logic except for cryptographically-secure random nonce generation (documented explicitly)

---

## Alignment with Secure Exchange Constitution

- **Principle I (Privacy Preservation)**: All plans route through privacy mechanisms; transaction intent never logged in plaintext; cryptographic commitments used instead of content exposure
- **Principle II (Deterministic Security Enforcement)**: Quote validation gates are deterministic and non-overridable; identical inputs produce identical validation results; structured rejection policies
- **Principle III (Adversarial Robustness)**: Layered filtering rejects threat patterns; threat classifications structured for audit; assumes well-resourced adversaries with access to request patterns
- **Principle IV (Custody-Safe Transaction Planning)**: All plans include custody transfer proofs; no funds move during planning; plans include explicit custody boundary statements; atomic execution sequence enforced
- **Principle V (Strict Development and Governance Standards)**: All security events logged with audit trail; code review required for validation gate changes; test coverage >95% for validation and threat filtering; no breaking changes to security APIs
