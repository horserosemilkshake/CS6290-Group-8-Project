# Role E Reproducibility Guide

This directory contains the Milestone 3 Role E automation for reproducing the final dataset bundle, benchmark summaries, figures, and threat-model writeup.

## Exact command

```bash
python scripts/run_integration_test.py
```

## What the command does

The default command is fully offline and deterministic. It:

1. freezes the final versioned attack dataset at `testcases/final_attack_dataset_v1.json`
2. loads the canonical benchmark reports for `bare`, `l1`, and `l1l2`
3. writes final result bundles to `artifacts/final_results/`
4. computes statistics and validation checks
5. exports report-ready figures and a LaTeX table to `report-latex/figures/`
6. writes the final Role E threat-model summary to `docs/threat-model/final_threat_model.md`

## Optional live mode

If the FastAPI agent is already running locally, you can regenerate the benchmark reports from the live service:

```bash
python scripts/run_integration_test.py --mode live
```

By default, live mode expects the service at `http://127.0.0.1:8000`.
