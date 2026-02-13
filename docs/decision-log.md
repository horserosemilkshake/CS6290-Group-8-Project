# Decision Log: LLM-Driven DeFi Agent Security & Privacy Evaluation

**Project**: CS6290 - Privacy-enhancing Technologies
**Team Size**: 5 members  
**Duration**: 10 weeks  
**PM**: efan  
**Last Updated**: 2026-02-13

---

## Executive Summary

This decision log documents the key architectural, scope, and organizational decisions made during the project planning phase. As PM, I facilitated alignment between team discussions, course requirements, and technical feasibility to establish a clear, executable project scope that maximizes our chances of achieving full marks while ensuring meaningful individual contributions.

---

## Decision 1: Core Research Question & Project Framing

**Date**: Week 1  
**Decision**: Adopt "Treasury Agent" model with layered defense evaluation

**Context**:  
Initial discussions explored multiple directions:
- Option A: On-chain Treasury Agent (AI manages a vault with policy enforcement)
- Option B: DEX Execution Agent (automated trading with MEV risks)
- Option C: Governance Voting Agent (privacy-focused delegation)

**Analysis** (PM synthesis from AI consultation + team input):

| Criterion | Treasury (A) | DEX Trading (B) | Governance (C) |
|-----------|--------------|-----------------|----------------|
| Spec-driven clarity | ✅ High (clear invariants) | ⚠️ Medium (price-dependent) | ⚠️ Medium (governance context) |
| Attack surface | ✅ Well-bounded | ⚠️ MEV complexity | ⚠️ Implementation heavy |
| PET alignment | ✅ Privacy + security | ⚠️ Primarily security | ✅ Strong privacy focus |
| Reproducibility | ✅ Deterministic | ⚠️ Market-dependent | ⚠️ Proposal-dependent |
| Team consensus | ✅ "A is good track" | - | - |

**Decision Rationale**:
- **Why Treasury**: Provides clearest security boundaries (funds custody), naturally supports spec-driven approach (contract-enforced invariants), and enables clean before/after measurement
- **PET Angle**: Agent-mediated execution introduces privacy risks (prompt leakage, RPC metadata, transaction linkability) that we can systematically address
- **Risk Mitigation**: Avoids market dependency and oracle manipulation complexities while still demonstrating real blockchain risks (allowance abuse, replay, recipient hijacking)

**Trade-offs Accepted**:
- ❌ Less "exciting" than live DEX trading
- ✅ More rigorous, reproducible, and defensible for academic evaluation

---

## Decision 2: Project Scope Definition

**Date**: Week 1-2  
**Decision**: Minimal viable scope with maximum measurability

**Final Scope** (PM consolidation):

### Supported Actions
- **APPROVED**: `approve(spender, amount)` + `swapExactTokensForTokens(...)`
- **DEFINITION CLARIFICATION** (response to team question): "approve" refers to **ERC20 token approval** (not agent approval of transactions). Agent constructs the approval transaction, which must pass guardrails before owner signing.

### Environment
- **Primary**: Local chain (Foundry anvil / Hardhat fork) for reproducibility
- **Optional**: Sepolia testnet for final demo

### Whitelist Constraints
- **Tokens**: 2 tokens (team consensus: "2 token")
- **Router**: 1 router address (team consensus: "1 router")
- **Recipient**: Must be Treasury Vault contract (no external EOA transfers)

**PM Justification**:
This scope minimizes implementation complexity while providing sufficient attack surface for meaningful evaluation. The constraints are engineering decisions, not limitations—they enable reproducible experiments with fixed parameters.

---

## Decision 3: Non-Trivial Risk Selection

**Date**: Week 2  
**Decision**: **Allowance Abuse** as primary risk, with privacy as co-equal PET focus

**Considered Risks**:
1. Allowance abuse (approve unlimited amounts to malicious spender)
2. MEV/sandwich attacks
3. RPC/LLM privacy leakage
4. Prompt injection leading to transaction manipulation

