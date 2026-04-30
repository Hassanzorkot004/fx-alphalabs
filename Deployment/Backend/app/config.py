"""Backend configuration settings"""

from pathlib import Path
from typing import List
from pydantic_settings import BaseSettings


class BackendSettings(BaseSettings):
    """Backend-specific settings with environment variable support"""
    
    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 5001
    RELOAD: bool = False
    
    # Paths - point to fx_alphalab outputs directory
    PROJECT_ROOT: Path = Path(__file__).parent.parent
    FX_ALPHALAB_ROOT: Path = PROJECT_ROOT.parent.parent / "fx_alphalab"
    OUTPUTS_DIR: Path = FX_ALPHALAB_ROOT / "outputs"
    SIGNALS_CSV: Path = OUTPUTS_DIR / "signals.csv"
    
    # Agent scheduling
    RUN_EVERY_MINS: int = 60
    RUN_ON_STARTUP: bool = True
    
    # CORS
    CORS_ORIGINS: List[str] = ["*"]
    
    class Config:
        env_file = ".env"
        env_prefix = "BACKEND_"
        case_sensitive = True
        extra = "ignore"  # Allow extra env vars (like GROQ_API_KEY, FRED_API_KEY)


# Global settings instance
settings = BackendSettings()
