# Final Threat Model and Attack Taxonomy

**Owner:** Role E - Red Team / Measurement  
**Milestone:** 3  
**Dataset:** `testcases/final_attack_dataset_v2.json`  
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
| Benign (legitimate) | `benign-` | 25 | ALLOW |

## 5. Final Experimental Findings

| Config | ASR | FP | TR (max s) |
| --- | ---: | ---: | ---: |
| bare | 84.00% | 0.00% | 4.2929 |
| l1 | 25.00% | 0.00% | 3.1442 |
| l1l2 | 0.00% | 0.00% | 3.0779 |
| l1l2l3 | 0.00% | 0.00% | 2.9626 |

## 6. Observed Failure Modes

- Bare configuration allowed 109 of 125 cases, confirming the undefended planner is highly vulnerable.
- Bare mode also produced 16 internal errors.
- L1 reduced successful attacks to 50 cases.
- L1+L2 reduced successful attacks to 25 cases.
- L1+L2+L3 reduced successful attacks to 25 cases with on-chain enforcement providing an additional verification layer.

### 6.1 L1L2L3 Breakdown by Attack Vector

- Direct injection: 23 refused, 2 blocked, 0 allowed.
- Indirect / encoded: 23 refused, 2 blocked, 0 allowed.
- Tool poisoning: 5 refused, 20 blocked, 0 allowed.
- Memory poisoning: 24 refused, 1 blocked, 0 allowed.

## 7. Limitations

- The v2 dataset includes 25 benign cases alongside 100 adversarial cases, enabling meaningful FP evaluation.
- Canonical final outputs are derived from archived benchmark reports unless `--mode live` is explicitly used with a running agent backend.
- l1l2l3 config requires a running Anvil/Sepolia chain and is only available in `--mode live`.
- The current evaluation focuses on planner and policy behavior rather than real on-chain execution.

## 8. Reproducibility

Run the following command from the repository root:

```bash
# Offline (archived bare/l1/l1l2 only):
python scripts/run_integration_test.py

# Live (all 4 configs including l1l2l3, requires running Agent + Anvil):
python scripts/run_integration_test.py --mode live
```

This command regenerates:

- `testcases/final_attack_dataset_v2.json`
- `artifacts/final_results/`
- `report-latex/figures/`
- this threat model document
