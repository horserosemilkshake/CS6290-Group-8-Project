"""
Swap Planning Agent - Main Package

This package implements a deterministic LLM agent for generating secure,
privacy-preserving cryptocurrency swap transaction plans with layered
security guardrails.

Module Organization:
- models: Data entities (SwapQuote, TransactionPlan, etc.)
- validation: Security gates and threat filtering
- agent: Core LLM agent and planning logic
- logging: Structured audit logging
- market: Market data and blockchain integration
- routing: Privacy routing strategy selection
"""

__version__ = "0.1.0"
__author__ = "Exchange Security Team"

# Core imports
from src.models.swap_quote import SwapQuote
from src.models.transaction_plan import TransactionPlan
from src.models.adversarial_threat import AdversarialThreat
from src.models.custody_proof import CustodyProof
from src.models.validation_gate import ValidationGate

__all__ = [
    "SwapQuote",
    "TransactionPlan",
    "AdversarialThreat",
    "CustodyProof",
    "ValidationGate",
]
