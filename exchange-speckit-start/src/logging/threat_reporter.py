"""
Threat Reporter - Format threat detection results for audit logging

Provides structured threat classification and reporting for audit trails.

Implements Principle III (Adversarial Robustness) from constitution:
- All threats classified and logged with structured format
- Threat codes enable automated analysis
- Audit trail captures detection details without sensitive data
"""

import json
from datetime import datetime
from typing import Dict, Any, Optional
from src.models.adversarial_threat import AdversarialThreat


class ThreatReporter:
    """
    Formats threat detections into structured audit-ready reports.
    """
    
    def format_threat_report(self, threat: AdversarialThreat) -> Dict[str, Any]:
        """
        Convert AdversarialThreat to audit-ready JSON dict
        
        Args:
            threat: AdversarialThreat object
            
        Returns:
            dict: Structured threat report for logging
        """
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": "threat_detected",
            "threat_detected": True,
            "threat_id": threat.threat_id,
            "threat_code": threat.threat_code,
            "threat_type": threat.threat_type,
            "severity": threat.severity,
            "detected_field": threat.detected_field,
            "detection_layer": threat.detection_layer,
            "rejection_reason": threat.rejection_reason,
            "recommended_action": threat.recommended_action,
        }
    
    def format_threat_summary(self, threats: list) -> Dict[str, Any]:
        """
        Create summary of multiple threats (for batch reporting)
        
        Args:
            threats: List of AdversarialThreat objects
            
        Returns:
            dict: Aggregated threat summary
        """
        by_code = {}
        by_severity = {"INFO": 0, "WARNING": 0, "CRITICAL": 0}
        
        for threat in threats:
            # Group by threat code
            if threat.threat_code not in by_code:
                by_code[threat.threat_code] = 0
            by_code[threat.threat_code] += 1
            
            # Count by severity
            by_severity[threat.severity] += 1
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": "threat_summary",
            "total_threats": len(threats),
            "threats_by_code": by_code,
            "threats_by_severity": by_severity,
            "critical_count": by_severity["CRITICAL"],
            "warning_count": by_severity["WARNING"],
            "info_count": by_severity["INFO"],
        }
    
    def classify_threat_severity(self, threat_code: str) -> str:
        """
        Classify threat severity based on threat code
        
        Args:
            threat_code: Threat classification code
            
        Returns:
            str: "INFO", "WARNING", or "CRITICAL"
        """
        critical_threats = {
            "THREAT_TOKEN_SPOOFING",
            "THREAT_OVERRIDE_ATTEMPT",
        }
        
        warning_threats = {
            "THREAT_DECIMAL_EXPLOIT",
            "THREAT_UNUSUAL_PARAMETERS",
            "THREAT_REPLAY_ATTEMPT",
        }
        
        if threat_code in critical_threats:
            return "CRITICAL"
        elif threat_code in warning_threats:
            return "WARNING"
        else:
            return "INFO"


# Global reporter instance
_reporter = ThreatReporter()


def format_threat_report(threat: AdversarialThreat) -> Dict[str, Any]:
    """Module-level function for threat reporting"""
    return _reporter.format_threat_report(threat)


def format_threat_summary(threats: list) -> Dict[str, Any]:
    """Module-level function for threat summary"""
    return _reporter.format_threat_summary(threats)


def classify_threat_severity(threat_code: str) -> str:
    """Module-level function for severity classification"""
    return _reporter.classify_threat_severity(threat_code)
