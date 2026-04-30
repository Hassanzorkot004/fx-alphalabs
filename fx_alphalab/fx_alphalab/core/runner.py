"""
Core agent execution logic - importable, no subprocess needed

This module extracts the business logic from run_agent.py into a reusable class
that can be imported and called directly by the backend.
"""

import csv
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

import yaml
from loguru import logger

from fx_alphalab.agents import MacroAgent, TechnicalAgent, SentimentAgent
from fx_alphalab.data_feed import PriceFeed, MacroFeed, NewsFeed
from fx_alphalab.memory import ContextStore
from fx_alphalab.orchestrator import Orchestrator
from fx_alphalab.config import settings


def _substitute_env_vars(config: dict) -> dict:
    """
    Recursively substitute ${VAR_NAME} placeholders with environment variables.
    
    Args:
        config: Configuration dictionary
        
    Returns:
        Configuration with environment variables substituted
    """
    if isinstance(config, dict):
        return {k: _substitute_env_vars(v) for k, v in config.items()}
    elif isinstance(config, list):
        return [_substitute_env_vars(item) for item in config]
    elif isinstance(config, str):
        # Match ${VAR_NAME} pattern
        pattern = r'\$\{([^}]+)\}'
        matches = re.findall(pattern, config)
        for var_name in matches:
            env_value = os.getenv(var_name, '')
            if not env_value:
                logger.warning(f"Environment variable {var_name} not set")
            config = config.replace(f'${{{var_name}}}', env_value)
        return config
    else:
        return config


class AgentRunner:
    """Manages agent lifecycle and execution"""
    
    def __init__(self, config_path: Optional[Path] = None):
        """
        Initialize the agent runner.
        
        Args:
            config_path: Path to agent_config.yaml (uses default if None)
        """
        self.config = self._load_config(config_path)
        self._init_agents()
        self._init_feeds()
        
    def _load_config(self, config_path: Optional[Path]) -> dict:
        """Load agent configuration from YAML with environment variable substitution"""
        path = config_path or settings.AGENT_CONFIG_PATH
        logger.debug(f"Loading config from {path}")
        with open(path) as f:
            cfg = yaml.safe_load(f)
        
        # Substitute environment variables
        cfg = _substitute_env_vars(cfg)
        
        # Convert relative paths to absolute paths (relative to fx_alphalab package root)
        if "paths" in cfg:
            for key, value in cfg["paths"].items():
                if isinstance(value, str) and not Path(value).is_absolute():
                    # Make path absolute relative to fx_alphalab root
                    cfg["paths"][key] = str(settings.PROJECT_ROOT / value)
        
        return cfg
    
    def _init_agents(self):
        """Load trained agents from disk"""
        logger.info("Loading trained agents...")
        try:
            self.macro_agent = MacroAgent(self.config).load()
            self.tech_agent = TechnicalAgent(self.config).load()
            self.sent_agent = SentimentAgent(self.config).load()
            self.orchestrator = Orchestrator(self.config)
            logger.success("✓ Agents loaded successfully")
        except FileNotFoundError as e:
            logger.error(f"Model files not found: {e}")
            logger.error("Run training first: fx-train or python scripts/train_agents.py")
            raise
        
    def _init_feeds(self):
        """Initialize data feeds"""
        self.price_feed = PriceFeed(self.config)
        self.macro_feed = MacroFeed(self.config)
        self.news_feed = NewsFeed(self.config)
        
        context_path = settings.OUTPUTS_DIR / "context.json"
        self.context = ContextStore(path=str(context_path))
    
    def run_cycle(self, pairs: Optional[List[str]] = None) -> List[Dict]:
        """
        Run one complete analysis cycle for all pairs.
        
        Args:
            pairs: List of currency pairs to analyze (uses config default if None)
            
        Returns:
            List of signal dictionaries
        """
        pairs = pairs or self.config["system"]["pairs"]
        signals = []
        
        logger.info(f"\n{'═'*60}")
        logger.info(f"  Cycle start: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
        logger.info(f"{'═'*60}")
        
        for pair in pairs:
            logger.info(f"\n  ── {pair} ──")
            
            try:
                signal = self._process_pair(pair)
                if signal:
                    signals.append(signal)
                    self._save_signal(signal)
            except Exception as e:
                logger.error(f"Error processing {pair}: {e}")
                continue
        
        logger.info(f"\n{'═'*60}")
        logger.info(f"  Cycle complete: {len(signals)} signals generated")
        logger.info(f"{'═'*60}\n")
        
        return signals
    
    def _process_pair(self, pair: str) -> Optional[Dict]:
        """Process a single currency pair"""
        
        # 1. Fetch price data
        price_df = self.price_feed.fetch(pair)
        if price_df is None or len(price_df) < 50:
            logger.warning(f"  Insufficient price data for {pair} — skipping")
            return None
        
        # 2. Fetch and merge macro data
        macro_df = self.macro_feed.fetch(price_df["timestamp_utc"], pair=pair)
        for col in macro_df.columns:
            price_df[col] = macro_df[col].values
        
        # 3. Fetch news data
        news_result = self.news_feed.fetch(pair)
        headlines = news_result["headlines"]
        nws_feats = news_result["nws_features"]
        
        # 4. Run specialist agents
        logger.info("  Running specialist agents...")
        macro_out = self.macro_agent.predict_live(price_df)
        tech_out = self.tech_agent.predict_live(price_df)
        sent_out = self.sent_agent.predict_live(nws_feats)
        
        logger.info(
            f"  macro={macro_out['regime_label']} "
            f"tech={tech_out['signal']} "
            f"sent={sent_out['signal']}"
        )
        
        # 5. LLM orchestrator
        logger.info("  LLM orchestrator reasoning...")
        signal = self.orchestrator.run(pair, macro_out, tech_out, sent_out, headlines)
        
        # 6. Store in memory
        self.context.add(pair, signal)
        
        return signal
    
    def _save_signal(self, signal: Dict):
        """Save signal to CSV file"""
        signals_csv = Path(self.config["paths"]["signals_csv"])
        signals_csv.parent.mkdir(parents=True, exist_ok=True)
        
        exists = signals_csv.exists()
        cols = [
            "timestamp", "pair", "direction", "confidence",
            "position_size", "macro_regime", "tech_signal", "sent_signal",
            "agent_agreement", "reasoning", "source",
        ]
        
        with open(signals_csv, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
            if not exists:
                writer.writeheader()
            writer.writerow(signal)
