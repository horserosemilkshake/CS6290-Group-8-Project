"""
Threat Catalog - Threat pattern definitions and test cases

Defines all threat types that the system detects and rejects.

Can be extended with new threat patterns as they're discovered.
"""


class ThreatCatalog:
    """Centralized threat pattern definitions"""
    
    THREAT_PATTERNS = {
        "THREAT_TOKEN_SPOOFING": {
            "name": "Token Address Spoofing",
            "description": "Token address differs by 1-2 characters from approved whitelist",
            "detection_method": "similarity_match",
            "severity": "CRITICAL",
            "test_patterns": [
                {
                    "legitimate": "0xfFf9976782d46CC05630D92EE39253E4423ACFB9",
                    "spoofed": "0xfFf9976782d46CC05630D92EE39253E4423ACFBB",  # Last char different
                    "description": "1-character substitution"
                }
            ]
        },
        
        "THREAT_DECIMAL_EXPLOIT": {
            "name": "Decimal Precision Exploit",
            "description": "Extreme decimal precision that triggers rounding errors or underflow",
            "detection_method": "decimal_range_check",
            "severity": "HIGH",
            "test_patterns": [
                {
                    "amount": "0.000000001",
                    "description": "Extreme precision below safe minimum"
                },
                {
                    "amount": "999999999999999999999",
                    "description": "Numeric overflow risk"
                }
            ]
        },
        
        "THREAT_UNUSUAL_PARAMETERS": {
            "name": "Unusual Parameters Attack",
            "description": "Unusual parameter values that suggest attack (e.g., 100% slippage)",
            "detection_method": "parameter_matching",
            "severity": "HIGH",
            "test_patterns": [
                {
                    "parameter": "slippage_tolerance",
                    "value": "100",
                    "description": "100% slippage guarantees failure"
                },
                {
                    "parameter": "market_confidence",
                    "value": "0.05",
                    "description": "Near-zero confidence is suspicious"
                },
                {
                    "parameter": "slippage_tolerance",
                    "value": "99.9",
                    "description": "Near-maximal slippage"
                }
            ]
        },
        
        "THREAT_REPLAY_ATTEMPT": {
            "name": "Replay Attack",
            "description": "Duplicate request within time window",
            "detection_method": "hash_cache",
            "severity": "MEDIUM",
            "cache_window_ms": 100,
            "test_patterns": [
                {
                    "scenario": "identical_quote_100ms_apart",
                    "description": "Same quote hash submitted twice within 100ms"
                },
                {
                    "scenario": "sequential_identical_quotes",
                    "description": "Three identical quote submissions in rapid succession"
                }
            ]
        },
        
        "THREAT_OVERRIDE_ATTEMPT": {
            "name": "Authorization Bypass",
            "description": "Attempt to bypass or override validation gates",
            "detection_method": "gate_skip_request",
            "severity": "CRITICAL",
            "test_patterns": [
                {
                    "scenario": "skip_validation_flag",
                    "description": 'Request includes "skip_validation" parameter'
                },
                {
                    "scenario": "enforcement_modification",
                    "description": 'Attempt to modify gate enforcement_level in request'
                }
            ]
        }
    }
    
    @classmethod
    def get_threat_pattern(cls, threat_code: str) -> dict:
        """Get threat pattern definition"""
        return cls.THREAT_PATTERNS.get(threat_code, {})
    
    @classmethod
    def get_all_threat_codes(cls) -> list:
        """Get list of all threat codes"""
        return list(cls.THREAT_PATTERNS.keys())
    
    @classmethod
    def get_test_patterns(cls, threat_code: str) -> list:
        """Get test patterns for a threat"""
        pattern = cls.get_threat_pattern(threat_code)
        return pattern.get("test_patterns", [])
    
    @classmethod
    def is_critical_threat(cls, threat_code: str) -> bool:
        """Check if threat is critical severity"""
        pattern = cls.get_threat_pattern(threat_code)
        return pattern.get("severity") == "CRITICAL"
