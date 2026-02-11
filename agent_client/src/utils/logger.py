"""
Logging utility
"""
import logging
import sys
from datetime import datetime


def setup_logger(name: str = "ai-agent") -> logging.Logger:
    """Configure and return a logger instance"""
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    
    # Console output
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.INFO)
    
    # Formatting
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    handler.setFormatter(formatter)
    
    logger.addHandler(handler)
    return logger


# Global logger
logger = setup_logger()
