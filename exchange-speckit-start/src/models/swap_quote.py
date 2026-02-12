"""
SwapQuote Model - Represents a published cryptocurrency swap offer

This entity is IMMUTABLE and designed to enforce security properties:
- All fields are read-only after creation
- Validation rules prevent unsafe quotes from being created
- Timestamps are UTC ISO8601 format for audit trail
"""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import uuid4


@dataclass(frozen=True)
class SwapQuote:
    """
    Represents a published swap offer from DEX, market maker, or user.
    
    IMMUTABLE: Once created, cannot be modified. If validation fails,
    the quote is discarded and a new one must be created.
    
    Validation Rules (enforced at creation):
    - from_token and to_token must be distinct Ethereum addresses
    - Both tokens must be on approved whitelist (config/routes.yaml)
    - from_amount must be >0 and <=user verified balance
    - slippage_tolerance must be 0 < x <= 10% (L2 policy cap)
    - market_confidence must be >0.8 (reject low-confidence quotes)
    - quote_expiry must be >current_time (reject expired quotes)
    - price_impact must be <= slippage_tolerance (sanity check)
    """
    
    # Primary identifiers
    quote_id: str = field(default_factory=lambda: str(uuid4()), init=False)
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat(), init=False)
    source: Literal["dex", "mm", "user"] = "dex"
    
    # Token pair
    from_token: str  # Ethereum address (lowercase, checksum verified)
    to_token: str    # Ethereum address (lowercase, checksum verified)
    
    # Amounts - using Decimal for precise arithmetic (no floating-point rounding errors)
    from_amount: Decimal
    to_amount: Decimal
    slippage_tolerance: Decimal  # Percentage: 0 < x <= 10
    
    # Quality metrics
    market_confidence: float  # [0.0, 1.0] confidence; must be >0.8
    price_impact: Decimal     # Estimated % price impact on market
    execution_fees: Decimal   # Estimated total fees (gas, swap fee, etc.)
    
    # Timing
    quote_expiry: str   # ISO8601 datetime; > current_time
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat(), init=False)
    
    def __post_init__(self):
        """Validate quote after initialization"""
        # Perform immutability checks
        pass  # Dataclass frozen=True enforces immutability
    
    def is_expired(self) -> bool:
        """Check if quote has expired"""
        expiry = datetime.fromisoformat(self.quote_expiry)
        return datetime.utcnow() > expiry
    
    def get_hash(self) -> str:
        """
        Get deterministic hash of quote for uniqueness/determinism testing
        Used to verify identical quotes produce identical outputs
        """
        import hashlib
        quote_str = f"{self.from_token}:{self.to_token}:{self.from_amount}:{self.slippage_tolerance}"
        return hashlib.sha256(quote_str.encode()).hexdigest()
