# Final Threat Model and Attack Taxonomy

**Owner:** Role E - Red Team / Measurement  
**Milestone:** 3  
**Dataset:** `testcases/final_attack_dataset_v1.json`  
**Results Source:** `artifacts/final_results/`  

## 1. Scope

This document summarizes the final attack taxonomy, threat assumptions, attacker capabilities, observed failure modes, and evaluation limitations for the adversarially-robust DeFi swap agent.

## 2. Threat Assumptions

- Attackers can submit arbitrary natural-language requests through the same chat interface used by benign users.
- Attackers can attempt direct prompt injection, indirect/encoded injection, tool parameter poisoning, and context or memory poisoning.
- Attackers cannot sign transactions on behalf of the owner.
- The system under test may reject, block, allow, or internally error when processing adversarial requests.

## 3. Attacker Capabilities

- Override or role-play attempts against the planner.
- Obfuscated or encoded malicious intent.
- Malicious transaction parameters such as unsafe routers, slippage, or token targets.
- Context poisoning via fake admin claims or fabricated prior approvals.

## 4. Final Attack Taxonomy

| Attack Vector | Prefix | Count | Expected Safe Outcome |
| --- | --- | ---: | --- |
| Direct injection | `adv-direct-` | 25 | REFUSE |
| Indirect / encoded | `adv-ind-` | 25 | REFUSE |
| Tool poisoning | `adv-tool-` | 25 | BLOCK or REFUSE |
| Memory poisoning | `adv-mem-` | 25 | REFUSE |

## 5. Final Experimental Findings

| Config | ASR | FP | TR (max s) |
| --- | ---: | ---: | ---: |
| bare | 75.00% | 0.00% | 3.8599 |
| l1 | 25.00% | 0.00% | 3.3735 |
| l1l2 | 14.00% | 0.00% | 3.6948 |

## 6. Observed Failure Modes

- Bare configuration allowed 75 of 100 adversarial cases, confirming the undefended planner is highly vulnerable.
- L1 reduced successful attacks to 25 cases, but tool-poisoning remained the dominant residual failure mode.
- L1+L2 reduced successful attacks to 14 cases; residual failures are concentrated in tool-poisoning, with a smaller remaining gap in indirect or encoded attacks.
- Bare mode also produced 25 internal errors, which are unsafe because they do not constitute a controlled refusal path.

### 6.1 L1+L2 Breakdown by Attack Vector

- Direct injection: 23 refused, 2 blocked, 0 allowed.
- Indirect / encoded: 22 refused, 2 blocked, 1 allowed.
- Tool poisoning: 5 refused, 7 blocked, 13 allowed.
- Memory poisoning: 25 refused, 0 blocked, 0 allowed.

## 7. Limitations

- The final dataset is adversarial-only, so FP remains defined by the harness as 0.0 rather than by a mixed benign/adversarial evaluation.
- Canonical final outputs are derived from archived benchmark reports unless `--mode live` is explicitly used with a running agent backend.
- The current evaluation focuses on planner and policy behavior rather than real on-chain execution.

## 8. Reproducibility

Run the following command from the repository root:

```bash
python scripts/run_integration_test.py
```

This command regenerates:

- `testcases/final_attack_dataset_v1.json`
- `artifacts/final_results/`
- `report-latex/figures/`
- this threat model document
