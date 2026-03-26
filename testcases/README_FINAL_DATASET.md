# Final Attack Dataset v1

The final Role E benchmark dataset is stored at:

- `testcases/final_attack_dataset_v1.json`

## Dataset structure

The file is a JSON list. Each case contains:

- `case_id`: stable case identifier
- `category`: high-level label (`adversarial`)
- `attack_vector`: normalized taxonomy label
- `input`: user-facing attack prompt
- `expected`: expected safe outcome (`REFUSE`, `BLOCK`, or `ALLOW`)
- `description`: short human-readable explanation

## Attack categories

The final dataset contains 100 adversarial cases split evenly across four categories:

- `direct_injection`
- `indirect_or_encoded`
- `tool_poisoning`
- `memory_poisoning`

Each category contains 25 cases.

## Generation process

- Source dataset: `testcases/adv_100_cases.json`
- Finalization step: `python scripts/run_integration_test.py`
- Normalization performed during finalization:
  - stable sort by `case_id`
  - normalized `attack_vector`
  - stripped text fields
  - deterministic JSON formatting

## Intended use

This dataset is the frozen Milestone 3 benchmark used to generate:

- `artifacts/final_results/`
- `report-latex/figures/`
- `docs/threat-model/final_threat_model.md`
