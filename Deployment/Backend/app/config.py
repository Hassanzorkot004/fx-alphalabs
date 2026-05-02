"""Backend configuration settings"""

import os
from pathlib import Path
from typing import List

import yaml
from pydantic_settings import BaseSettings


class BackendSettings(BaseSettings):
    """Backend-specific settings with environment variable support"""
    
    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8080
    RELOAD: bool = False
    
    # Paths - point to fx_alphalab outputs directory
    PROJECT_ROOT: Path = Path(__file__).parent.parent
    FX_ALPHALAB_ROOT: Path = PROJECT_ROOT.parent.parent / "fx_alphalab"
    OUTPUTS_DIR: Path = FX_ALPHALAB_ROOT / "outputs"
    SIGNALS_CSV: Path = OUTPUTS_DIR / "signals.csv"
    
    # Agent scheduling
    RUN_EVERY_MINS: int = 60
    RUN_ON_STARTUP: bool = True
    
    # API Keys
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    
    # RSS Feeds - load from agent config
    RSS_FEEDS: List[str] = []
    
    # CORS - handle both string and list
    CORS_ORIGINS: List[str] = ["*"]
    
    class Config:
        env_file = ".env"
        env_prefix = "BACKEND_"
        case_sensitive = True
        extra = "ignore"
        
        @classmethod
        def parse_env_var(cls, field_name: str, raw_val: str):
            if field_name == 'CORS_ORIGINS':
                # Handle comma-separated string or single value
                if raw_val == '*':
                    return ['*']
                return [x.strip() for x in raw_val.split(',')]
            return raw_val


# Global settings instance
settings = BackendSettings()

# Load RSS feeds from agent config
AGENT_CONFIG_PATH = settings.FX_ALPHALAB_ROOT / "fx_alphalab" / "config" / "configs" / "agent_config.yaml"
if AGENT_CONFIG_PATH.exists():
    try:
        with open(AGENT_CONFIG_PATH) as f:
            _agent_cfg = yaml.safe_load(f)
        settings.RSS_FEEDS = _agent_cfg.get("news", {}).get("rss_feeds", [])
    except Exception:
        pass

# Fallback RSS feeds if config not found
if not settings.RSS_FEEDS:
    settings.RSS_FEEDS = [
        "https://feeds.content.dowjones.io/public/rss/mw_realtimeheadlines",
        "https://feeds.bbci.co.uk/news/business/rss.xml",
    ]

