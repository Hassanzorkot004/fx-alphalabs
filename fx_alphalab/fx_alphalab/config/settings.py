"""Configuration settings for FX AlphaLab using Pydantic"""

import os
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings
from dotenv import load_dotenv


# Explicitly load .env file from fx_alphalab root
# This ensures environment variables are available regardless of CWD
_env_path = Path(__file__).parent.parent.parent / ".env"
if _env_path.exists():
    load_dotenv(_env_path)


class Settings(BaseSettings):
    """Application settings with environment variable support"""
    
    # Paths (relative to package or configurable)
    PROJECT_ROOT: Path = Path(__file__).parent.parent.parent
    DATA_DIR: Path = PROJECT_ROOT / "data"
    OUTPUTS_DIR: Path = PROJECT_ROOT / "outputs"
    MODELS_DIR: Path = PROJECT_ROOT / "models"
    
    # API Keys
    GROQ_API_KEY: Optional[str] = None
    FRED_API_KEY: Optional[str] = None
    
    # Agent config
    AGENT_CONFIG_PATH: Path = PROJECT_ROOT / "fx_alphalab" / "config" / "configs" / "agent_config.yaml"
    
    # Runtime
    RUN_EVERY_MINS: int = 60
    MIN_CONFIDENCE: float = 0.45
    
    class Config:
        # Look for .env in the project root
        env_file = str(Path(__file__).parent.parent.parent / ".env")
        env_file_encoding = "utf-8"
        case_sensitive = True


# Global settings instance
settings = Settings()
