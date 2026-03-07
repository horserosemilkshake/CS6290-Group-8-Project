"""
Project configuration management
"""
import os
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings

# Resolve project root: settings.py -> config/ -> src/ -> agent_client/ -> project root
_PROJECT_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    """Application settings"""
    
    # API configuration
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    API_VERSION: str = "v0"
    
    # LLM configuration
    OPENAI_API_KEY: Optional[str] = None
    LLM_MODEL: str = "gpt-4"
    LLM_TEMPERATURE: float = 0.1  # Low temperature for stable output
    LLM_MAX_TOKENS: int = 1000
    
    # Security limits
    MAX_TRANSACTION_VALUE_ETH: float = 10.0  # Max transaction amount
    MAX_SLIPPAGE_BPS: int = 1000  # Max slippage 10%
    REQUEST_TIMEOUT_SECONDS: int = 30
    
    # Tool configuration (reserved)
    PREFERRED_AGGREGATORS: list = ["1inch", "0x"]
    
    class Config:
        env_file = str(_PROJECT_ROOT / ".env")
        case_sensitive = True
        extra = "ignore"


# Global settings instance
settings = Settings()
