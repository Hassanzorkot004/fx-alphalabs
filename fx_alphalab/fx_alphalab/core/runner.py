"""
core/runner.py
────────────────────────────────────────────────────────────────────────────
5-Stage Hybrid Pipeline — AgentRunner

PIPELINE:
  Stage 1: MacroAgent.predict_live()     → regime + mac_features
  Stage 2: TechnicalAgent.predict_live() → direction + probabilities
           (receives macro context for regime-aware inference)
  Stage 3: SentimentAgent.predict_live() → sentiment + probabilities
           (receives macro context for regime-aware calibration)
  Stage 4: ConvictionGate.evaluate()     → final direction + confidence
  Stage 5: Orchestrator.run()            → per-agent analyst text + reasoning
           (uses RAG-retrieved headlines instead of raw RSS)
"""
from __future__ import annotations

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
from fx_alphalab.agents.conviction_gate import ConvictionGate
from fx_alphalab.data_feed import PriceFeed, MacroFeed, NewsFeed
from fx_alphalab.data_feed.news_rag import NewsRAG
from fx_alphalab.memory import ContextStore
from fx_alphalab.orchestrator import Orchestrator
from fx_alphalab.postprocessor.monitor import BalanceMonitor
from fx_alphalab.config import settings


def _substitute_env_vars(config: dict) -> dict:
    if isinstance(config, dict):
        return {k: _substitute_env_vars(v) for k, v in config.items()}
    elif isinstance(config, list):
        return [_substitute_env_vars(item) for item in config]
    elif isinstance(config, str):
        pattern = r'\$\{([^}]+)\}'
        for var_name in re.findall(pattern, config):
            env_value = os.getenv(var_name, '')
            if not env_value:
                logger.warning(f"Environment variable {var_name} not set")
            config = config.replace(f'${{{var_name}}}', env_value)
        return config
    return config


