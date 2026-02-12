"""
Logging Package - Structured audit logging

Provides centralized audit logging with privacy preservation and
structured JSON output for security analysis.
"""

from src.logging.audit_logger import StructuredLogger
from src.logging.threat_reporter import format_threat_report, format_threat_summary, classify_threat_severity

__all__ = [
    "StructuredLogger",
    "format_threat_report",
    "format_threat_summary",
    "classify_threat_severity",
]

# Global logger instance
_global_logger = None


def get_logger(name: str = "swap-planning-agent") -> StructuredLogger:
    """Get or create global logger instance"""
    global _global_logger
    if _global_logger is None:
        _global_logger = StructuredLogger(name)
    return _global_logger
