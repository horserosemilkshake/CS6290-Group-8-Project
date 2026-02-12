"""
CustodyProof Model - Cryptographic evidence of user control

Represents different types of cryptographic proofs that demonstrate
the user maintains control throughout transaction execution.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, Literal
from uuid import uuid4


@dataclass(frozen=True)
class CustodyProof:
    """
    Represents cryptographic evidence that user maintains custody control
    throughout the swap execution.
    
    Proof Types:
    - balance_merkle: Merkle proof of user's token balance
    - commitment_preimage: Preimage of a cryptographic commitment
    - multisig_requirement: Multi-sig authorization requirement structure
    - zero_knowledge_proof: ZKP proving transaction correctness
    
    Properties:
    - IMMUTABLE (frozen dataclass)
    - REQUIRED: At least one proof must be in every TransactionPlan
    - VERIFIED: Must pass verification_method check
    - TEMPORAL: Has expiry (typically +24 hours from creation)
    
    Used in TransactionPlan to ensure:
    1. User retains cryptographic proof of fund control
    2. Agent didn't intercept or redirect funds
    3. Plan is reversible until user authorization
    """
    
    # Identification
    proof_id: str = field(default_factory=lambda: str(uuid4()), init=False)
    proof_type: Literal[
        "balance_merkle",
        "commitment_preimage",
        "multisig_requirement",
        "zero_knowledge_proof"
    ] = "balance_merkle"
    
    # Proof content - structure depends on proof_type
    proof_content: Dict[str, Any] = field(default_factory=dict)
    
    # Verification
    verification_method: str = ""  # How to verify (e.g., "merkle_verify()")
    verification_hash: str = ""    # SHA256 of proof_content for tampering detection
    
    # Timing
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat(), init=False)
    expiry: str = field(default_factory=lambda: (datetime.utcnow() + timedelta(hours=24)).isoformat(), init=False)
    
    def is_valid(self) -> bool:
        """Check if proof is still valid (not expired)"""
        expiry_time = datetime.fromisoformat(self.expiry)
        return datetime.utcnow() < expiry_time
    
    def get_content_hash(self) -> str:
        """Get SHA256 hash of proof content for verification"""
        import hashlib
        import json
        content_str = json.dumps(self.proof_content, sort_keys=True)
        return hashlib.sha256(content_str.encode()).hexdigest()