**Selection Rationale**:

**Primary (Security): Allowance Abuse**
- Most concrete DeFi-specific risk
- Directly measurable (unlimited vs. capped approvals)
- Enables clear spec: `S-02: approval_amount ≤ CAP ∧ spender ∈ ALLOWLIST`
- Addresses course requirement for "non-trivial risk" (Milestone 2)

**Co-Primary (PET): Privacy Leakage**
- Aligns with course PET focus
- Measurable via disclosure score (wallet address, balances in prompts/logs/RPC)
- Demonstrates privacy-enhancing mechanisms (redaction, local inference)

**Deferred Risks**:
- MEV: Acknowledged but not primary (simulation complexity vs. time budget)
- Complex prompt injection: Covered through adversarial test suite but not separate category

**PM Note**: This dual-focus structure directly addresses earlier feedback that "mainline not clear"—we now have security AND privacy as co-equal research questions.

---

## Decision 4: Defense Layer Architecture

**Date**: Week 2  
**Decision**: Three-configuration comparative evaluation

| Config | Defense Layer | Enforcement Point | Purpose |
|--------|---------------|-------------------|---------|
| **Config 0** | None (Baseline) | - | Demonstrate attack success without defenses |
| **Config 1** | L1: Off-chain Guardrails | Pre-signature spec validation | Language-level + rule-based filtering |
| **Config 2** | L1 + L2: On-chain Enforcement | Smart contract invariants | Unstoppable contract-level limits |

**Measured Trade-offs**:
- Attack Success Rate (ASR): Expected Config0 > Config1 > Config2
- False Rejection Rate (FRR): Expected Config0 < Config1 < Config2  
- Gas Cost: Expected Config0 < Config1 < Config2
- Latency: Expected Config0 ≈ Config1 < Config2

**PM Strategic Note**:  
This structure transforms our project from "a demo" into "a comparative study"—exactly what the rubric rewards. Each config becomes a data point in our empirical evaluation.

---

## Decision 5: Specification Framework

**Date**: Week 2-3  
**Decision**: Gherkin-based Given/When/Then specs with Threat→Spec→Test mapping

**Approach**:
- Each security/privacy invariant gets a `S-XX` identifier
- Specifications written as executable acceptance criteria (Gherkin format)
- Explicit mapping: Threat → Spec → Test → Metric

**Example Spec** (refined during PM-AI iteration):
```gherkin
Feature: S-02 Approval Amount Limit
  Scenario: Agent proposes approval within cap
    Given the owner has configured MAX_APPROVAL_CAP = 1000 USDC
    When the agent proposes approve(spender=0xRouter, amount=500)
    Then the guardrail MUST allow the transaction
    
  Scenario: Agent proposes excessive approval
    Given the owner has configured MAX_APPROVAL_CAP = 1000 USDC  
    When the agent proposes approve(spender=0xRouter, amount=10000)
    Then the guardrail MUST reject with reason="S-02: APPROVAL_EXCEEDS_CAP"
```

**PM Rationale**:  
This addresses the spec-driven bonus criteria and provides clear acceptance criteria for testing. Each team member's Evidence Pack can reference specific spec IDs they validated.

---

## Decision 6: Team Division of Labor

**Date**: Week 2  
**Decision**: Role-aligned ownership with mandatory cross-validation

### Role Assignments

| Member | Primary Module | Secondary Responsibility | Evidence Focus |
|--------|----------------|-------------------------|----------------|
| **efan (PM)** | Integration + Report | SCOPE.md, interfaces.md, reproducibility | Coordinated final deliverables + results synthesis |
| **Member B** | Architecture & Specification | Given/When/Then criteria + measurement protocol | Spec revision logs + traceability tables |
| **Member C** | Agent Backend & Tx Builder | Natural language → TxPlan pipeline | Transaction construction logs + API docs |
| **Member D** | Harness & Artifact Infrastructure | Experiment automation + metrics pipeline | Reproducible runs + artifact integrity checks |
| **Member E** | Security & Verification | Threat model + adversarial/benign case labeling | Failure analysis + security summary tables |

