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
    
    # API Keys
    GROQ_API_KEY: str = ""
    OLLAMA_API_KEY: str = "sk-c5aed44fb5704eec9559df32ad022483"
    OLLAMA_BASE_URL: str = "https://tokenfactory.esprit.tn/api"
    
    # RSS Feeds - load from agent config
    RSS_FEEDS: List[str] = []
    
    # CORS - comma-separated string in .env, parsed manually
    CORS_ORIGINS: List[str] = ["*"]
    
    # Trading pairs
    PAIRS: List[str] = ["EURUSD=X", "GBPUSD=X", "USDJPY=X"]
    
    class Config:
        env_file = ".env"
        env_prefix = ""
        case_sensitive = True
        extra = "ignore"

    @classmethod
    def parse_env_var(cls, field_name: str, raw_val: str):
        """Parse environment variables with special handling for lists."""
        if field_name in ('CORS_ORIGINS', 'PAIRS', 'RSS_FEEDS'):
            if raw_val == '*':
                return ['*']
            # Handle JSON arrays: ["http://a", "http://b"]
            if raw_val.strip().startswith('['):
                import json
                try:
                    return json.loads(raw_val)
                except json.JSONDecodeError:
                    pass
            # Handle comma-separated: http://a,http://b
            return [x.strip() for x in raw_val.split(',') if x.strip()]
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