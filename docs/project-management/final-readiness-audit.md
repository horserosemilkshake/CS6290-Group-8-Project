# Final Readiness Audit

This document checks the current project against `docs/specification/` and highlights what is already good enough for final delivery, what was repaired in this pass, and what still deserves attention for report, presentation, and demo quality.

## Repaired In This Pass

| Area | Spec / Need | Change |
| --- | --- | --- |
| Real external tool integration | S-02, S-03, demo credibility | Updated real-tool path to support current 1inch base URL configuration, API-key headers, and strict fail-closed mode |
| Tool provenance | S-02, S-13, observability | Added `tool_audit` metadata to `TxPlan` so output now records quote/snapshot source, endpoint, latency, and fallback reason |
| Silent fallback risk | Demo credibility | Added `REAL_TOOLS_STRICT=true` support so live demos fail instead of silently degrading to mock |
| Health / demo inspectability | Presentation / demo | `/v0/health` now exposes defense config and tool runtime status |
| FP auxiliary statistics | Measurement correctness | Fixed `scripts/run_integration_test.py` helper FP calculation to count any benign non-`ALLOW` as false positive |
| Harness artifact accuracy | Report credibility | `SmokeHarness` notes now describe the actual client instead of always claiming placeholder mode |
| Operator entry points | Report / demo completeness | Refreshed `README.md` and added `scripts/run_real_tools_smoke.py` + `testcases/real_tools_smoke_cases.json` |
| TxPlan completeness | S-04, task 17 | `TxPlan` now includes `slippage_bounds` and `quote_validity`, and L2 enforces quote freshness metadata |
| L3 parity | Optional S-10 | `SwapGuard` and the Python L3 validator now mirror router, cap, and slippage enforcement |
| Wallet handoff | S-05, tasks 18-20 | Added an in-memory wallet bridge plus `/v0/wallet/handoffs/*` API routes so plans pause on explicit owner action |
| Live-tool benchmark path | Demo / integration rigor | Added `scripts/run_real_tools_benchmark.py` for guarded strict-mode live benchmarking without re-labeling it as canonical experimental data |

## Ready Enough For Final Report

| Item | Status | Notes |
| --- | --- | --- |
| Four-config comparison pipeline | Good | `scripts/run_integration_test.py --mode live` produces final results, figures, tables, and threat model |
| Versioned final dataset | Good | `testcases/final_attack_dataset_v2.json` plus final result artifacts are present |
| L3 local-chain demonstration | Good | Local `SwapGuard` deployment plus `eth_call` validation is wired |
| Report figure generation | Good | `report-latex/figures/` has current metrics and breakdown plots |
| Threat model export | Good | `docs/threat-model/final_threat_model.md` regenerates from pipeline |

## Highest-Priority Remaining Gaps

These are the items most worth fixing if time remains before final submission.

| Priority | Gap | Why It Matters |
| --- | --- | --- |
| High | ASR targets from spec are not met | Bare ASR is far above the original target, and tuned ASR is still above the post-tuning target |
| Medium | Sanitizer provenance is only partially logged | S-07 / S-09 ask for logging stripped or spotlighted untrusted content segments |
| Medium | Performance benchmarking is max-based, not p95-based | Tasks 24-25 ask for p95-style benchmarks |
| Medium | README / report text should avoid claiming old 3-config workflow | Final doc now points to 4-config pipeline, but paper/slides should stay aligned |
| Medium | No dedicated slide source exists in-repo yet | There is no `slides/` directory or deck source to version alongside the report |

## What Should Be Repaired Next

### For Report

1. Add a short subsection that clearly separates:
   - canonical reproducible benchmark (`REAL_TOOLS=false`)
   - external integration smoke / live demo (`REAL_TOOLS=true`)
2. Add a limitations paragraph for:
   - current ASR not meeting original target
   - wallet handoff is demo-oriented in-memory bridge, not production wallet SDK custody infrastructure
3. Ensure the paper references the current 125-case dataset, not the old 100-case-only wording.

### For Presentation And Demo

1. Keep the main metrics demo on deterministic mode.
2. Use `scripts/run_real_tools_smoke.py` as the live “real-world integration proof”.
3. Show `/v0/health` before the live smoke so the audience can see:
   - active defense config
   - `REAL_TOOLS=true`
   - strict mode enabled
4. Avoid relying on a full 125-case live real-tools run during presentation.

## Items That Are Fine To Leave As-Is If Time Is Short

- Full public-chain deployment beyond local Anvil
- Reworking the entire dataset to optimize L3 incremental gains
- Replacing the in-memory wallet bridge with a production wallet SDK bridge

Those would improve the system, but they are not the shortest path to a complete and defensible final submission.
