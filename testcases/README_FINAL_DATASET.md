# Final Attack Dataset

The final Role E benchmark dataset is stored at:

- `testcases/final_attack_dataset.json`

## Dataset structure

The file is a JSON list. Each case contains:

- `case_id`: stable case identifier
- `category`: high-level label (`adversarial` or `benign`)
- `attack_vector`: normalized taxonomy label
- `input`: user-facing prompt
- `expected`: expected safe outcome (`REFUSE`, `BLOCK`, or `ALLOW`)
- `description`: short human-readable explanation

## Final dataset composition

The final dataset contains 125 cases:

- 100 adversarial cases split evenly across four categories
- 25 benign swap requests used for false-positive measurement

The four adversarial categories are:

- `direct_injection`
- `indirect_or_encoded`
- `tool_poisoning`
- `memory_poisoning`

Each adversarial category contains 25 cases.

## Generation process

- Final frozen dataset file: `testcases/final_attack_dataset.json`
- Freeze / normalization step: `python scripts/run_integration_test.py`
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
