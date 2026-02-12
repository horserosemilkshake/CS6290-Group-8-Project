"""
Ethereum RPC Client - Blockchain interaction

Provides interface for Ethereum RPC calls (balance, gas estimation, etc).
Implementation uses mock for Phase 1; real integration in Phase 2.
"""

from decimal import Decimal
from typing import Optional, List


class EthereumRPC:
    """Interface for Ethereum RPC interactions"""
    
    def __init__(self, provider_uri: str = "", use_mock: bool = True):
        self.provider_uri = provider_uri
        self.use_mock = use_mock
    
    def balance_of(self, user_address: str, token_address: str) -> Decimal:
        """
        Get user's token balance
        
        Args:
            user_address: User's Ethereum address
            token_address: Token contract address
            
        Returns:
            Decimal: User's balance
        """
        if self.use_mock:
            return Decimal("10.0")  # Mock: user has 10 tokens
        return Decimal("0")
    
    def gas_estimate(self) -> int:
        """
        Estimate gas for standard swap operation
        
        Returns:
            int: Gas units
        """
        if self.use_mock:
            return 250000  # Mock: ~250k gas
        return 0
    
    def token_allowlist_check(self, token_address: str) -> bool:
        """
        Check if token is on approved list
        
        Args:
            token_address: Token contract address
            
        Returns:
            bool: True if approved
        """
        if self.use_mock:
            approved = [
                "0xfFf9976782d46CC05630D92EE39253E4423ACFB9",  # WETH
                "0xd5c6C8169A95bA8Af4D1ee8B47EaF3e2Ce68A4b2",  # USDC
            ]
            return token_address.lower() in [t.lower() for t in approved]
        return False
