"""
Threat Filters - L1/L3 Adversarial Threat Detection

Implements layered threat detection that identifies and rejects
adversarial input patterns.

Can be invoked pre-LLM (L1 pre-filter) or post-LLM (L3 post-gate).
"""

from typing import List, Optional
from datetime import datetime, timedelta
from src.models.swap_quote import SwapQuote
from src.models.adversarial_threat import AdversarialThreat
from src.models.transaction_plan import TransactionPlan


class ReplayCache:
    """Simple in-memory cache for replay attack detection"""
    
    def __init__(self, window_ms: int = 100):
        self.window_ms = window_ms
        self.cache = {}  # {hash: timestamp}
    
    def is_duplicate(self, item_hash: str) -> bool:
        """Check if hash seen recently (within window)"""
        now = datetime.utcnow()
        
        if item_hash in self.cache:
            cached_time = self.cache[item_hash]
            age_ms = (now - cached_time).total_seconds() * 1000
            return age_ms < self.window_ms
        
        # Add to cache
        self.cache[item_hash] = now
        
        # Cleanup old entries
        cutoff = now - timedelta(milliseconds=self.window_ms * 2)
        self.cache = {h: t for h, t in self.cache.items() if t > cutoff}
        
        return False


_replay_cache = ReplayCache(window_ms=100)


def detect_token_spoofing(
    quote: SwapQuote,
    approved_tokens: List[str]
) -> Optional[AdversarialThreat]:
    """
    Detect token address spoofing (address similar to legitimate token)
    
    Args:
        quote: SwapQuote to check
        approved_tokens: List of approved token addresses
        
    Returns:
        AdversarialThreat if spoofing detected, None otherwise
    """
    approved_lower = [t.lower() for t in approved_tokens]
    
    # Check exact match first
    if quote.from_token.lower() not in approved_lower and quote.to_token.lower() not in approved_lower:
        # Check for 1-2 character differences (spoofing attempt)
        for approved in approved_lower:
            if _similar_address(quote.from_token.lower(), approved, max_diff=2):
                return AdversarialThreat(
                    threat_type="THREAT_TOKEN_SPOOFING",
                    threat_code="THREAT_TOKEN_SPOOFING",
                    detected_field="from_token",
                    actual_value=quote.from_token,
                    policy_threshold=",".join(approved_tokens[:3]),
                    rejection_reason="Token address mismatch detected against whitelist",
                    severity="CRITICAL",
                    detection_layer="L1_PRE_FILTER",
                )
            if _similar_address(quote.to_token.lower(), approved, max_diff=2):
                return AdversarialThreat(
                    threat_type="THREAT_TOKEN_SPOOFING",
                    threat_code="THREAT_TOKEN_SPOOFING",
                    detected_field="to_token",
                    actual_value=quote.to_token,
                    policy_threshold=",".join(approved_tokens[:3]),
                    rejection_reason="Token address mismatch detected against whitelist",
                    severity="CRITICAL",
                    detection_layer="L1_PRE_FILTER",
                )
    
    return None


def detect_decimal_exploit(quote: SwapQuote) -> Optional[AdversarialThreat]:
    """
    Detect decimal precision exploit (rounding errors, underflow)
    
    Args:
        quote: SwapQuote to check
        
    Returns:
        AdversarialThreat if exploit detected, None otherwise
    """
    # Check for extremely small amounts
    if quote.from_amount < 0.00000001 or quote.from_amount > 999999999999999999:
        return AdversarialThreat(
            threat_type="THREAT_DECIMAL_EXPLOIT",
            threat_code="THREAT_DECIMAL_EXPLOIT",
            detected_field="from_amount",
            actual_value=str(quote.from_amount),
            policy_threshold="0.00000001 - 999999999999999999",
            rejection_reason="Amount precision outside safe range",
            severity="HIGH",
            detection_layer="L1_PRE_FILTER",
        )
    
    return None


def detect_unusual_parameters(quote: SwapQuote) -> Optional[AdversarialThreat]:
    """
    Detect unusual parameters that suggest attack (e.g., 100% slippage)
    
    Args:
        quote: SwapQuote to check
        
    Returns:
        AdversarialThreat if unusual params detected, None otherwise
    """
    # 100% slippage suggests attack (guarantees failure or massive loss)
    if quote.slippage_tolerance >= 99:
        return AdversarialThreat(
            threat_type="THREAT_UNUSUAL_PARAMETERS",
            threat_code="THREAT_UNUSUAL_PARAMETERS",
            detected_field="slippage_tolerance",
            actual_value=str(quote.slippage_tolerance),
            policy_threshold="<=10%",
            rejection_reason="Quote parameters match known attack pattern",
            severity="HIGH",
            detection_layer="L1_PRE_FILTER",
        )
    
    # Near-zero confidence suggests manipulation
    if quote.market_confidence < 0.1:
        return AdversarialThreat(
            threat_type="THREAT_UNUSUAL_PARAMETERS",
            threat_code="THREAT_UNUSUAL_PARAMETERS",
            detected_field="market_confidence",
            actual_value=str(quote.market_confidence),
            policy_threshold=">=0.8",
            rejection_reason="Quote parameters match known attack pattern",
            severity="HIGH",
            detection_layer="L1_PRE_FILTER",
        )
    
    return None


def detect_replay_attempt(quote: SwapQuote) -> Optional[AdversarialThreat]:
    """
    Detect replay attacks (duplicate requests within time window)
    
    Args:
        quote: SwapQuote to check
        
    Returns:
        AdversarialThreat if replay detected, None otherwise
    """
    quote_hash = quote.get_hash()
    
    if _replay_cache.is_duplicate(quote_hash):
        return AdversarialThreat(
            threat_type="THREAT_REPLAY_ATTEMPT",
            threat_code="THREAT_REPLAY_ATTEMPT",
            detected_field="quote_hash",
            actual_value=quote_hash,
            policy_threshold="no_duplicates_within_100ms",
            rejection_reason="Duplicate request detected within skip window",
            severity="MEDIUM",
            detection_layer="L1_PRE_FILTER",
        )
    
    return None


def detect_threats(
    quote: SwapQuote,
    approved_tokens: Optional[List[str]] = None
) -> List[AdversarialThreat]:
    """
    Execute ALL threat detection filters on quote (L1 pre-filter)
    
    Args:
        quote: SwapQuote to check
        approved_tokens: List of approved token addresses
        
    Returns:
        List of detected AdversarialThreat objects (empty if no threats)
    """
    threats = []
    
    # Check 1: Token spoofing
    if approved_tokens:
        threat = detect_token_spoofing(quote, approved_tokens)
        if threat:
            threats.append(threat)
            return threats  # Return immediately on critical threat
    
    # Check 2: Decimal exploit
    threat = detect_decimal_exploit(quote)
    if threat:
        threats.append(threat)
    
    # Check 3: Unusual parameters
    threat = detect_unusual_parameters(quote)
    if threat:
        threats.append(threat)
    
    # Check 4: Replay attempt
    threat = detect_replay_attempt(quote)
    if threat:
        threats.append(threat)
    
    return threats


def _similar_address(addr1: str, addr2: str, max_diff: int = 2) -> bool:
    """Check if addresses are similar (differ by at most max_diff chars)"""
    if len(addr1) != len(addr2):
        return False
    
    diff_count = sum(c1 != c2 for c1, c2 in zip(addr1, addr2))
    return diff_count <= max_diff
