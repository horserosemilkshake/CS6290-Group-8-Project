"""
Models Package - Core data entities

Defines immutable data entities for the swap planning agent:
- SwapQuote: Published swap offer
- ValidationGate: Deterministic security policy
- TransactionPlan: Unsigned custody-safe plan with TransactionStep
- CustodyProof: Cryptographic proof of user control
- AdversarialThreat: Detected threat pattern
"""

from src.models.swap_quote import SwapQuote
from src.models.validation_gate import ValidationGate
from src.models.transaction_plan import TransactionPlan, TransactionStep
from src.models.custody_proof import CustodyProof
from src.models.adversarial_threat import AdversarialThreat

__all__ = [
    "SwapQuote",
    "ValidationGate",
    "TransactionPlan",
    "TransactionStep",
    "CustodyProof",
    "AdversarialThreat",
]
