"""
AdversarialThreat Model - Represents detected threat patterns

Records threat patterns detected by L1 pre-filter or L3 post-gate.
All threats are structured for audit logging and analysis.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal, Optional
from uuid import uuid4


@dataclass(frozen=True)
class AdversarialThreat:
    """
    Represents a detected adversarial threat pattern.
    
    Threat Types:
    - THREAT_TOKEN_SPOOFING: Token address differs from approved whitelist
    - THREAT_DECIMAL_EXPLOIT: Decimal precision attack (rounding exploits)
    - THREAT_UNUSUAL_PARAMETERS: Attack pattern (e.g., 100% slippage)
    - THREAT_REPLAY_ATTEMPT: Duplicate request within time window
    - THREAT_OVERRIDE_ATTEMPT: Attempt to bypass validation gates
    
    Properties:
    - IMMUTABLE (frozen dataclass)
    - STRUCTURED: All threat data in defined format
    - AUDITABLE: Each threat includes detection details and context
    - ACTIONABLE: Rejection reason and recommended action included
    
    Used in:
    - L1 pre-filter (pre-agent threat detection)
    - L3 post-gate (post-agent plan verification)
    - Audit logging (all threats logged for security analysis)
    """
    
    # Identification
    threat_id: str = field(default_factory=lambda: str(uuid4()), init=False)
    threat_type: Literal[
        "THREAT_TOKEN_SPOOFING",
        "THREAT_DECIMAL_EXPLOIT",
        "THREAT_UNUSUAL_PARAMETERS",
        "THREAT_REPLAY_ATTEMPT",
        "THREAT_OVERRIDE_ATTEMPT"
    ] = "THREAT_TOKEN_SPOOFING"
    
    threat_code: str = ""  # Short code for audit logs
    
    # Detection details
    detected_field: str = ""  # Which field triggered detection
    actual_value: str = ""    # The actual value that triggered threat
    policy_threshold: str = ""  # What policy threshold was violated
    
    # Rejection
    rejection_reason: str = ""  # Human-readable rejection reason
    
    # Severity
    severity: Literal["INFO", "WARNING", "CRITICAL"] = "WARNING"
    
    # Context
    detected_at: str = field(default_factory=lambda: datetime.utcnow().isoformat(), init=False)
    detection_layer: Literal["L1_PRE_FILTER", "L3_POST_GATE"] = "L1_PRE_FILTER"
    
    # Downstream action
    recommended_action: str = "block_request"  # "block_request", "block_request_alert_security", etc.
    
    def to_audit_log(self) -> dict:
        """Convert to structured audit log entry"""
        return {
            "timestamp": self.detected_at,
            "event_type": "threat_detected",
            "threat_detected": True,
            "threat_code": self.threat_code,
            "threat_severity": self.severity,
            "detection_layer": self.detection_layer,
            "detected_field": self.detected_field,
            "rejection_reason": self.rejection_reason,
            "threat_id": self.threat_id,
        }
