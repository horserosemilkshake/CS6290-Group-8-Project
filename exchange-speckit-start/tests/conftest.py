"""
pytest configuration and fixtures for Swap Planning Agent tests

This file provides shared fixtures and configuration for all test suites.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock
import json


# ============================================================================
# Fixtures for Common Test Data
# ============================================================================

@pytest.fixture
def sample_swap_quote():
    """Fixture providing a valid SwapQuote for testing"""
    return {
        "quote_id": "test_quote_001",
        "timestamp": datetime.utcnow().isoformat(),
        "source": "dex",
        "from_token": "0xfFf9976782d46CC05630D92EE39253E4423ACFB9",  # WETH (Sepolia)
        "to_token": "0xd5c6C8169A95bA8Af4D1ee8B47EaF3e2Ce68A4b2",   # USDC (Sepolia)
        "from_amount": "1.0",  # 1 WETH
        "to_amount": "2700.0",  # ~2700 USDC at market rate
        "slippage_tolerance": 0.5,  # 0.5% slippage
        "market_confidence": 0.95,  # 95% confidence
        "price_impact": 0.2,  # 0.2% price impact
        "execution_fees": 50.0,  # ~50 USDC in fees
        "quote_expiry": (datetime.utcnow() + timedelta(minutes=10)).isoformat(),
        "created_at": datetime.utcnow().isoformat(),
    }


@pytest.fixture
def invalid_quote_excessive_slippage():
    """Fixture providing a quote with >10% slippage (should be rejected)"""
    quote = {
        "quote_id": "test_quote_bad_slippage",
        "timestamp": datetime.utcnow().isoformat(),
        "source": "user",
        "from_token": "0xfFf9976782d46CC05630D92EE39253E4423ACFB9",
        "to_token": "0xd5c6C8169A95bA8Af4D1ee8B47EaF3e2Ce68A4b2",
        "from_amount": "1.0",
        "to_amount": "2400.0",  # 50% slippage (way over 10% limit)
        "slippage_tolerance": 50.0,  # 50% slippage - INVALID
        "market_confidence": 0.8,
        "price_impact": 45.0,
        "execution_fees": 100.0,
        "quote_expiry": (datetime.utcnow() + timedelta(minutes=10)).isoformat(),
        "created_at": datetime.utcnow().isoformat(),
    }
    return quote


@pytest.fixture
def invalid_quote_low_confidence():
    """Fixture providing a quote with <0.8 confidence (should be rejected)"""
    quote = {
        "quote_id": "test_quote_low_conf",
        "timestamp": datetime.utcnow().isoformat(),
        "source": "dex",
        "from_token": "0xfFf9976782d46CC05630D92EE39253E4423ACFB9",
        "to_token": "0xd5c6C8169A95bA8Af4D1ee8B47EaF3e2Ce68A4b2",
        "from_amount": "1.0",
        "to_amount": "2500.0",
        "slippage_tolerance": 2.0,
        "market_confidence": 0.5,  # 50% - INVALID (< 0.8)
        "price_impact": 1.0,
        "execution_fees": 50.0,
        "quote_expiry": (datetime.utcnow() + timedelta(minutes=10)).isoformat(),
        "created_at": datetime.utcnow().isoformat(),
    }
    return quote


@pytest.fixture
def invalid_quote_spoofed_token():
    """Fixture providing a quote with spoofed token address"""
    quote = {
        "quote_id": "test_quote_spoofed",
        "timestamp": datetime.utcnow().isoformat(),
        "source": "user",
        "from_token": "0xfFf9976782d46CC05630D92EE39253E4423ACFBB",  # 1-char diff from WETH
        "to_token": "0xd5c6C8169A95bA8Af4D1ee8B47EaF3e2Ce68A4b2",
        "from_amount": "1.0",
        "to_amount": "2700.0",
        "slippage_tolerance": 1.0,
        "market_confidence": 0.9,
        "price_impact": 0.3,
        "execution_fees": 50.0,
        "quote_expiry": (datetime.utcnow() + timedelta(minutes=10)).isoformat(),
        "created_at": datetime.utcnow().isoformat(),
    }
    return quote


# ============================================================================
# Fixtures for Mock Services
# ============================================================================

@pytest.fixture
def mock_market_oracle():
    """Fixture providing a mock MarketOracle"""
    oracle = MagicMock()
    oracle.get_price.return_value = {"WETH": 2700, "USDC": 1.0}
    oracle.get_confidence.return_value = 0.95
    return oracle


@pytest.fixture
def mock_eth_rpc():
    """Fixture providing a mock EthereumRPC client"""
    rpc = MagicMock()
    rpc.balance_of.return_value = 10.0  # User has 10 WETH
    rpc.gas_estimate.return_value = 21000  # Standard gas for simple transfer
    rpc.token_allowlist_check.return_value = True
    return rpc


@pytest.fixture
def mock_logger():
    """Fixture providing a mock structured logger"""
    logger = MagicMock()
    logger.log_validation.return_value = None
    logger.log_threat.return_value = None
    return logger


# ============================================================================
# Fixtures for Test Configuration
# ============================================================================

@pytest.fixture
def test_policy_config():
    """Fixture providing test policy configuration"""
    return {
        "max_slippage_check": {
            "threshold": 10.0,
            "operator": "<=",
            "rejection_code": "QUOTE_EXCESSIVE_SLIPPAGE",
        },
        "min_confidence_check": {
            "threshold": 0.8,
            "operator": ">=",
            "rejection_code": "QUOTE_LOW_CONFIDENCE",
        },
        "token_whitelist": ["0xfFf9976782d46CC05630D92EE39253E4423ACFB9", "0xd5c6C8169A95bA8Af4D1ee8B47EaF3e2Ce68A4b2"],
    }


@pytest.fixture
def test_threat_rules():
    """Fixture providing test threat rules"""
    return {
        "THREAT_TOKEN_SPOOFING": {
            "detection_methods": ["whitelist_check", "similarity_match"],
            "rejection_code": "THREAT_TOKEN_SPOOFING",
        },
        "THREAT_DECIMAL_EXPLOIT": {
            "detection_methods": ["decimal_range_check"],
            "rejection_code": "THREAT_DECIMAL_EXPLOIT",
        },
        "THREAT_UNUSUAL_PARAMETERS": {
            "detection_methods": ["slippage_extreme"],
            "rejection_code": "THREAT_UNUSUAL_PARAMETERS",
        },
        "THREAT_REPLAY_ATTEMPT": {
            "detection_methods": ["hash_cache"],
            "rejection_code": "THREAT_REPLAY_ATTEMPT",
            "cache_window_ms": 100,
        },
    }


# ============================================================================
# Test Session Configuration
# ============================================================================

def pytest_configure(config):
    """Configure pytest session"""
    config.addinivalue_line(
        "markers", "requires_network: marks tests that require network access"
    )
