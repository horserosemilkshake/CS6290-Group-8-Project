## Milestone Timeline & Deliverables

**Project Duration**: 10 weeks (Jan 26 - Apr 19, 2026)  
**Course Deadline Structure**: Individual Evidence Packs + Final Team Deliverables

---

### Milestone 1: MVP Closed Loop
**Evidence Pack Deadline**: **February 13, 2026 (11:59 PM)**  
**Objective**: Demonstrate end-to-end system works with minimal functionality

#### Individual Deliverables by Role

| Role | Deliverables | Evidence Items (≥2 required) | Validation (≥1 required) |
|------|--------------|------------------------------|--------------------------|
| **A - PM/Lead** | • SCOPE.md finalized<br>• Decision log v1.0<br>• interfaces.md (API contracts)<br>• Milestone schedule | • Git commits to SCOPE.md, DECISIONS.md<br>• Meeting notes from scope freeze discussion<br>• Interface schema definitions | • Verify all team members can access and understand scope document<br>• Test that interface definitions are unambiguous |
| **B - Spec Owner** | • v0 system specification (interfaces, assumptions, invariants)<br>• Given/When/Then acceptance criteria<br>• Measurement protocol draft | • specs/ directory with .feature files<br>• specification.md update logs<br>• measurement_protocol.md draft | • Coverage check: core assumptions map to testable criteria<br>• Peer review: verify 3 acceptance criteria are testable |
| **C - Agent Owner** | • Agent pipeline skeleton<br>• Standardized tx_candidate.json output<br>• Demo: natural language → TxPlan | • Source code PR for agent module<br>• Example transaction logs (valid swap)<br>• CLI command execution screenshot | • Unit tests: valid input produces expected JSON schema<br>• Integration test: run full pipeline on 1 benign case |
| **D - Harness/Artifacts Owner** | • Smoke test harness<br>• Artifact schema definition (input/output/log format)<br>• Basic CI pipeline execution | • experiments/ scaffold with runnable smoke tests<br>• artifact_schema.json (or equivalent schema doc)<br>• CI run logs/screenshots | • Smoke test reproducibility: same seed gives same output<br>• CI sanity check: pipeline runs on clean checkout |
| **E - Security/Verification Owner** | • Threat model v1 (assets, adversaries, attack surface)<br>• Initial labeled test cases (benign + adversarial)<br>• Attack taxonomy v1 | • threat_model.md with complete table<br>• attacks/ directory with labeled starter set<br>• Labeling rubric / annotation guideline | • Manual review: validate labels and expected outcomes are consistent<br>• Cross-check with B: threats map to testable spec statements |

**Team Sync Meeting**: February 9, 2026 (8:00 PM) - Pre-submission integration check

---

### Milestone 2: Non-Trivial Risk Closed Loop
**Evidence Pack Deadline**: **March 8, 2026 (11:59 PM)**  
**Objective**: Demonstrate allowance abuse risk is addressed with measurable improvements

#### Individual Deliverables by Role

| Role | Deliverables | Evidence Items (≥2 required) | Validation (≥1 required) |
|------|--------------|------------------------------|--------------------------|
| **A - PM/Lead** | • Decision log v2.0 (updated with M1 learnings)<br>• Draft report outline with section assignments<br>• First-pass results visualization (graphs) | • Updated DECISIONS.md with rationale for changes<br>• Report structure in report/ directory<br>• Python scripts for generating ASR/FRR plots | • Reproduce peer's experiment (E) and verify trend<br>• Cross-check that results match spec expectations |
| **B - Spec Owner** | • Spec refinement (all specs have tests)<br>• Threat→Spec→Test complete mapping<br>• Coverage report | • Updated specs/ with test file references<br>• Automated coverage script output<br>• Decision log for spec changes | • Verify E's attack samples map to threat model<br>• Run coverage script: confirm ≥90% spec coverage |
| **C - Agent Owner** | • Agent with Config0/1/2 switching<br>• Explanation outputs (spec_id when rejected)<br>• Integration with guardrails | • PR showing config parameter handling<br>• Logs demonstrating different behaviors per config<br>• Transaction rejection reasons with spec IDs | • Run same attack batch through Config0 vs Config2<br>• Verify ASR difference is measurable (>20%) |
| **D - Harness/Artifacts Owner** | • Full red-team test harness<br>• Metric computation scripts (ASR/FRR/latency/gas)<br>• Reproducible experiment runs across Config0/1/2 | • run_experiments.py complete version<br>• results.csv + aggregation scripts<br>• Timestamped outputs in results/ | • Reproducibility test: re-run with same seed on different machine<br>• Metric sanity check: script output matches manual sample calculation |
| **E - Security/Verification Owner** | • Expanded adversarial suite with expected outcomes<br>• Failure case analysis (root cause + severity)<br>• Threat-to-test coverage review | • attacks/ dataset with fixed seeds + labels<br>• failure_analysis.md with categorized failures<br>• coverage matrix (threat_id -> test_id) | • Cross-validate with B: threat→spec→test mapping remains complete<br>• Spot-check with D: failing cases are correctly represented in harness outputs |

**Team Sync Meeting**: March 2, 2026 (8:00 PM) - Results review and M3 planning

---