**Cross-Validation Requirement** (PM mandate):
- Every milestone: Each member must validate ≥1 peer's work
- Documented in Evidence Pack "Validation performed" section
- Prevents siloed work and ensures collective understanding

**Rotation Plan** (Week 6):
- B ↔ E swap validation duties (spec consistency ↔ threat/label consistency)
- C ↔ D perform interface challenge (agent output schema ↔ harness input contract)
- Documented as "peer challenge & response" in Evidence Packs

---

## Decision 7: Metrics & Success Criteria

**Date**: Week 3  
**Decision**: Five quantitative metrics across security, usability, cost, and privacy

### Metrics Definition

1. **Attack Success Rate (ASR)**  
   - Definition: Percentage of malicious inputs resulting in policy-violating transactions
   - Target: Config0 > 80%, Config2 < 5%

2. **False Rejection Rate (FRR)**  
   - Definition: Percentage of legitimate requests incorrectly blocked
   - Target: Config2 < 10% (acceptable usability cost)

3. **Gas Overhead**  
   - Definition: Additional gas cost per transaction (Config X vs. Config 0)
   - Measurement: Mean + 95th percentile across test suite

4. **Latency**  
   - Definition: Time from user input → transaction ready for signing
   - Components: LLM inference + guardrail validation + contract simulation

5. **Privacy Disclosure Score** (PET focus)  
   - Definition: Count of sensitive fields in external communications
   - Fields: wallet address, balances, transaction history, intent details
   - Configs: Baseline (no redaction) vs. Privacy-enhanced (redaction + local inference)

**PM Note**: These metrics were refined through AI consultation to ensure they're (a) measurable with our test infrastructure, (b) comparable across configs, and (c) aligned with both security and PET evaluation criteria.

---

## Decision 8: Attack Dataset Composition

**Date**: Week 3  
**Decision**: Structured adversarial test suite with reproducible seeding

### Attack Categories

| Category | Example Attacks | Target Spec Violations | Quantity |
|----------|----------------|----------------------|----------|
| Allowance Abuse | Unlimited approval, unknown spender | S-02, S-03 | 20-30 |
| Recipient Hijacking | Transfer to attacker EOA | S-04 | 15-20 |
| Slippage Manipulation | High-slippage swaps | S-05 | 15-20 |
| Replay | Reuse command IDs / nonces | S-06 | 10-15 |
| Privacy Probing | Prompt extraction of wallet data | P-01, P-02 | 15-20 |

**Reproducibility Requirements** (PM mandate):
- All attacks generated with fixed seeds
- Attack dataset versioned with SHA-256 hashes
- `attacks/` directory structure: `attacks/<category>/<seed>_<hash>.json`

**Execution Ownership** (assigned to Member D):
- Integrate labeled attacks into automated harness pipelines
- Compute ASR/FRR/latency/gas metrics from standardized artifacts
- Maintain deterministic experiment scripts and artifact schemas

**Validation** (assigned to Member E):
- Random sample (N≥10) manually reviewed for label accuracy
- Cross-machine reproducibility test (same seed → same outputs)

---

## Decision 9: Milestone Deliverables & Evidence Standards

**Date**: Week 2-3  
**Decision**: Standardized Evidence Pack template for individual accountability

### Per-Milestone Requirements

