# CS6290 — Individual Evidence Pack

> **Course:** CS6290 Privacy-Enhancing Technologies  
> **Submission type:** Individual (MANDATORY for each milestone)  
> **Length:** 1 page recommended (max 2 pages)  
> **Format:** PDF (export from Markdown is acceptable)

---

## Student Information

- **Name:** Biying FANG
- **Student ID (SID):** (填写)
- **Group Number / Project Title:** Group 8 — Adversarially-Robust DeFi Swap Agent
- **Milestone:** ☐ M1 ☑ M2 ☐ M3
- **Date:** 8 Mar, 2026

---

## 1) What I Contributed (2–5 bullets)

- **Built the L2 Policy Engine** (`policy_engine/`): Designed and implemented 7 deterministic, LLM-non-overridable rules — R-01 Token allowlist, R-02 Router allowlist, R-03 Slippage limit, R-04 Value cap, R-05 No unlimited ERC-20 approvals, R-07 TxPlan structure validation, R-17 Network scope enforcement — with fail-safe design (any rule exception → auto-BLOCK). Replaced the previous mock stub in the agent pipeline with the real engine. Wrote 53 unit tests covering positive, negative, and edge cases for every rule.

- **Implemented the Telegram Bot front-end** (`telegram_bot/`): A standalone proxy process that receives user messages from Telegram, calls the existing Agent API (`POST /v0/agent/plan`), and returns formatted results. Supports both group chat (adversarial "arena" per spec) and private chat, with owner identity tagging (`OWNER_TELEGRAM_ID`), group-chat privacy protection (ALLOW TxPlans sent via DM only), and `/start` `/status` `/help` commands. 13 unit tests.

- **Ran three-config red-team evaluation** (Config0: bare / Config1: L1 / Config2: L1+L2): Added runtime defense-config switching via `GET/POST /v0/defense-config` endpoint (no server restart needed), and `--all-configs` CLI flag for automated sequential runs. Produced reproducible artifacts (fixed seed 6290, git commit hash, suite SHA-256). **Final result with live DeepSeek LLM (2026-03-08, git `d963d5c`): ASR 75% → 25% → 14%, FP = 0% across all configs.**

- **Fixed critical correctness bugs affecting metric accuracy**: (a) Harness `_STATUS_MAP` expanded from 3 to 8 entries — `INPUT_REJECTED`/`OUTPUT_VALIDATION_FAILED` were incorrectly mapped to ERROR instead of REFUSE, directly inflating ASR; (b) R-04 value cap used hardcoded 18-decimal for all tokens, making the cap ineffective for USDC/USDT (6-decimal); (c) DAI decimal error in mock parser (`6` → `18`); (d) `_format_amount` hardcoded `10**18` division; (e) `sanitize_input` regex stripped DeFi-relevant characters (`-`, `:`, `/`, `@`).

---

## 2) Evidence (at least 2 items)

