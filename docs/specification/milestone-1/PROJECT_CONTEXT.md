## Background

Decentralized Finance (DeFi) user interfaces are undergoing a structural shift.
Instead of manually constructing and signing transactions, users increasingly interact with chat-based or AI-assisted agents that translate natural-language instructions into on-chain actions. Examples include wallet copilots, Telegram trading bots, and conversational DeFi assistants.

This shift introduces a new and under-explored attack surface:
the language-mediated transaction planning layer that sits before signing and broadcasting. Unlike smart contracts, which are deterministic and formally analyzable, large language models (LLMs) operate probabilistically and are known to be vulnerable to prompt injection, social engineering, and context poisoning—especially in open communication environments such as Telegram or WhatsApp.

In such environments, an adversary can directly interact with the same agent as the legitimate owner, embedding malicious instructions, indirect prompts, or encoded payloads that attempt to influence transaction generation. Because blockchain transactions are irreversible, even a single unsafe plan can result in permanent loss.

Despite extensive research on smart-contract vulnerabilities, MEV, oracle manipulation, and key custody, there is limited empirical work on the security of LLM-driven DeFi transaction planning under adversarial language inputs.

## Problem Statement

This project studies the following core question:

> Can an LLM-driven DeFi transaction planning agent remain safe, privacy-preserving, and custody-preserving when exposed to adversarial natural-language inputs in an open communication environment?

Specifically, we focus on the pre-execution stage of DeFi interactions, where an agent converts user intent into a structured transaction plan. This stage is critical because it defines what would be executed if approved, yet it is often implicitly trusted.

The key risks addressed in this project include:
- Unsafe or policy-violating transaction plans caused by prompt injection or social engineering
- Leakage of sensitive user information (wallet address, balances, intent, or transaction metadata)
- Over-reliance on LLM outputs without deterministic enforcement
- Lack of measurable, reproducible security evaluation for such agents

## Scope and Non-Goals

### In Scope

- A minimal DeFi transaction planning agent that converts natural-language requests into unsigned transaction plans (TxPlans)
- Layered guardrails:
  - L1: pre- and post-LLM language-level defenses
  - L2: deterministic policy enforcement (allowlists, caps, invariants)

- A reproducible evaluation harness for adversarial testing
- Empirical measurement of:
  - Attack Success Rate (ASR)
  - Time to Refusal (TR)
  - False Positive rate (FP)
- Ethereum as the sole supported chain (for simplicity and reproducibility)

### Explicit Non-Goals

- No private-key custody or signing
- No transaction broadcasting or execution
- No market-making, routing optimization, or price discovery research
- No multi-chain or production-grade wallet integration

The system intentionally stops at the signer boundary, ensuring that the owner retains full control over execution.

## System Overview

The system operates in a one-owner-one-agent model within an adversarial open messaging environment.

High-level flow:

1. A user (owner or adversary) sends a natural-language message to the agent.

2. L1 guardrails sanitize and tag untrusted input before LLM reasoning.

3. The agent generates a candidate unsigned TxPlan.

4. L2 deterministic policy enforcement validates the plan against strict rules:
- allowlisted routers
- slippage limits
- approval constraints
- value caps

5. If any rule is violated, the plan is blocked with a non-overridable reason.

6. If valid, the TxPlan is forwarded to the owner’s wallet for optional approval—without signing or broadcasting by the agent.

All artifacts are logged in a privacy-preserving, de-identified manner.

## Research Goals

The project aims to deliver empirical evidence, not a production trading system.

Our primary goals are:

- Adversarial robustness: demonstrate that unsafe transaction plans can be reliably prevented under malicious inputs
- Deterministic enforcement: ensure LLM outputs cannot override policy decisions
- Privacy preservation: prevent disclosure of wallet identity, balances, or transaction metadata
- Measurability: provide reproducible metrics across multiple defense configurations
- Trade-off analysis: quantify security improvements versus latency and false positives

## Project Deliverables

The project delivers the following research artifacts:

1. A minimal, custody-preserving DeFi transaction planning agent

2. A specification-driven policy framework with explicit assumptions, invariants, and acceptance criteria

3. A deterministic red-team evaluation harness with a 100-case adversarial test suite

4. Empirical results comparing:
- bare LLM
- LLM + L1 guardrails
- LLM + L1 + L2 guardrails

5. A final report and presentation that document system design, threat modeling, experimental results, and limitations
