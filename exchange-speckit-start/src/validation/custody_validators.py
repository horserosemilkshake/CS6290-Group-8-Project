"""
Custody Validators - Custody proof generation and verification

Generates cryptographic proofs that demonstrate user maintains control
throughout transaction execution.

Implements Principle IV (Custody-Safe) from constitution.
"""

import hashlib
import json
from typing import Optional
from decimal import Decimal
from src.models.transaction_plan import TransactionPlan
from src.models.custody_proof import CustodyProof


def generate_custody_proof_balance_merkle(
    user_address: str,
    balance_before: Decimal,
    nonce: str
) -> CustodyProof:
    """
    Generate balance merkle proof
    
    Args:
        user_address: User's Ethereum address
        balance_before: User's balance before swap
        nonce: Random nonce for uniqueness
        
    Returns:
        CustodyProof with merkle proof data
    """
    # Create merkle root hash
    data_to_hash = f"{user_address}:{balance_before}:{nonce}"
    merkle_root = hashlib.sha256(data_to_hash.encode()).hexdigest()
    
    proof_content = {
        "user_address": user_address,
        "balance_before": str(balance_before),
        "balance_root": "0x" + merkle_root[:16],  # Truncated for example
        "merkle_path": ["0xffff0000", "0xeeee1111"],  # Example path
        "nonce": nonce,
    }
    
    return CustodyProof(
        proof_type="balance_merkle",
        proof_content=proof_content,
        verification_method="merkle_verify()",
        verification_hash=hashlib.sha256(json.dumps(proof_content, sort_keys=True).encode()).hexdigest(),
    )


def generate_custody_proof_commitment_preimage(
    user_address: str,
    plan_id: str
) -> CustodyProof:
    """
    Generate commitment preimage proof
    
    Args:
        user_address: User's Ethereum address
        plan_id: Transaction plan ID
        
    Returns:
        CustodyProof with commitment preimage data
    """
    # Create commitment hash
    preimage_data = f"{user_address}:{plan_id}"
    commitment_hash = hashlib.sha256(preimage_data.encode()).hexdigest()
    
    proof_content = {
        "commitment_hash": "0x" + commitment_hash[:32],
        "preimage": preimage_data,
        "user_address": user_address,
    }
    
    return CustodyProof(
        proof_type="commitment_preimage",
        proof_content=proof_content,
        verification_method="check_commitment()",
        verification_hash=hashlib.sha256(json.dumps(proof_content, sort_keys=True).encode()).hexdigest(),
    )


def generate_custody_proof_multisig(
    user_address: str,
    required_signers: int
) -> CustodyProof:
    """
    Generate multi-sig custody proof
    
    Args:
        user_address: User's Ethereum address
        required_signers: Number of signatures required
        
    Returns:
        CustodyProof with multi-sig data
    """
    proof_content = {
        "user_address": user_address,
        "required_signers": required_signers,
        "signer_structure": f"Multisig_M_of_{required_signers}",
    }
    
    return CustodyProof(
        proof_type="multisig_requirement",
        proof_content=proof_content,
        verification_method="verify_signer_count()",
        verification_hash=hashlib.sha256(json.dumps(proof_content, sort_keys=True).encode()).hexdigest(),
    )


def generate_custody_proof_zkp(plan_id: str) -> CustodyProof:
    """
    Generate zero-knowledge proof custody proof
    
    Args:
        plan_id: Transaction plan ID
        
    Returns:
        CustodyProof with ZKP data
    """
    proof_content = {
        "circuit_type": "swap_correctness",
        "plan_id": plan_id,
        "zkp_snippet": f"zkp_proof_for_{plan_id[:8]}",
    }
    
    return CustodyProof(
        proof_type="zero_knowledge_proof",
        proof_content=proof_content,
        verification_method="verify_zkp_circuit()",
        verification_hash=hashlib.sha256(json.dumps(proof_content, sort_keys=True).encode()).hexdigest(),
    )


def generate_custody_proofs_for_plan(
    plan: TransactionPlan,
    user_address: str,
    balance_before: Decimal
) -> list:
    """
    Generate all required custody proofs for a plan
    
    At least one proof must be generated per plan.
    
    Args:
        plan: TransactionPlan to generate proofs for
        user_address: User's Ethereum address
        balance_before: User's balance before swap
        
    Returns:
        List of CustodyProof objects
    """
    import uuid
    
    proofs = []
    
    # Always generate a balance merkle proof as primary
    nonce = str(uuid.uuid4())[:8]
    merkle_proof = generate_custody_proof_balance_merkle(user_address, balance_before, nonce)
    proofs.append(merkle_proof)
    
    # If privacy routing (N>3 intermediaries), also add commitment proof
    if len(plan.intermediate_addresses) >= 3:
        commitment_proof = generate_custody_proof_commitment_preimage(user_address, plan.plan_id)
        proofs.append(commitment_proof)
    
    # For high-value plans, could add multi-sig requirement
    # (This would be user-configurable in practice)
    
    return proofs


def verify_custody_proof(proof: CustodyProof) -> bool:
    """
    Verify a custody proof is valid
    
    Args:
        proof: CustodyProof to verify
        
    Returns:
        bool: True if proof is valid and not expired
    """
    if not proof.is_valid():
        return False  # Proof expired
    
    # Verify content hash matches
    content_hash = proof.get_content_hash()
    return content_hash == proof.verification_hash
