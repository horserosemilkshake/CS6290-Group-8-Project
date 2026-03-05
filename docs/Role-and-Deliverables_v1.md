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
- v0 system specification (interfaces, assumptions, invariants)
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

## Role D — Implementation #2: Harness / Artifacts Owner (Critical Role)

### Role Summary
Builds the **testing and evaluation infrastructure**. Ensures experiments are reproducible, metrics are computed correctly, and results are automatable.

### Learning Requirements
- Python testing frameworks (e.g., pytest)
- Experiment artifact structuring (JSON logs)
- Security evaluation metrics (ASR, FP, TR)
- Basic CI configuration (e.g., GitHub Actions)

_No blockchain programming required._

### Milestone Deliverables

**Milestone 1**
- Smoke test harness
- Artifact schema definition
- Basic CI pipeline execution

**Milestone 2**
- Full red-team test harness
- Metric computation scripts
- Reproducible experiment runs

**Milestone 3**
- One-command reproduction scripts
- Final evaluation artifacts used in report

### Estimated Workload
- High, especially in Milestones 1 and 2
- Central to project success and research credibility

---

## Role E — Security & Verification

### Role Summary
Designs and labels **adversarial and benign test cases**. Provides threat modeling and interprets security failures.

### Learning Requirements
- Prompt injection and indirect attack patterns
- Adversarial testing concepts
- Writing structured test cases with expected outcomes

_No exploit development or blockchain internals required._

### Milestone Deliverables

**Milestone 1**
- Threat model v1
- Initial labeled test cases (benign and adversarial)

**Milestone 2**
- Expanded adversarial suite
- Failure case analysis

**Milestone 3**
- Final threat model and attack taxonomy
- Security results summary for report

### Estimated Workload
- Medium
- Conceptually challenging but implementation-light

---

## Workload Balance Summary

| Role | Relative Workload | Risk Level |
|------|------------------|------------|
| A — PM | Medium–High | Coordination fatigue |
| B — Spec | Medium | Abstract reasoning errors |
| C — Agent | Medium | Scope creep |
| D — Harness | High | Technical complexity |
| E — Security | Medium | Test quality variance |