### Milestone 3: Final Integration & Polish
**Evidence Pack Deadline**: **March 29, 2026 (11:59 PM)**  
**Objective**: Complete system, reproducible experiments, report-ready

#### Individual Deliverables by Role

| Role | Deliverables | Evidence Items (≥2 required) | Validation (≥1 required) |
|------|--------------|------------------------------|--------------------------|
| **A - PM/Lead** | • Complete report draft (all sections)<br>• Contribution mapping document<br>• Reproducibility verification | • Final report PDF in report/<br>• CONTRIBUTORS.md with role→section mapping<br>• Clean environment test log | • Fresh VM: run `make reproduce` → verify all figures regenerate<br>• Peer review full report for consistency |
| **B - Spec Owner** | • Finalized spec appendix for report<br>• Traceability matrix (spec→test→metric→result)<br>• Peer review of threat model section | • Appendix A (all specs) in report<br>• Traceability table (CSV + formatted for report)<br>• Comments/suggestions on draft sections | • Audit: every spec referenced in report exists in specs/<br>• Cross-check metric definitions with E's implementation |
| **C - Agent Owner** | • Stable agent backend (no breaking changes)<br>• Documentation of all APIs<br>• Demo script for presentation | • Final agent code freeze tag<br>• API.md with endpoint documentation<br>• demo.sh script with annotated output | • End-to-end test: demo runs without errors<br>• Integration: verify D's harness consumes agent outputs correctly |
| **D - Harness/Artifacts Owner** | • One-command reproduction workflow (`make reproduce` equivalent)<br>• Final evaluation artifacts used in report<br>• CI-stable experiment pipeline | • Reproduction script + runbook notes<br>• Final results/ artifacts with metadata<br>• CI logs proving end-to-end run | • Fresh environment run regenerates key figures/tables<br>• Artifact integrity check (hashes + schema validation) |
| **E - Security/Verification Owner** | • Final threat model and attack taxonomy<br>• Security results summary for report<br>• Final verification notes on major failure modes | • threat_model_final.md + taxonomy appendix<br>• security_results_summary.md<br>• Versioned labeled test suite archive | • Security claims in report match measured failures/successes<br>• Cross-review with A/B for narrative consistency |

**Team Sync Meetings**: 
- March 23, 2026 (8:00 PM) - Report draft review
- March 28, 2026 (8:00 PM) - Final evidence pack check

---

### Final Deliverables (Team Submission)

#### Presentation Preparation
**Slides Deadline**: **April 11, 2026 (11:59 PM)**

**Responsibilities**:
- **A (Lead)**: Slide structure, introduction, demo coordination
- **B (Spec)**: Threat model + architecture slides
- **C (Agent)**: System design + agent demo walkthrough
- **D (Harness/Artifacts)**: Evaluation pipeline demo + trade-off graphs
- **E (Security/Verification)**: Threat model + attack taxonomy + security findings

**Deliverable**: Single PDF, 15-20 slides, uploaded to Canvas

---

#### Final Report Submission
**Report Deadline**: **April 19, 2026 (11:59 PM)**

**Responsibilities**:
- **A (Lead)**: Final editing, consistency check, submission
- **B (Spec)**: Appendices (specs, threat model, traceability)
- **C (Agent)**: System implementation section
- **D (Harness/Artifacts)**: Evaluation setup, reproducibility, and artifacts
- **E (Security/Verification)**: Security analysis, failure interpretation, and limitations

**Deliverable**: Single PDF, 10-14 pages + appendices, uploaded to Canvas

---

### Critical Dates Summary

| Date | Event | Action Required |
|------|-------|-----------------|
| **Feb 9** | M1 Pre-check | All members verify Evidence Pack draft ready |
| **Feb 13** | **M1 Deadline** | Individual Evidence Pack submission (11:59 PM) |
| **Mar 2** | M2 Pre-check | Results review meeting, M3 planning |
| **Mar 8** | **M2 Deadline** | Individual Evidence Pack submission (11:59 PM) |
| **Mar 23** | M3 Draft Review | Full report draft circulated for team feedback |
| **Mar 28** | M3 Pre-check | Final Evidence Pack verification |
| **Mar 29** | **M3 Deadline** | Individual Evidence Pack submission (11:59 PM) |
| **Apr 6** | Presentation Prep | Slides draft complete, rehearsal scheduled |
| **Apr 11** | **Slides Due** | Team presentation slides submission (11:59 PM) |
| **Apr 13-17** | Presentations | In-class presentations (exact date TBD) |
| **Apr 19** | **Report Due** | Final report submission (11:59 PM) |

---

### Evidence Pack Submission Checklist

**Every milestone, every member must include**:

✅ **Contributions** (2-5 bullets)
- Specific, verifiable deliverables
- No vague statements like "participated in discussions"

✅ **Evidence** (≥2 items)
- Git commit links
- Test output logs
- Screenshots
- Generated artifacts (CSVs, graphs, contracts)

✅ **Validation** (≥1 item)
- What did you test/verify?
- Whose work did you validate?
- What was the result?

✅ **AI Transparency**
- 1 example where you **adopted** AI output (what + why)
- 1 example where you **rejected** AI output (what + why)

**Submission Format**: PDF, filename: `M{X}_EvidencePack_{YourName}.pdf`