class AgentRunner:
    """Manages the 5-stage pipeline lifecycle and execution."""

    def __init__(self, config_path: Optional[Path] = None):
        self.config = self._load_config(config_path)
        self._init_agents()
        self._init_feeds()

    def _load_config(self, config_path: Optional[Path]) -> dict:
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
        logger.info("Loading trained agents (5-stage pipeline) …")
        try:
            self.macro_agent    = MacroAgent(self.config).load()
            self.tech_agent     = TechnicalAgent(self.config).load()
            self.sent_agent     = SentimentAgent(self.config).load()
            min_conf            = self.config["signal"].get("min_confidence", 0.50)
            self.conviction     = ConvictionGate(min_confidence=min_conf)
            self.orchestrator   = Orchestrator(self.config)
            logger.success("✓ All 5 pipeline stages initialized")
        except FileNotFoundError as e:
            logger.error(f"Model files not found: {e}")
            logger.error("Run training first: python train_v4.py")
            raise

    def _init_feeds(self):
        self.price_feed = PriceFeed(self.config)
        self.macro_feed = MacroFeed(self.config)
        self.news_feed  = NewsFeed(self.config)
        self.news_rag   = NewsRAG()

        # Per-pair balance monitors — alert when signal distribution skews
        pairs = [p.replace("=X", "") for p in self.config["system"]["pairs"]]
        self._monitors = {pair: BalanceMonitor(pair) for pair in pairs}

        context_path = settings.OUTPUTS_DIR / "context.json"
        self.context = ContextStore(path=str(context_path))

    # ── Cycle ─────────────────────────────────────────────────────────────────

    def run_cycle(self, pairs: Optional[List[str]] = None) -> List[Dict]:
        pairs   = pairs or self.config["system"]["pairs"]
        signals = []

        logger.info(f"\n{'═'*60}")
        logger.info(f"  Cycle: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
        logger.info(f"{'═'*60}")

        for pair in pairs:
            logger.info(f"\n  ── {pair} ──")
            try:
                signal = self._process_pair(pair)
                if signal:
                    signals.append(signal)
                    self._save_signal(signal)
            except Exception as e:
                logger.error(f"Error processing {pair}: {e}", exc_info=True)

        logger.info(f"\n{'═'*60}")
        logger.info(f"  Cycle complete: {len(signals)} signals")
        logger.info(f"{'═'*60}\n")
        return signals

    def run_technical_only(self, pairs: Optional[List[str]] = None) -> List[Dict]:
        """Fast 15-min cycle: technical agent only, no macro/sentiment re-fetch."""
        pairs   = pairs or self.config["system"]["pairs"]
        signals = []
        for pair in pairs:
            try:
                price_df = self.price_feed.fetch(pair)
                if price_df is None or len(price_df) < 50:
                    continue
                tech_out = self.tech_agent.predict_live(price_df)
                signals.append({"pair": pair, "tech_signal": tech_out.get("signal"), **tech_out})
            except Exception as e:
                logger.error(f"Tech-only error [{pair}]: {e}")
        return signals

    # ── Single pair processing ────────────────────────────────────────────────

    def _process_pair(self, pair: str) -> Optional[Dict]:

        # ── Fetch data ────────────────────────────────────────────────────────
        price_df = self.price_feed.fetch(pair)
        if price_df is None or len(price_df) < 50:
            logger.warning(f"  Insufficient price data for {pair}")
            return None

        macro_df = self.macro_feed.fetch(price_df["timestamp_utc"], pair=pair)
        for col in macro_df.columns:
            price_df[col] = macro_df[col].values

        news_result = self.news_feed.fetch(pair)
        nws_feats   = news_result["nws_features"]
        raw_articles = self.news_feed._get_cached_articles()

        # Ingest articles into RAG store
        self.news_rag.ingest(raw_articles)

        # ── Stage 1: Macro ────────────────────────────────────────────────────
        logger.info("  Stage 1: MacroAgent …")
        macro_out = self.macro_agent.predict_live(price_df)
        logger.info(f"    regime={macro_out['regime_label']} conf={macro_out['regime_conf']:.2f}")

        # ── Stage 2: Technical (receives macro context) ───────────────────────
        logger.info("  Stage 2: TechnicalAgent …")
        # Inject macro regime as context features into price_df for the model
        price_df = self._inject_macro_context(price_df, macro_out)
        tech_out = self.tech_agent.predict_live(price_df)
        logger.info(
            f"    signal={tech_out['signal']} "
            f"p_buy={tech_out['p_buy']:.3f} p_sell={tech_out['p_sell']:.3f} "
            f"conf={tech_out['confidence']:.3f}"
        )

        # ── Stage 3: Sentiment (receives macro context) ───────────────────────
        logger.info("  Stage 3: SentimentAgent …")
        sent_out = self.sent_agent.predict_live(nws_feats, macro_context=macro_out)
        logger.info(f"    signal={sent_out['signal']} conf={sent_out['confidence']:.3f}")

        # ── Stage 4: Conviction Gate ──────────────────────────────────────────
        logger.info("  Stage 4: ConvictionGate …")
        conviction = self.conviction.evaluate(macro_out, tech_out, sent_out)
        logger.info(
            f"    direction={conviction['direction']} "
            f"conf={conviction['confidence']:.3f} "
            f"agree={conviction['agreement']}"
        )

        # ── RAG: retrieve relevant headlines for this signal context ──────────
        rag_query  = self._build_rag_query(pair, conviction, macro_out, tech_out)
        headlines  = self.news_rag.retrieve(pair, rag_query, top_k=5)
        if not headlines:
            headlines = news_result["headlines"]   # fallback to raw RSS
        logger.debug(f"  RAG: {len(headlines)} headlines retrieved")

        # ── Stage 5: Orchestrator (per-agent LLM + final reasoning) ──────────
        logger.info("  Stage 5: Orchestrator (LLM) …")
        last_bar = price_df.iloc[-1].to_dict()
        signal   = self.orchestrator.run(
            pair, macro_out, tech_out, sent_out,
            headlines, conviction, last_bar,
        )

        # ── Enrich with raw feature values ───────────────────────────────────
        signal.update(self._build_enrichment(price_df, macro_out, tech_out, sent_out, news_result))
        signal = self._add_trade_levels(signal)

        self.context.add(pair, signal)

        # Record signal in balance monitor and check for skew
        pair_key = pair.replace("=X", "")
        if pair_key not in self._monitors:
            self._monitors[pair_key] = BalanceMonitor(pair_key)
        self._monitors[pair_key].record(
            "BUY"  if signal.get("direction") == 1
            else "SELL" if signal.get("direction") == -1
            else "HOLD"
        )
        health = self._monitors[pair_key].check()
        for alert in health.get("alerts", []):
            logger.warning(alert)

        return signal

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _inject_macro_context(price_df, macro_out: Dict):
        """
        Add macro regime context columns to price_df so the TechnicalAgent
        can optionally use them (they're in FEATURE_COLS if the model was
        trained with them; otherwise they're ignored by the scaler).
        """
        regime = macro_out.get("regime_label", "neutral")
        feats  = macro_out.get("mac_features", {})
        price_df = price_df.copy()
        price_df["ctx_regime_bearish"] = 1.0 if regime == "bearish" else 0.0
        price_df["ctx_regime_bullish"] = 1.0 if regime == "bullish" else 0.0
        price_df["ctx_vix_z"]          = float(feats.get("mac_vix_z", 0.0))
        return price_df

    @staticmethod
    def _build_rag_query(pair: str, conviction: Dict,
                         macro_out: Dict, tech_out: Dict) -> str:
        """Build a semantic query string for RAG retrieval."""
        pair_clean = pair.replace("=X", "")
        direction  = conviction.get("direction", "HOLD")
        regime     = macro_out.get("regime_label", "neutral")
        tech_sig   = tech_out.get("signal", "HOLD")
        feats      = macro_out.get("mac_features", {})
        yield_z    = feats.get("mac_yield_z", 0.0)
        vix_z      = feats.get("mac_vix_z", 0.0)

        return (
            f"{pair_clean} {direction} signal {regime} macro regime "
            f"yield curve {'steepening' if yield_z > 0 else 'flattening'} "
            f"{'risk-off VIX elevated' if vix_z > 0.5 else 'risk-on'} "
            f"technical {tech_sig} central bank interest rate"
        )

    @staticmethod
    def _build_enrichment(price_df, macro_out, tech_out, sent_out, news_result) -> Dict:
        last         = price_df.iloc[-1]
        mac_feats    = macro_out.get("mac_features", {})
        regime_probs = macro_out.get("regime_probs", {})
        return {
            "price_at_signal":  round(float(last["close"]), 5),
            "atr":              round(float(last.get("atr", 0.0)), 6),
            "yield_z":          round(float(mac_feats.get("mac_yield_z", 0.0)), 4),
            "carry_signal":     round(float(mac_feats.get("pair_carry_signal", 0.0)), 4),
            "vix_z":            round(float(mac_feats.get("mac_vix_z", 0.0)), 4),
            "regime_prob_bull": round(float(regime_probs.get("bullish", 0.33)), 4),
            "regime_prob_neut": round(float(regime_probs.get("neutral", 0.34)), 4),
            "regime_prob_bear": round(float(regime_probs.get("bearish", 0.33)), 4),
            "p_buy":            round(float(tech_out.get("p_buy", 0.0)), 4),
            "p_sell":           round(float(tech_out.get("p_sell", 0.0)), 4),
            "p_hold":           round(float(tech_out.get("p_hold", 0.0)), 4),
            "model_conf":       round(float(tech_out.get("confidence", 0.0)), 4),
            "rsi14":            round(float(last.get("rsi14", 0.0)) * 100, 2),
            "macd_hist":        round(float(last.get("macd_hist", 0.0)), 8),
            "bb_pos":           round(float(last.get("bb_pos", 0.5)), 4),
            "p_bullish":        round(float(sent_out.get("p_buy", 0.5)), 4),
            "n_articles":       int(news_result.get("n_articles", 0)),
            "sent_raw":         round(float(news_result["nws_features"].get("nws_sent_signal", 0.0)), 4),
            "headlines":        json.dumps(news_result.get("headlines", [])[:5]),
        }

    @staticmethod
    def _add_trade_levels(signal: Dict) -> Dict:
        price     = signal.get("price_at_signal", 0.0)
        atr       = signal.get("atr", 0.0)
        direction = signal.get("direction", "HOLD")

        if atr == 0.0 or direction == "HOLD":
            signal.update({
                "entry_low": None, "entry_high": None,
                "stop_estimate": None, "target_estimate": None,
            })
            return signal

        buf = 0.2 * atr
        if direction == "BUY":
            signal["entry_low"]       = round(price - buf, 5)
            signal["entry_high"]      = round(price + buf, 5)
            signal["stop_estimate"]   = round(price - 1.5 * atr, 5)
            signal["target_estimate"] = round(price + 2.0 * atr, 5)
        else:
            signal["entry_low"]       = round(price - buf, 5)
            signal["entry_high"]      = round(price + buf, 5)
            signal["stop_estimate"]   = round(price + 1.5 * atr, 5)
            signal["target_estimate"] = round(price - 2.0 * atr, 5)
        return signal

    def _save_signal(self, signal: Dict):
        signals_csv = Path(self.config["paths"]["signals_csv"])
        signals_csv.parent.mkdir(parents=True, exist_ok=True)
        exists = signals_csv.exists()
        cols = [
            "timestamp", "pair", "direction", "confidence", "position_size",
            "macro_regime", "macro_regime_raw", "tech_signal", "sent_signal", "agent_agreement",
            "reasoning", "key_driver", "risk_note", "source",
            "macro_conf", "tech_conf", "sent_conf",
            "macro_analyst", "macro_key_feat", "macro_override",
            "tech_analyst",  "tech_key_feat",  "tech_override",
            "sent_analyst",  "sent_key_feat",  "sent_override",
            "price_at_signal", "atr", "entry_low", "entry_high",
            "stop_estimate", "target_estimate",
            "yield_z", "carry_signal", "vix_z",
            "regime_prob_bull", "regime_prob_neut", "regime_prob_bear",
            "p_buy", "p_sell", "p_hold", "model_conf",
            "rsi14", "macd_hist", "bb_pos",
            "p_bullish", "n_articles", "sent_raw", "headlines",
        ]
        with open(signals_csv, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore",
                                    quoting=csv.QUOTE_ALL)
            if not exists:
                writer.writeheader()
            writer.writerow(signal)
