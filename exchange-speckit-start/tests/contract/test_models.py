"""
Contract tests for quote validation

Tests the CLI interface and quote validation contracts.
Written TEST-FIRST: Tests define the spec, implementation follows.
"""

import pytest
import json
from decimal import Decimal
from datetime import datetime, timedelta
from src.models.swap_quote import SwapQuote
from src.validation.quote_validator import validate_quote


class TestQuoteValidationContracts:
    """Contract tests for quote validation I/O"""
    
    def test_valid_quote_passes_all_gates(self, sample_swap_quote):
        """Test that valid quote passes all validation gates"""
        quote = SwapQuote(**sample_swap_quote)
        
        policy_config = {
            'max_slippage': 10.0,
            'min_confidence': 0.8,
        }
        approved_tokens = [
            "0xfFf9976782d46CC05630D92EE39253E4423ACFB9",
            "0xd5c6C8169A95bA8Af4D1ee8B47EaF3e2Ce68A4b2",
        ]
        
        is_valid, rejection_code = validate_quote(quote, policy_config, approved_tokens)
        
        assert is_valid is True
        assert rejection_code is None
    
    def test_excessive_slippage_rejected(self, invalid_quote_excessive_slippage):
        """Test that quotes with >10% slippage are rejected"""
        quote = SwapQuote(**invalid_quote_excessive_slippage)
        
        policy_config = {'max_slippage': 10.0, 'min_confidence': 0.8}
        approved_tokens = ["0xfFf9976782d46CC05630D92EE39253E4423ACFB9", "0xd5c6C8169A95bA8Af4D1ee8B47EaF3e2Ce68A4b2"]
        
        is_valid, rejection_code = validate_quote(quote, policy_config, approved_tokens)
        
        assert is_valid is False
        assert rejection_code == "QUOTE_EXCESSIVE_SLIPPAGE"
    
    def test_low_confidence_rejected(self, invalid_quote_low_confidence):
        """Test that quotes with <0.8 confidence are rejected"""
        quote = SwapQuote(**invalid_quote_low_confidence)
        
        policy_config = {'max_slippage': 10.0, 'min_confidence': 0.8}
        approved_tokens = ["0xfFf9976782d46CC05630D92EE39253E4423ACFB9", "0xd5c6C8169A95bA8Af4D1ee8B47EaF3e2Ce68A4b2"]
        
        is_valid, rejection_code = validate_quote(quote, policy_config, approved_tokens)
        
        assert is_valid is False
        assert rejection_code == "QUOTE_LOW_CONFIDENCE"
    
    def test_determinism_identical_quotes(self, sample_swap_quote):
        """Test determinism: identical inputs produce identical outputs"""
        quote1 = SwapQuote(**sample_swap_quote)
        quote2 = SwapQuote(**sample_swap_quote)
        
        policy_config = {'max_slippage': 10.0, 'min_confidence': 0.8}
        approved_tokens = ["0xfFf9976782d46CC05630D92EE39253E4423ACFB9", "0xd5c6C8169A95bA8Af4D1ee8B47EaF3e2Ce68A4b2"]
        
        # Validate both quotes
        is_valid1, code1 = validate_quote(quote1, policy_config, approved_tokens)
        is_valid2, code2 = validate_quote(quote2, policy_config, approved_tokens)
        
        # Results must be byte-identical
        assert is_valid1 == is_valid2
        assert code1 == code2
    
    def test_spoofed_token_address_rejected(self, invalid_quote_spoofed_token):
        """Test that spoofed token addresses are rejected"""
        quote = SwapQuote(**invalid_quote_spoofed_token)
        
        policy_config = {'max_slippage': 10.0, 'min_confidence': 0.8}
        approved_tokens = ["0xfFf9976782d46CC05630D92EE39253E4423ACFB9", "0xd5c6C8169A95bA8Af4D1ee8B47EaF3e2Ce68A4b2"]
        
        is_valid, rejection_code = validate_quote(quote, policy_config, approved_tokens)
        
        assert is_valid is False
        assert rejection_code == "QUOTE_INVALID_TOKENS"
    
    def test_validation_no_override_possible(self, sample_swap_quote):
        """Test that validation gates cannot be overridden"""
        quote = SwapQuote(**sample_swap_quote)
        
        # Even with override flag, validation continues
        policy_config = {
            'max_slippage': 10.0,
            'min_confidence': 0.8,
            'skip_validation': True,  # Should be ignored!
        }
        approved_tokens = ["0xfFf9976782d46CC05630D92EE39253E4423ACFB9", "0xd5c6C8169A95bA8Af4D1ee8B47EaF3e2Ce68A4b2"]
        
        is_valid, rejection_code = validate_quote(quote, policy_config, approved_tokens)
        
        # Should still pass normal validation (override ignored)
        assert is_valid is True


class TestThreatDetectionContracts:
    """Contract tests for threat detection"""
    
    def test_token_spoofing_detection(self, invalid_quote_spoofed_token):
        """Test that token spoofing is detected"""
        from src.validation.threat_filters import detect_threats
        
        quote = SwapQuote(**invalid_quote_spoofed_token)
        approved_tokens = ["0xfFf9976782d46CC05630D92EE39253E4423ACFB9", "0xd5c6C8169A95bA8Af4D1ee8B47EaF3e2Ce68A4b2"]
        
        threats = detect_threats(quote, approved_tokens)
        
        assert len(threats) > 0
        assert threats[0].threat_code == "THREAT_TOKEN_SPOOFING"
    
    def test_unusual_parameters_detection(self, invalid_quote_excessive_slippage):
        """Test that unusual parameters (100% slippage) are detected"""
        from src.validation.threat_filters import detect_threats
        
        quote = SwapQuote(**invalid_quote_excessive_slippage)
        
        threats = detect_threats(quote)
        
        # Should detect unusual parameters (100% slippage)
        assert any(t.threat_code == "THREAT_UNUSUAL_PARAMETERS" for t in threats)
