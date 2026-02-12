"""
ValidationGate Model - Represents deterministic security policy check

This entity enforces non-overridable validation gates that cannot be modified
at runtime. All changes require Git commit + security team review.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable, Literal, Optional, Union
from decimal import Decimal


@dataclass(frozen=True)
class ValidationGate:
    """
    Represents a single deterministic security policy validation gate.
    
    Properties:
    - MUST be non-overridable (enforcement_level = "REJECT_NO_OVERRIDE")
    - MUST use deterministic test_function (no randomness)
    - MUST be immutable (frozen dataclass)
    - MUST be defined in YAML config (config/policy.yaml)
    - Changes require git commit + security team review
    
    Examples:
    - max_slippage_check: slippage_tolerance <= 10%
    - min_confidence_check: market_confidence >= 0.8
    - token_whitelist_check: from_token and to_token in approved list
    
    No Dynamic Overrides: System MUST reject any request to bypass,
    modify, or skip a ValidationGate at runtime.
    """
    
    # Identification
    gate_id: str  # Unique identifier (e.g., "max_slippage_check")
    gate_name: str  # Human-readable name
    description: str  # What this gate enforces
    
    # Policy definition
    threshold: Optional[Union[float, Decimal, str]] = None  # Policy threshold value
    operator: Literal["<=", ">=", "<", ">", "==", "!=", "in", "not_in"]  # Comparison
    parameter_path: str = ""  # Path into quote (e.g., "slippage_tolerance")
    
    # Enforcement - MUST ALWAYS BE NON-NEGOTIABLE
    enforcement_level: Literal["REJECT_NO_OVERRIDE"] = "REJECT_NO_OVERRIDE"
    rejection_code: str = ""  # Code returned if gate fails
    
    # Testing - MUST be pure function (no side effects, deterministic)
    test_function: Optional[Callable] = field(default=None, repr=False)
    
    # Audit trail
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat(), init=False)
    modified_at: str = field(default_factory=lambda: datetime.utcnow().isoformat(), init=False)
    modified_by: str = "SYSTEM"  # Security team member who modified
    
    def evaluate(self, quote) -> bool:
        """
        Evaluate this gate against a quote (deterministic)
        
        Args:
            quote: SwapQuote to evaluate
            
        Returns:
            bool: True if quote passes gate, False if fails
            
        Must be deterministic: identical inputs always produce identical outputs
        """
        if self.test_function:
            return self.test_function(quote)
        
        # Fallback: evaluate using threshold/operator
        from src.models.swap_quote import SwapQuote
        quote_value = getattr(quote, self.parameter_path.split(',')[0], None)
        
        if quote_value is None:
            return False
        
        if self.operator == "<=":
            return quote_value <= self.threshold
        elif self.operator == ">=":
            return quote_value >= self.threshold
        elif self.operator == "<":
            return quote_value < self.threshold
        elif self.operator == ">":
            return quote_value > self.threshold
        elif self.operator == "==":
            return quote_value == self.threshold
        elif self.operator == "!=":
            return quote_value != self.threshold
        elif self.operator == "in":
            return quote_value in self.threshold if isinstance(self.threshold, (list, tuple)) else False
        elif self.operator == "not_in":
            return quote_value not in self.threshold if isinstance(self.threshold, (list, tuple)) else False
        
        return False
    
    def can_be_overridden(self) -> bool:
        """Gate cannot be overridden (enforcement_level is always REJECT_NO_OVERRIDE)"""
        return False
