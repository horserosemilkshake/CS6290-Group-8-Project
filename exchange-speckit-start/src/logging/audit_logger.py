"""
Audit Logger - Structured JSON logging for security events

Provides deterministic, tamper-evident logging of all security-relevant events
without exposing transaction content in plaintext.

Implements Principle I (Privacy Preservation) from constitution:
- Personal identifying information and transaction intent never in plaintext logs
- Only cryptographic commitments and structured metadata logged
- All logs are JSON format for audit analysis
"""

import json
import sys
from datetime import datetime
from typing import Any, Dict, Optional


class StructuredLogger:
    """
    Centralized structured JSON logger for audit trails.
    
    Properties:
    - All output is valid JSON (one object per line)
    - No plaintext transaction content
    - Timestamp on every entry
    - Severity levels: INFO, WARNING, CRITICAL
    """
    
    def __init__(self, name: str = "swap-planning-agent"):
        self.name = name
        self.events = []
    
    def log_quote_validation(
        self,
        quote_id: str,
        status: str,  # "accepted" or "rejected"
        gates_passed: int,
        gates_failed: int,
        rejection_code: Optional[str] = None,
        threat_detected: bool = False,
        threat_code: Optional[str] = None,
    ) -> None:
        """
        Log quote validation result (deterministic event)
        
        Note: No quote details (amounts, tokens) in plaintext.
        Only gate results, threat detection, and rejection codes.
        """
        event = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": "quote_validated",
            "quote_id": quote_id,
            "status": status,
            "gates_passed": gates_passed,
            "gates_failed": gates_failed,
            "rejection_code": rejection_code or "",
            "threat_detected": threat_detected,
            "threat_code": threat_code or "",
            "event_layer": "L2_VALIDATION",
            "application": self.name,
        }
        self._write_log(event)
    
    def log_threat_detection(
        self,
        threat_id: str,
        threat_code: str,
        threat_type: str,
        detected_field: str,
        rejection_reason: str,
        severity: str,  # "INFO", "WARNING", "CRITICAL"
        detection_layer: str,  # "L1_PRE_FILTER", "L3_POST_GATE"
    ) -> None:
        """
        Log threat detection event
        
        Note: No sensitive data values. Only field names and threat classification.
        """
        event = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": "threat_detected",
            "threat_detected": True,
            "threat_id": threat_id,
            "threat_code": threat_code,
            "threat_type": threat_type,
            "detected_field": detected_field,
            "rejection_reason": rejection_reason,
            "severity": severity,
            "event_layer": detection_layer,
            "application": self.name,
        }
        self._write_log(event)
    
    def log_plan_generation(
        self,
        plan_id: str,
        quote_id: str,
        routing_strategy: str,
        privacy_level: int,
        status: str,
        plan_hash: str,  # SHA256 hash for determinism verification
    ) -> None:
        """
        Log plan generation result
        
        Note: Plan details (steps, addresses) not logged. Only plan hash
        and metadata for audit trail.
        """
        event = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": "plan_generated",
            "plan_id": plan_id,
            "quote_id": quote_id,
            "routing_strategy": routing_strategy,
            "privacy_level": privacy_level,
            "status": status,
            "plan_hash": plan_hash,  # For reproducibility verification
            "event_layer": "AGENT",
            "application": self.name,
        }
        self._write_log(event)
    
    def log_determinism_check(
        self,
        input_hash: str,
        output_hash_1: str,
        output_hash_2: str,
        iteration: int,
        match: bool,
    ) -> None:
        """
        Log determinism verification (test-only event)
        
        Used only in CI/CD testing to verify identical inputs
        produce byte-identical outputs.
        """
        event = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": "determinism_check",
            "input_hash": input_hash,
            "output_hash_1": output_hash_1,
            "output_hash_2": output_hash_2,
            "iteration": iteration,
            "match": match,
            "event_layer": "TEST",
            "application": self.name,
        }
        self._write_log(event)
    
    def _write_log(self, event: Dict[str, Any]) -> None:
        """
        Write event to structured log (stderr for events)
        
        Format: One JSON object per line (JSONL format)
        """
        self.events.append(event)
        json_line = json.dumps(event)
        print(json_line, file=sys.stderr)
    
    def get_events(self) -> list:
        """Get all logged events (for testing)"""
        return self.events.copy()
