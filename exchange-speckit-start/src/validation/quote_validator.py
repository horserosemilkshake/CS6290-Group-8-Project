"""
Quote Validator - L2 Deterministic Policy Enforcement

Implements non-overridable validation gates that evaluate swap quotes
against strict security policies.

All validation is deterministic: identical inputs always produce identical outputs.
"""

from decimal import Decimal
from typing import Optional, Tuple
from src.models.swap_quote import SwapQuote
from src.models.validation_gate import ValidationGate


def validate_quote_slippage(quote: SwapQuote, max_slippage: float = 10.0) -> Tuple[bool, Optional[str]]:
    """
    Validate slippage tolerance is within policy (<=10%)
    
    Args:
        quote: SwapQuote to validate
        max_slippage: Maximum allowed slippage (default 10%)
        
    Returns:
        tuple: (is_valid, rejection_code or None)
    """
    if quote.slippage_tolerance > Decimal(str(max_slippage)):
        return False, "QUOTE_EXCESSIVE_SLIPPAGE"
    return True, None


def validate_quote_confidence(quote: SwapQuote, min_confidence: float = 0.8) -> Tuple[bool, Optional[str]]:
    """
    Validate market confidence is within policy (>0.8)
    
    Args:
        quote: SwapQuote to validate
        min_confidence: Minimum acceptable confidence (default 0.8)
        
    Returns:
        tuple: (is_valid, rejection_code or None)
    """
    if quote.market_confidence < min_confidence:
        return False, "QUOTE_LOW_CONFIDENCE"
    return True, None


def validate_quote_expiry(quote: SwapQuote) -> Tuple[bool, Optional[str]]:
    """
    Validate quote has not expired
    
    Args:
        quote: SwapQuote to validate
        
    Returns:
        tuple: (is_valid, rejection_code or None)
    """
    if quote.is_expired():
        return False, "QUOTE_EXPIRED"
    return True, None


def validate_quote_required_fields(quote: SwapQuote) -> Tuple[bool, Optional[str]]:
    """
    Validate all required fields are present and non-empty
    
    Args:
        quote: SwapQuote to validate
        
    Returns:
        tuple: (is_valid, rejection_code or None)
    """
    required_fields = [
        'quote_id', 'from_token', 'to_token',
        'from_amount', 'to_amount', 'slippage_tolerance',
        'market_confidence', 'quote_expiry'
    ]
    
    for field in required_fields:
        value = getattr(quote, field, None)
        if value is None or (isinstance(value, str) and not value.strip()):
            return False, "QUOTE_MISSING_FIELDS"
    
    return True, None


def validate_quote_tokens_distinct(quote: SwapQuote) -> Tuple[bool, Optional[str]]:
    """
    Validate from_token and to_token are distinct addresses
    
    Args:
        quote: SwapQuote to validate
        
    Returns:
        tuple: (is_valid, rejection_code or None)
    """
    if quote.from_token.lower() == quote.to_token.lower():
        return False, "QUOTE_INVALID_TOKENS"
    return True, None


def validate_quote_token_whitelist(
    quote: SwapQuote,
    approved_tokens: list
) -> Tuple[bool, Optional[str]]:
    """
    Validate tokens are on approved whitelist
    
    Args:
        quote: SwapQuote to validate
        approved_tokens: List of approved token addresses
        
    Returns:
        tuple: (is_valid, rejection_code or None)
    """
    approved_lower = [t.lower() for t in approved_tokens]
    
    if quote.from_token.lower() not in approved_lower:
        return False, "QUOTE_INVALID_TOKENS"
    if quote.to_token.lower() not in approved_lower:
        return False, "QUOTE_INVALID_TOKENS"
    
    return True, None


def validate_quote(
    quote: SwapQuote,
    policy_config: dict,
    approved_tokens: Optional[list] = None
) -> Tuple[bool, Optional[str]]:
    """
    Execute ALL L2 validation gates against quote (deterministic)
    
    Gates are evaluated in order. First failure returns immediately.
    
    Args:
        quote: SwapQuote to validate
        policy_config: Policy configuration dict
        approved_tokens: List of approved token addresses (optional)
        
    Returns:
        tuple: (is_valid, rejection_code or None)
        
    Note: This is deterministic - identical inputs always produce identical outputs
    """
    
    # Gate 1: Required fields
    is_valid, rejection_code = validate_quote_required_fields(quote)
    if not is_valid:
        return False, rejection_code
    
    # Gate 2: Tokens distinct
    is_valid, rejection_code = validate_quote_tokens_distinct(quote)
    if not is_valid:
        return False, rejection_code
    
    # Gate 3: Token whitelist
    if approved_tokens:
        is_valid, rejection_code = validate_quote_token_whitelist(quote, approved_tokens)
        if not is_valid:
            return False, rejection_code
    
    # Gate 4: Expiry check
    is_valid, rejection_code = validate_quote_expiry(quote)
    if not is_valid:
        return False, rejection_code
    
    # Gate 5: Slippage check
    max_slippage = policy_config.get('max_slippage', 10.0)
    is_valid, rejection_code = validate_quote_slippage(quote, max_slippage)
    if not is_valid:
        return False, rejection_code
    
    # Gate 6: Confidence check
    min_confidence = policy_config.get('min_confidence', 0.8)
    is_valid, rejection_code = validate_quote_confidence(quote, min_confidence)
    if not is_valid:
        return False, rejection_code
    
    # All gates passed
    return True, None