**Every team member must submit**:
1. **Contributions** (2-5 bullets): Concrete, verifiable deliverables
2. **Evidence** (≥2 items): Links to code, logs, tests, artifacts
3. **Validation** (≥1 item): What you tested/verified (your work or peers')
4. **AI Transparency**: 1 adopted use + 1 rejected use with rationale

### Milestone Checkpoints

**M1 (Week 3-4): MVP Runthrough**
- Deliverable: Agent can construct valid TxPlan; smoke harness runs end-to-end; initial threat model + labeled test cases complete
- Evidence Standard: `make reproduce` runs end-to-end

**M2 (Week 6-7): Non-Trivial Risk Closed Loop**
- Deliverable: Allowance abuse threat addressed with full chain (Threat→Spec→Security Test Case→Harness→Metric)
- Evidence Standard: Three-config comparison with measurable ASR reduction

**M3 (Week 9-10): Final Report + Demo**
- Deliverable: Complete report, reproducible results, polished demo
- Evidence Standard: Report meets rubric; experiments repeatable on clean environment

**PM Accountability**:  
As PM, I'm responsible for ensuring:
- Milestone deadlines tracked and communicated
- Interface contracts (tx_candidate.json schema, results.csv format) frozen early
- Blockers surfaced and resolved before they cascade

---

## Decision 10: Reproducibility & Artifact Standards

**Date**: Week 3  
**Decision**: All experiments must be one-command reproducible

### Repository Structure
```
/
├── agent/          # LLM planner + tx construction
├── specs/          # Gherkin specs + threat mapping
├── contracts/      # Treasury vault + enforcement
├── attacks/        # Adversarial test dataset
├── experiments/    # Harness + evaluation scripts
├── results/        # Timestamped experiment outputs
├── report/         # LaTeX/Markdown source
├── SCOPE.md        # Frozen scope document
├── RUNBOOK.md      # Reproduction instructions
└── Makefile        # One-command orchestration
```

### Reproducibility Checklist
- [ ] `make reproduce` generates all figures/tables from scratch
- [ ] All random processes use fixed seeds (documented in RUNBOOK.md)
- [ ] Dependencies pinned (requirements.txt with exact versions)
- [ ] Results include environment metadata (OS, Python version, chain block number)

**PM Commitment**:  
I will personally verify reproducibility in a fresh environment before each milestone deadline. This is non-negotiable for full marks.

---

## Decision 11: Privacy-Enhancing Mechanisms (PET Focus)

**Date**: Week 4  
**Decision**: Implement measurable privacy controls for Config 2 (optional Config 3)

### Privacy Threat Model

**Sensitive Data Categories**:
1. Wallet identity (address, public key)
2. Asset holdings (balances, transaction history)
3. Intent details (swap amounts, target prices)
4. Transaction metadata (nonce, gas limits, timing patterns)

**Exposure Channels**:
- LLM API calls (if external provider used)
- RPC requests (balance queries, transaction simulation)
- Application logs (debugging output)
- Network traffic (WebSocket connections, HTTP requests)

### Privacy Controls (Implementation)

| Mechanism | Description | Measurement |
|-----------|-------------|-------------|
| Prompt Redaction | Strip wallet addresses from LLM inputs | Field count in prompts |
| Local Inference | Use local LLM (Llama/Mistral) vs. external API | External call count |
| RPC Minimization | Batch queries, cache balances | RPC request count |
| Log Sanitization | Redact sensitive fields in application logs | Sensitive field occurrences |

**Experimental Config**:
- **Config 2-Privacy**: Treasury-Strong + privacy controls enabled
- **Metric**: Disclosure score = weighted sum of exposed sensitive fields

**PM Note**: This directly addresses the critique—privacy is now a first-class metric, not an afterthought.

---

## Decision 12: Risk Mitigation & Contingency Planning

**Date**: Week 3  
**Decision**: Define clear scope boundaries and fallback options

### Known Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| LLM inference too slow | Medium | High (unusable latency) | **Fallback**: Use smaller local model or GPT-3.5-turbo with caching |
| Harness pipeline instability | Medium | High (non-reproducible results) | **Owner D**: Lock artifact schema, CI smoke runs, deterministic seeds |
| Test label quality variance | Medium | Medium | **Owner E**: Labeling rubric + dual review + disagreement log |
| Team member unavailability | Medium | Medium | **Cross-training**: Each module has documented interfaces + tests |
| Reproducibility failures | Medium | Critical | **PM mandate**: Weekly reproducibility checks starting Week 5 |

### Scope Creep Guards (PM Authority)

**Out of Scope** (Will reject if proposed):
- ❌ Multi-chain support
- ❌ Live mainnet deployment
- ❌ Complex DeFi strategies (multi-hop swaps, yield farming)
- ❌ Novel cryptographic protocols

**In-Scope Flexibility** (Can adjust if needed):
- ✅ Attack dataset size (20-50 per category)
- ✅ Privacy controls granularity
- ✅ Number of specs (10-20 acceptable range)

---

## Decision 13: Communication & Workflow Standards

**Date**: Week 2  
**Decision**: Async-first workflow with weekly sync + documented decisions

### Communication Channels

| Purpose | Channel | Frequency |
|---------|---------|-----------|
| Quick questions | WeChat group | Async, <24h response |
| Code review | GitHub PR comments | Within 48h of PR |
| Major decisions | Decision log (this document) | PM updates weekly |
| Technical blockers | WeChat + follow-up meeting | Escalate immediately |
| Milestone sync | Video call (30-45min) | Weekly (Sundays 8pm) |

### Workflow Rules (PM Enforced)

1. **PR Hygiene**:
   - Every PR linked to ≥1 spec ID
   - Description includes: what changed, why, how to verify
   - At least 1 reviewer approval required

2. **Evidence Documentation**:
   - Evidence artifacts committed to `/evidence/<member>/<milestone>/`
   - Naming convention: `YYYYMMDD_<artifact_type>_<description>`

3. **Conflict Resolution**:
   - Technical disagreements: Test both approaches, measure
   - Scope disagreements: PM has final call (documented here)

---

## Open Questions & Future Decisions

**Tracked for Resolution by Week 5**:

1. **LLM Selection**: Local (Llama 3.1) vs. API (GPT-4o-mini)?
   - **Trade-off**: Privacy/cost vs. quality/latency
   - **Decision deadline**: Week 4 (need for initial experiments)

2. **MEV Simulation**: Include basic front-running tests or defer?
   - **Current stance**: Optional, only if Week 7 capacity allows
   - **Fallback**: Acknowledge as limitation in report

3. **Formal Verification**: Explore Certora/Halmos for contract specs?
   - **Current stance**: Bonus if time permits, not required for full marks
   - **Assigned**: Member E to investigate feasibility (with C support if implementation changes are required)

---

## Changelog

| Date | Change | Rationale |
|------|--------|-----------|
| 2026-02-13 | Updated role ownership model (D=Harness, E=Security) | Align decision log with revised role-and-deliverables and timeline |
| 2025-02-12 | Initial decision log created | Consolidate PM work and team alignment |
| 2025-02-12 | Added Privacy-Enhancing Controls (Decision 11) | Address PET alignment feedback |
| 2025-02-12 | Clarified "approve" definition (Decision 2) | Response to team question about ambiguity |

---

## PM Reflection

This decision log represents ~15 hours of PM work including:
- Synthesizing 5+ hours of AI consultation on project structure
- Facilitating team consensus through WeChat discussions
- Analyzing course requirements and rubric alignment
- Creating standardized templates (Evidence Packs, specs, metrics)
- Defining clear interfaces to prevent integration chaos

**Key PM Contributions**:
1. **Scope Discipline**: Resisted feature creep, enforced MVP boundaries
2. **Risk Alignment**: Identified and addressed communication through explicit privacy focus
3. **Measurement Rigor**: Defined quantitative metrics before implementation
4. **Team Coordination**: Structured work to guarantee individual accountability via Evidence Packs
---

**Document Status**: Living document, updated weekly by PM  
**Version**: 1.1  
**Distribution**: All team members + course staff (if requested)