| # | Evidence type | Link / Reference | What this shows |
|---|---------------|------------------|-----------------|
| 1 | PR (L2 engine) | [PR #5](https://github.com/horserosemilkshake/CS6290-Group-8-Project/pull/5) | L2 policy engine implementation merged into main |
| 2 | Commit (L2 impl) | [`4b25390`](https://github.com/horserosemilkshake/CS6290-Group-8-Project/commit/4b25390) — feat(L2): implement deterministic policy engine and replace mock | 8 files, +569/−304: `policy_engine/` (rules.py, engine.py, config.py, \_\_init\_\_.py), 254-line test suite, agent integration in l1\_agent.py |
| 3 | Commit (Telegram Bot) | [`0dd9084`](https://github.com/horserosemilkshake/CS6290-Group-8-Project/commit/0dd9084) — add Telegram bot as Agent proxy with group/private chat | 13 files, +996/−97: `telegram_bot/` (bot.py, formatter.py, config.py, main.py), 200-line test file, defense-config API, harness expansion |
| 4 | Commit (R-05/R-07/R-17 + bug fixes) | [`ab10ba7`](https://github.com/horserosemilkshake/CS6290-Group-8-Project/commit/ab10ba7) | 13 files, +452/−20: 3 new L2 rules, STATUS\_MAP fix (3→8), R-04 decimal fix, DAI fix, sanitize\_input fix, `.env.example`, +242 test lines |
| 5 | Artifact files (committed) | [`artifacts/three_config_comparison_adv_100_cases.json`](../artifacts/three_config_comparison_adv_100_cases.json), [`results_bare_adv_100_cases.json`](../artifacts/results_bare_adv_100_cases.json), [`results_l1_adv_100_cases.json`](../artifacts/results_l1_adv_100_cases.json), [`results_l1l2_adv_100_cases.json`](../artifacts/results_l1l2_adv_100_cases.json) | 3-config ASR comparison with live DeepSeek LLM (git `d963d5c`): bare 75% → l1 25% → l1l2 14%, FP = 0% |
| 6 | Test suite (66 tests) | `tests/test_policy_engine.py` (53 tests), `tests/test_telegram_bot.py` (13 tests) | Per-rule unit tests, engine integration, STATUS\_MAP, audit context, bot config/formatter/identity |

---

## 3) Validation Performed (at least 1 item)

- **What did you check or test?** All 7 L2 rules with positive, negative, and edge cases; engine orchestration (multi-violation aggregation, fail-safe exception handling); Telegram bot (config loading, message formatting across 4 response types, API mock, owner identity logic); end-to-end 100-case red-team suite across 3 defense configs with live LLM; experiment reproducibility via replay script.

- **How did you do it?** Ran `python -m pytest tests/ -v` after every change (66 passed, zero regression). Ran `python scripts/run_integration_test.py adv_100_cases.json --all-configs` with live DeepSeek API to produce Config0/1/2 results (final run: 2026-03-08, git `d963d5c`). Ran `python scripts/replay_integration_test.py` to re-execute against baseline artifacts and automatically compare seed, suite SHA-256, case ordering, ASR, and FP for consistency.

- **What was the result?** 66/66 unit tests passed. ASR monotonically decreased: bare 75% → L1 25% → L1+L2 14%, FP = 0%. The 6-case milestone1 suite achieved 6/6 expected==observed (ASR = 0%, FP = 0%). Replay script confirmed deterministic reproducibility (seed, suite hash, case order, metrics all matched baseline). All 4 artifact JSON files committed to repository for verification.

---

## 4) AI Usage Transparency (required)

- **AI tool(s) used:** Claude (Cursor Copilot), ChatGPT

- **One AI output I adopted:** Claude generated the initial skeleton for `policy_engine/rules.py` with the four core check functions and the `Violation` dataclass. I adopted this structure because the duck-typing approach (accepting `Any` for intent/tool\_response instead of importing `agent_client.src.models`) correctly preserved architectural separation between the L2 engine and Role C's agent code. I refined the slippage calculation and added the sanity-ceiling mechanism for mock data.

- **One AI output I rejected (and why):** Claude generated `sanitize_input()` with regex `[^\w\s\.\,\!\?]` that stripped hyphens, colons, slashes, and `@` — characters routinely found in DeFi token pairs (e.g. "WETH-USDC"), contract addresses, and URL-style parameters. This would silently corrupt legitimate user inputs before they reach the LLM, causing false refusals. I rejected this and expanded the allowed character set to preserve DeFi-relevant syntax.

---

## 5) Reflection / Risk / Next Step (short)

**Limitation:** The remaining 14% ASR (Config2) is largely caused by the mock Tool Coordinator returning hardcoded valid quotes regardless of malicious user parameters (e.g. 50% slippage, fake chain IDs). L2 rules are correct but cannot detect attacks invisible at the quote level. Additionally, `_STATUS_MAP` was originally missing 5 agent response codes, which means earlier experiment runs before commit `ab10ba7` had inflated ASR numbers — a reminder that metric infrastructure bugs can silently distort security evaluation.

**Next step (M3):** Implement L3 on-chain enforcement via a Solidity guard contract on a local Anvil fork, aligning rules with L2 (allowlist, cap, slippage) so that even a compromised off-chain agent cannot execute a violating transaction. Produce gas measurement comparison (Config0 vs Config2/Config3) as required by the v2 deliverables.
