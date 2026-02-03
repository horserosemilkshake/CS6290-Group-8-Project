# Development & Testing Task List (35 Tasks)
Based on the specification for the *Adversarially‑Robust Minimal DeFi Agent*.

## A. Foundations & Project Setup
1. [ ] Create repository structure, environments, and CI with unit‑test gating. 
2. [ ] Add immutable system prompt file and enforce hash‑change checks. 
3. [ ] Implement least‑privilege runtime configuration and permissions audit. 

## B. L1 Guardrails (Pre‑LLM / Post‑LLM)
4. [ ] Implement pre‑LLM input sanitizer (size limits, markup removal, tagging untrusted content). 
5. [ ] Develop prompt‑injection detector for direct/encoded patterns. 
6. [ ] Implement post‑LLM JSON structure validator for TxPlan output. 
7. [ ] Block all broadcast‑capable tools globally and confirm they are unreachable. 

## C. Quote Tooling & Market Snapshot
8. [ ] Implement quote‑fetch tool for allowlisted DEX providers. 
9. [ ] Implement market snapshot tool with freshness and latency limits. 
10. [ ] Add tool audit logging (endpoint, latency, allowlist decision). 

## D. L2 Deterministic Policy Engine
11. [ ] Create policy schema (router allowlist, slippage ≤10%, no unlimited approvals, value caps). 
12. [ ] Implement deterministic policy evaluator with reproducible outputs. 
13. [ ] Establish full reason‑code catalog and unit‑test coverage for each. 
14. [ ] Add LLM‑override prevention test for blocked quotes. 

## E. TxPlan Generation (Unsigned Only)
15. [ ] Implement TxPlan composer with redacted calldata preview. 
16. [ ] Implement HITL pause logic at signer boundary. 
17. [ ] Add expiry enforcement for quotes and plans. 

## F. Wallet Bridge (Owner Signing Only)
18. [ ] Implement unsigned plan forwarding to wallet bridge. 
19. [ ] Ensure agent never receives signatures — only owner‑side state updates. 
20. [ ] Add chain‑ID mismatch detection and error handling. 

## G. Privacy & Artifact Handling
21. [ ] Enforce “no public TX hash” at all output surfaces. 
22. [ ] Implement artifact de‑identification (addresses, nonce, raw calldata). 
23. [ ] Store artifacts in private storage with retention policy. 

## H. Performance Requirements
24. [ ] Benchmark agent response time (p95 < 3s). 
25. [ ] Benchmark tools quote latency (p95 < 2s). 

## I. Security & Red‑Team Harness
26. [ ] Build deterministic 100‑case red‑team suite. 
27. [ ] Run ASR baseline (bare LLM) and document <20% target. 
28. [ ] Measure ASR post‑L1/L2 and confirm <5%. 
29. [ ] Validate TR < 6 seconds under malicious cases. 
30. [ ] Validate FP = 0% on legit user requests. 

## J. User Flow End‑to‑End Tests
31. [ ] E2E test: real user “Swap 1 ETH to USDT on Ethereum” path produces valid TxPlan. 
32. [ ] E2E test: malicious user prompt causes safe refusal and spotlighted logging. 

## K. Errors & Observability
33. [ ] Implement deterministic error model (`POLICY_BLOCKED`, `QUOTE_EXPIRED`, etc.). 
34. [ ] Add structured logs (run_id, decisions, reason codes) for every plan. 

## L. Finalization & Documentation
35. [ ] Deploy MVP on Ethereum and update documentation (API, data model, 100‑case harness). 
