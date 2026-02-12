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
| **B - Spec Owner** | • Threat model v1 (assets, adversaries, attack surface)<br>• 10-15 specs with ID system (S-01 to S-15)<br>• Threat→Spec mapping table | • specs/ directory with .feature files<br>• threat_model.md with complete table<br>• mapping.csv (threat_id → spec_id) | • Coverage check: every identified threat maps to ≥1 spec<br>• Peer review: verify 3 specs are testable |
| **C - Agent Owner** | • Agent pipeline skeleton<br>• Standardized tx_candidate.json output<br>• Demo: natural language → TxPlan | • Source code PR for agent module<br>• Example transaction logs (valid swap)<br>• CLI command execution screenshot | • Unit tests: valid input produces expected JSON schema<br>• Integration test: run full pipeline on 1 benign case |
| **D - Guardrails/Contract Owner** | • L1 guardrail rule engine framework<br>• L2 contract skeleton (deployment on local chain)<br>• ≥3 negative tests (violations must revert) | • Contract deployment logs (address + verification)<br>• Test output showing revert messages<br>• Foundry/Hardhat test files | • Property test: violating S-02 (allowance cap) reverts<br>• Gas baseline measurement script output |
| **E - Red Team/Measurement** | • Attack sample generator v0<br>• Attack taxonomy (5 categories)<br>• Experiment harness skeleton | • attacks/ directory with ≥10 samples per category<br>• run_experiments.py initial version<br>• Sample classification schema | • Manual review: validate 5 attack labels are correct<br>• Reproducibility: same seed produces same samples |

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
| **D - Guardrails/Contract Owner** | • Complete L1 rule engine (all specs enforced)<br>• L2 contract with enforcement (cap/allowlist/replay)<br>• Gas measurement comparison (Config0 vs Config2) | • Updated contract with enforcement logic<br>• Property tests (≥8 covering all key specs)<br>• gas_benchmark.csv with measurements | • Each spec violation in test suite reverts with correct reason<br>• Gas overhead documented (mean + percentiles) |
| **E - Red Team/Measurement** | • Expanded attack dataset (20-50 per category)<br>• Three-config comparison results<br>• results.csv with ASR/FRR/gas/latency | • attacks/ dataset with fixed seeds + hashes<br>• run_experiments.py complete version<br>• results/ directory with timestamped outputs | • Reproducibility test: re-run with same seed on different machine<br>• Cross-validate: B reviews attack→threat mapping |

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
| **C - Agent Owner** | • Stable agent backend (no breaking changes)<br>• Documentation of all APIs<br>• Demo script for presentation | • Final agent code freeze tag<br>• API.md with endpoint documentation<br>• demo.sh script with annotated output | • End-to-end test: demo runs without errors<br>• Integration: verify D's contract calls work correctly |
| **D - Guardrails/Contract Owner** | • Production-ready contracts (commented)<br>• Final gas/latency measurements<br>• Security analysis writeup for report | • Contract source with NatSpec comments<br>• Final gas_analysis.md<br>• Contract deployment guide | • All property tests pass in CI<br>• Security section draft reviewed by E |
| **E - Red Team/Measurement** | • Final attack dataset (versioned + archived)<br>• Complete results with statistical analysis<br>• Figures/tables for report (camera-ready) | • attacks_v1.0.tar.gz with SHA-256 hash<br>• Final results/ with analysis notebook<br>• All PNG/PDF figures for report | • Results match report claims (spot-check 3 tables)<br>• Statistical validity check (sample sizes, variance) |

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
- **D (Guardrails/Contract)**: Enforcement mechanism + trade-off graphs
- **E (Red Team)**: Attack taxonomy + experimental results

**Deliverable**: Single PDF, 15-20 slides, uploaded to Canvas

---

#### Final Report Submission
**Report Deadline**: **April 19, 2026 (11:59 PM)**

**Responsibilities**:
- **A (Lead)**: Final editing, consistency check, submission
- **B (Spec)**: Appendices (specs, threat model, traceability)
- **C (Agent)**: System implementation section
- **D (Guardrails/Contract)**: Enforcement design + evaluation setup
- **E (Red Team)**: Results, discussion, limitations

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
