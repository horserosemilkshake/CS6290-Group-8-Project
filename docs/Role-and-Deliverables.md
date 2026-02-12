This document defines **role-specific learning requirements, milestone deliverables, and expected workload** for the project **“Adversarially-Robust Minimal DeFi Transaction Planning Agent.”**

The goal is to ensure that each team member—assuming **only general computer science background (first-year master’s level)**—has:
- a clear responsibility boundary,
- achievable learning objectives,
- independent Evidence Pack material for each milestone,
- and a fair, well-balanced workload.

---

## Milestone Overview

| Milestone | Timeframe | Core Objective |
|---------|----------|----------------|
| Milestone 1 | Proposal & Plan | System definition + closed prototype loop |
| Milestone 2 | Midway Evidence | Early security results + non-trivial risk addressed |
| Milestone 3 | Final Integration | Consolidation, reproducibility, and report readiness |

---

## Role A — Lead / PM

### Role Summary
Owns project **scope, timeline, and decision-making**. Acts as the **single editor** for the final report and slides to ensure consistent narrative and technical alignment.

### Learning Requirements
- Basic DeFi concepts (swap, approve, router) at a conceptual level
- Research-style project management (scope freeze, decision logs)
- Academic report structure (introduction, evaluation, limitations)

_No blockchain programming or security exploit knowledge required._

### Milestone Deliverables

**Milestone 1**
- Project scope definition and exclusions
- Decision log (design trade-offs and rationale)
- Milestone schedule and risk register

**Milestone 2**
- Updated decision log reflecting changes or removals
- Cross-role integration notes
- Draft outline of final report sections

**Milestone 3**
- Final report and slides (primary editor)
- Contribution mapping (who did what and where it appears)

### Estimated Workload
- Medium–High, distributed across the project
- Higher intensity near Milestone 3 and final submission

---

## Role B — Architecture / Spec Owner

### Role Summary
Maintains the **authoritative system specification**. Responsible for correctness, clarity, and traceability from threat model to tests and measurements.

### Learning Requirements
- Specification-driven development concepts
- Writing assumptions, invariants, and acceptance criteria
- Given/When/Then (GWT) formulation
- Measurement protocol design

_No implementation or exploit coding required._

### Milestone Deliverables

**Milestone 1**
- Threat model v1 (assets, adversaries, attack surface)
- 10–15 specs with ID system (S-01 to S-15)
- Threat→Spec mapping table
- GWT acceptance criteria
- Measurement protocol draft

**Milestone 2**
- Updated spec (v1) reflecting observed issues
- Mapping from threats to test cases

**Milestone 3**
- Finalized spec for inclusion in report appendix
- Traceability table (spec → test → metric)

### Estimated Workload
- High in Milestone 1
- Medium thereafter (maintenance and clarification)

---

## Role C — Implementation #1: Agent Backend Owner

### Role Summary
Implements the **LLM-driven transaction planning logic**. Focuses on API structure and data flow, not security enforcement or optimization.

### Learning Requirements
- API design and JSON schema validation
- Basic LLM invocation and output handling
- Mocked tool integration

_No deep DeFi, blockchain, or security knowledge required._

### Milestone Deliverables

**Milestone 1**
- Agent API skeleton
- Planner logic producing dummy unsigned TxPlans

**Milestone 2**
- Integration with market snapshot / quote tools
- Structured TxPlan outputs

**Milestone 3**
- Stable backend used in end-to-end tests
- Documentation of agent interfaces

### Estimated Workload
- Medium and steady across milestones
- Low risk of overload if scope remains minimal

---

## Role D — Implementation #2: Guardrails / Contract Owner (Critical Role)

### Role Summary
Builds the **L1 and L2 guardrail enforcement system**. L1 provides pre-LLM input sanitization, max-risk filters, untrusted context segregation, and post-LLM output checks (structured output validation, refusal enforcement). L2 provides deterministic policy enforcement: allowlisted routers, slippage ≤ 10%, approval constraints (no unlimited approve), value ≤ daily cap. L3 (on-chain smart contract restrictions) is **optional and deprioritized** per specification.md.

### Learning Requirements
- L1 guardrail patterns (input sanitization, output validation)
- L2 deterministic policy enforcement concepts
- Gas and latency profiling
- Smart contract / Solidity (optional, only if L3 is pursued)

_L1 + L2 are the must-have layers (rule engine / middleware). L3 is optional._

### Milestone Deliverables

**Milestone 1**
- L1 guardrail rule engine framework
- L2 policy engine skeleton (not necessarily on-chain contract)
- ≥3 negative tests (violations must be blocked)

**Milestone 2**
- Complete L1 rule engine (all specs enforced)
- L2 with full enforcement (cap/allowlist/replay)
- Gas measurement comparison (Config0 vs Config2)
- Integration with Role C's agent backend

**Milestone 3**
- Production-ready guardrail code (commented)
- Final gas/latency measurements
- Security analysis writeup for report

### Estimated Workload
- High, especially in Milestones 1 and 2
- Central to project success and research credibility

---

## Role E — Red Team / Measurement

### Role Summary
Designs, generates, and executes the **100-case adversarial test suite** (4 categories × 25). Builds the **evaluation harness** that computes ASR, TR, and FP across three defense configurations (Config0: bare LLM, Config1: +L1, Config2: +L1+L2). Owns all experiment artifacts and reproducibility.

### Learning Requirements
- Prompt injection patterns (direct, indirect/encoded)
- Tool-poisoning and memory-poisoning concepts
- Python testing frameworks (e.g., pytest)
- Experiment harness design
- ASR, TR, FP metric computation
- Basic CI configuration (e.g., GitHub Actions)
- Statistical analysis

_No blockchain programming required._

### Milestone Deliverables

**Milestone 1**
- Attack sample generator v0
- Attack taxonomy (4 categories: direct injection, indirect/encoded injection, tool-poisoning, memory-poisoning)
- ≥10 labeled samples per category (≥40 total)
- Experiment harness skeleton
- Smoke test against bare LLM

**Milestone 2**
- Expanded to 25 samples per category (100 total)
- Full harness with automated metric computation
- Three-config comparison results
- results.csv with ASR/FRR/gas/latency
- Failure case analysis

**Milestone 3**
- Final versioned attack dataset
- Complete results with statistical analysis
- Figures/tables for report
- One-command reproduction script
- Final threat model and attack taxonomy writeup

### Estimated Workload
- High, especially in Milestones 1 and 2
- Owns harness and measurement pipeline
- Central to project success and research credibility

---

## Workload Balance Summary

| Role | Relative Workload | Risk Level |
|------|------------------|------------|
| A — PM | Medium–High | Coordination fatigue |
| B — Spec | Medium | Abstract reasoning errors |
| C — Agent | Medium | Scope creep |
| D — Guardrails | High | Technical complexity |
| E — Red Team | High | Test quality variance |

