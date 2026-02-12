"""
Quote Cache - Caching layer for DEX quotes

Implements 10-minute TTL caching with fallback to live quotes.
Simple dict-based implementation for Phase 1.
"""

from datetime import datetime, timedelta
from typing import Dict, Optional


class QuoteCache:
    """Simple in-memory quote cache with TTL"""
    
    def __init__(self, ttl_seconds: int = 600):
        """
        Initialize cache
        
        Args:
            ttl_seconds: Time-to-live for cached quotes (default 10 minutes)
        """
        self.ttl_seconds = ttl_seconds
        self.cache: Dict[str, dict] = {}
    
    def get(self, quote_id: str) -> Optional[dict]:
        """
        Get cached quote if still valid
        
        Args:
            quote_id: Quote identifier
            
        Returns:
            dict: Cached quote or None if expired
        """
        if quote_id in self.cache:
            entry = self.cache[quote_id]
            age_seconds = (datetime.utcnow() - entry['cached_at']).total_seconds()
            
            if age_seconds < self.ttl_seconds:
                return entry['quote']
            else:
                del self.cache[quote_id]  # Expired, remove
        
        return None
    
    def set(self, quote_id: str, quote: dict) -> None:
        """
        Cache a quote
        
        Args:
            quote_id: Quote identifier
            quote: Quote data to cache
        """
        self.cache[quote_id] = {
            'quote': quote,
            'cached_at': datetime.utcnow(),
        }
    
    def clear(self) -> None:
        """Clear all cached quotes"""
        self.cache.clear()
