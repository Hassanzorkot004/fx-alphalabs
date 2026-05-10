"""
Core agent execution logic - importable, no subprocess needed

This module extracts the business logic from run_agent.py into a reusable class
that can be imported and called directly by the backend.
"""

import csv
import json
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
from fx_alphalab.postprocessor.corrector import SignalCorrector, CorrectorConfig
from fx_alphalab.postprocessor.monitor import BalanceMonitor
from fx_alphalab.analysts.macro import run_macro_analyst
from fx_alphalab.analysts.technical import run_tech_analyst
from fx_alphalab.analysts.sentiment import run_sent_analyst
from fx_alphalab.analysts.orchestrator import run_orchestrator


def _substitute_env_vars(config: dict) -> dict:
    """
    Recursively substitute ${VAR_NAME} placeholders with environment variables.
    """
    if isinstance(config, dict):
        return {k: _substitute_env_vars(v) for k, v in config.items()}
    elif isinstance(config, list):
        return [_substitute_env_vars(item) for item in config]
    elif isinstance(config, str):
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
        self.config = self._load_config(config_path)
        self._init_agents()
        self._init_feeds()
        
    def _load_config(self, config_path: Optional[Path]) -> dict:
        """Load agent configuration from YAML with environment variable substitution"""
        path = config_path or settings.AGENT_CONFIG_PATH
        logger.debug(f"Loading config from {path}")
        with open(path) as f:
            cfg = yaml.safe_load(f)
        
        cfg = _substitute_env_vars(cfg)
        
        if "paths" in cfg:
            for key, value in cfg["paths"].items():
                if isinstance(value, str) and not Path(value).is_absolute():
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

            # Init pipeline state (corrector + balance monitor)
            pairs = self.config.get("system", {}).get("pairs", ["EURUSD", "GBPUSD", "USDJPY"])
            self.corrector = SignalCorrector("default", CorrectorConfig(
                conviction_threshold=2.5,
                session_suppress_tokyo=True,
                symmetry_window=24,
                symmetry_ratio=3.0,
            ))
            self.monitor = BalanceMonitor("default", window=48)
            self.bar_count = 0
            
            # Init RAG store for AlphaBot
            from fx_alphalab.llm.rag import AlphaBotRAG
            self.rag = AlphaBotRAG()
            
            logger.success("✓ Agents loaded successfully")
            logger.success("✓ RAG store initialized")
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
        """Run one complete analysis cycle for all pairs."""
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
                    
                    # Index signal into RAG store
                    if hasattr(self, 'rag'):
                        self.rag.index_signal(signal)
                        self.rag.index_macro_snapshot(
                            macro_features=signal.get("mac_features", {}),
                            regime=signal.get("macro_regime", "unknown"),
                            timestamp=signal.get("timestamp", ""),
                        )
            except Exception as e:
                logger.error(f"Error processing {pair}: {e}")
                continue
        
        logger.info(f"\n{'═'*60}")
        logger.info(f"  Cycle complete: {len(signals)} signals generated")
        logger.info(f"{'═'*60}\n")
        
        return signals
    
    def _process_pair(self, pair: str) -> Optional[Dict]:
        """Process a single currency pair through the 5-stage pipeline."""
        
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
        
        # Stage 1: Run specialist ML agents
        logger.info("  Running specialist agents...")
        macro_out = self.macro_agent.predict_live(price_df)
        tech_out = self.tech_agent.predict_live(price_df)
        sent_out = self.sent_agent.predict_live(nws_feats)

        # Stage 2: Conviction gate on technical
        last_row = price_df.iloc[-1].to_dict()
        tech_corrected = self.corrector.correct(tech_out, last_row)
        self.monitor.record(tech_corrected["signal"])

        # Stage 3: Macro LLM analyst
        macro_packet = run_macro_analyst(pair, macro_out)

        # Stage 4: Technical + Sentiment LLM analysts (parallel)
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            future_tech = pool.submit(run_tech_analyst, pair, tech_corrected, macro_packet)
            future_sent = pool.submit(run_sent_analyst, pair, sent_out, macro_packet)
            tech_packet = future_tech.result(timeout=10)
            sent_packet = future_sent.result(timeout=10)

        # Stage 5: Orchestrator LLM (with fallback to old orchestrator)
        try:
            signal = run_orchestrator(pair, macro_packet, tech_packet, sent_packet, headlines)
                    # Ensure required fields exist
                # Ensure required fields exist
            signal["timestamp"] = signal.get("timestamp") or datetime.now(timezone.utc).isoformat()
            signal["macro_regime"] = signal.get("macro_regime") or macro_out.get("regime_label", "unknown")
            signal["tech_signal"] = signal.get("tech_signal") or tech_out.get("signal", "HOLD")
            signal["sent_signal"] = signal.get("sent_signal") or sent_out.get("signal", "HOLD")
            signal["source"] = signal.get("source") or "llm_pipeline"
            signal["agent_agreement"] = signal.get("agent_agreement") or "partial"
        except Exception as e:
            logger.warning(f"LLM orchestrator failed: {e} — using old orchestrator")
            signal = self.orchestrator.run(
                pair=pair,
                macro_agent=self.macro_agent,
                tech_agent=self.tech_agent,
                sent_agent=self.sent_agent,
                macro_features=price_df,
                tech_df=price_df,
                sent_features=nws_feats,
                headlines=headlines,
            )

        # Embed analyst packets into signal for frontend
        signal["macro_agent"] = macro_packet.to_dict()
        signal["tech_agent"] = tech_packet.to_dict()
        signal["sent_agent"] = sent_packet.to_dict()
        signal["conviction_data"] = {
            "sell": tech_corrected["conviction_sell"],
            "buy": tech_corrected["conviction_buy"],
            "symmetry_active": tech_corrected["symmetry_gate_active"],
            "tokyo_active": tech_corrected["tokyo_gate_active"],
        }

        # Balance monitor check every 6 bars
        if self.bar_count % 6 == 0:
            health = self.monitor.check()
            if not health["healthy"]:
                for alert in health["alerts"]:
                    logger.warning(alert)
        
        logger.info(
            f"  macro={macro_out['regime_label']} "
            f"tech={tech_out['signal']} "
            f"sent={sent_out['signal']}"
        )
        
        # ── Enrichment ──
        last = price_df.iloc[-1]
        current_price = float(last["close"])
        atr_val = float(last.get("atr", 0.0))
        mac_feats = macro_out.get("mac_features", {})
        regime_probs = macro_out.get("regime_probs", {})
        
        enrichment = {
            "price_at_signal": round(current_price, 5),
            "atr":             round(atr_val, 6),
            "yield_z":         round(float(mac_feats.get("mac_yield_z", 0.0)), 4),
            "carry_signal":    round(float(mac_feats.get("pair_carry_signal", 0.0)), 4),
            "vix_z":           round(float(mac_feats.get("mac_vix_z", 0.0)), 4),
            "regime_prob_bull": round(float(regime_probs.get("bullish", 0.33)), 4),
            "regime_prob_neut": round(float(regime_probs.get("neutral", 0.34)), 4),
            "regime_prob_bear": round(float(regime_probs.get("bearish", 0.33)), 4),
            "p_buy":           round(float(tech_out.get("p_buy", 0.0)), 4),
            "p_sell":          round(float(tech_out.get("p_sell", 0.0)), 4),
            "p_hold":          round(float(tech_out.get("p_hold", 0.0)), 4),
            "model_conf":      round(float(tech_out.get("confidence", 0.0)), 4),
            "rsi14":           round(float(last.get("rsi14", 0.0)) * 100, 2),
            "macd_hist":       round(float(last.get("macd_hist", 0.0)), 8),
            "bb_pos":          round(float(last.get("bb_pos", 0.5)), 4),
            "p_bullish":       round(float(sent_out.get("p_buy", 0.5)), 4),
            "n_articles":      int(news_result.get("n_articles", 0)),
            "sent_raw":        round(float(nws_feats.get("nws_sent_signal", 0.0)), 4),
            "headlines":       json.dumps(headlines[:5]),
            "mac_features":    mac_feats,
        }
        
        signal.update(enrichment)
        signal = self._add_trade_levels(signal)
        
        # 6. Store in memory
        self.context.add(pair, signal)

        self.bar_count += 1
        
        return signal
    
    def _add_trade_levels(self, signal: Dict) -> Dict:
        """Compute entry zone, stop, target from price and ATR."""
        price = signal.get("price_at_signal", 0.0)
        atr = signal.get("atr", 0.0)
        direction = signal.get("direction", "HOLD")

        if atr == 0.0 or direction == "HOLD":
            signal.update({
                "entry_low": None, "entry_high": None,
                "stop_estimate": None, "target_estimate": None,
            })
            return signal

        entry_buffer = 0.2 * atr
        if direction == "BUY":
            signal["entry_low"]       = round(price - entry_buffer, 5)
            signal["entry_high"]      = round(price + entry_buffer, 5)
            signal["stop_estimate"]   = round(price - 1.5 * atr, 5)
            signal["target_estimate"] = round(price + 2.0 * atr, 5)
        elif direction == "SELL":
            signal["entry_low"]       = round(price - entry_buffer, 5)
            signal["entry_high"]      = round(price + entry_buffer, 5)
            signal["stop_estimate"]   = round(price + 1.5 * atr, 5)
            signal["target_estimate"] = round(price - 2.0 * atr, 5)

        return signal
    
    def _save_signal(self, signal: Dict):
        """Save signal to CSV file"""
        signals_csv = Path(self.config["paths"]["signals_csv"])
        signals_csv.parent.mkdir(parents=True, exist_ok=True)
        
        exists = signals_csv.exists()
        cols = [
            "timestamp", "pair", "direction", "confidence", "position_size",
            "macro_regime", "tech_signal", "sent_signal", "agent_agreement",
            "reasoning", "source",
            # Pipeline fields
            "key_driver", "risk_note", "headline", "narrative",
            "suppressed_by_regime",
            # Analyst packets (serialized as JSON strings for CSV)
            "macro_agent", "tech_agent", "sent_agent", "conviction_data",
            # Enriched fields
            "price_at_signal", "atr", "entry_low", "entry_high",
            "stop_estimate", "target_estimate",
            "yield_z", "carry_signal", "vix_z",
            "regime_prob_bull", "regime_prob_neut", "regime_prob_bear",
            "p_buy", "p_sell", "p_hold", "model_conf",
            "rsi14", "macd_hist", "bb_pos",
            "p_bullish", "n_articles", "sent_raw", "headlines",
        ]
        
        # Serialize nested dicts to JSON strings for CSV storage
        signal_copy = dict(signal)
        for field in ["macro_agent", "tech_agent", "sent_agent", "conviction_data"]:
            if field in signal_copy and isinstance(signal_copy[field], (dict, list)):
                signal_copy[field] = json.dumps(signal_copy[field])
        
        with open(signals_csv, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
            if not exists:
                writer.writeheader()
            writer.writerow(signal_copy)