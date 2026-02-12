"""
Market Oracle - External market data provider interface

Provides market price data from external oracles.
Implementation uses mock for Phase 1; real integration in Phase 2.
"""

from typing import Dict, Optional
from decimal import Decimal


class MarketOracle:
    """Interface for market data provider"""
    
    def __init__(self, use_mock: bool = True):
        self.use_mock = use_mock
        self.mock_data = {
            "WETH": Decimal("2700"),
            "USDC": Decimal("1.0"),
        }
    
    def get_price(self, token_pair: str) -> Optional[Decimal]:
        """
        Get current market price for token pair
        
        Args:
            token_pair: "TOKEN1/TOKEN2" format
            
        Returns:
            Decimal: Current price or None
        """
        if self.use_mock:
            tokens = token_pair.split("/")
            if len(tokens) == 2:
                token1, token2 = tokens
                price1 = self.mock_data.get(token1.upper())
                price2 = self.mock_data.get(token2.upper())
                if price1 and price2:
                    return price1 / price2
        return None
    
    def get_confidence(self, token_pair: str) -> float:
        """
        Get confidence in price data (0.0 - 1.0)
        
        Args:
            token_pair: "TOKEN1/TOKEN2" format
            
        Returns:
            float: Confidence score
        """
        if self.use_mock:
            return 0.95  # Mock data has high confidence
        return 0.0
