"""Signal state management and CSV operations"""

import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd
from loguru import logger

from app.config import settings


class SignalStore:
    """Manages signal state and CSV file operations"""
    
    def __init__(self):
        self.last_signals: List[Dict] = []  # Latest signal per pair
        self.history: List[Dict] = []       # All active signals
        self.stats: Dict = {}
        self.lock = threading.Lock()
        
    def load_from_csv(self):
        """Load existing signals from CSV file"""
        if not settings.SIGNALS_CSV.exists():
            logger.info("No existing signals.csv found")
            return
            
        try:
            df = pd.read_csv(settings.SIGNALS_CSV)
            if df.empty:
                return
            
            logger.debug(f"load_from_csv: read {len(df)} rows from CSV")
            
            # Handle new enriched columns - fill missing with defaults
            new_cols = {
                "price_at_signal": 0.0, "atr": 0.0, "entry_low": None, "entry_high": None,
                "stop_estimate": None, "target_estimate": None,
                "yield_z": 0.0, "carry_signal": 0.0, "vix_z": 0.0,
                "regime_prob_bull": 0.33, "regime_prob_neut": 0.34, "regime_prob_bear": 0.33,
                "p_buy": 0.0, "p_sell": 0.0, "p_hold": 0.0, "model_conf": 0.0,
                "rsi14": 0.0, "macd_hist": 0.0, "bb_pos": 0.5,
                "p_bullish": 0.0, "n_articles": 0, "sent_raw": 0.0, "headlines": "[]",
            }
            for col, default in new_cols.items():
                if col not in df.columns:
                    df[col] = default
                    
            # Convert numeric columns
            numeric_cols = ["confidence", "position_size", "macro_conf", "tech_conf", "sent_conf",
                           "price_at_signal", "atr", "yield_z", "carry_signal", "vix_z",
                           "regime_prob_bull", "regime_prob_neut", "regime_prob_bear",
                           "p_buy", "p_sell", "p_hold", "model_conf",
                           "rsi14", "macd_hist", "bb_pos", "p_bullish", "sent_raw"]
            for col in numeric_cols:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)
            
            # Sort by timestamp descending
            if "timestamp" in df.columns:
                df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
                df = df.sort_values("timestamp", ascending=False)
            
            all_signals = df.to_dict(orient="records")
            logger.debug(f"load_from_csv: converted to {len(all_signals)} signal dicts")
            
            with self.lock:
                self.last_signals = self._get_latest_signals(all_signals)
                self.history = self._get_active_signals(all_signals)
                self.stats = self._compute_stats(all_signals)
                
            logger.info(
                f"Loaded {len(self.last_signals)} live signals ({[s.get('pair') for s in self.last_signals]}), "
                f"{len(self.history)} history entries from CSV"
            )
            
        except Exception as e:
            logger.error(f"Error loading signals.csv: {e}")
    
    def update(self, signals: List[Dict]):
        """Update state with new signals"""
        if not signals:
            return
        
        logger.debug(f"update() received {len(signals)} signals: {[s.get('pair') for s in signals]}")
        
        with self.lock:
            # Update in-memory state directly from incoming signals
            for s in signals:
                pair = str(s.get("pair", ""))
                # Replace latest signal for this pair
                self.last_signals = [x for x in self.last_signals 
                                      if str(x.get("pair", "")) != pair]
                self.last_signals.append(s)
            
            # Append to history if active (position_size > 0)
            for s in signals:
                if float(s.get("position_size", 0)) > 0:
                    self.history.insert(0, s)
            
            logger.debug(f"After update: last_signals has {len(self.last_signals)} signals: {[s.get('pair') for s in self.last_signals]}")
        
        logger.info(f"State updated with {len(signals)} new signals")
    
    def _get_latest_signals(self, all_signals: List[Dict]) -> List[Dict]:
        """Get the latest signal per pair"""
        seen = set()
        latest = []
        for s in all_signals:
            pair = str(s.get("pair", ""))
            if pair not in seen:
                seen.add(pair)
                latest.append(s)
            if len(seen) == 3:  # Assuming 3 pairs
                break
        return latest
    
    def _get_active_signals(self, all_signals: List[Dict]) -> List[Dict]:
        """Get signals with position_size > 0"""
        return [s for s in all_signals if float(s.get("position_size", 0)) > 0]
    
    def _compute_stats(self, all_signals: List[Dict]) -> Dict:
        """Compute performance metrics - try to load from cache first"""
        # Try to load from stats cache file
        stats_cache = settings.OUTPUTS_DIR / "stats_cache.json"
        if stats_cache.exists():
            try:
                import json
                with open(stats_cache) as f:
                    cached = json.load(f)
                    if "overall" in cached:
                        logger.info("Loaded stats from cache")
                        return cached["overall"]
            except Exception as e:
                logger.warning(f"Failed to load stats cache: {e}")
        
        # Fallback: compute basic stats from signals
        active = self._get_active_signals(all_signals)
        if not active:
            return {
                "n_trades": 0, "win_rate": 0.0, "total_pips": 0.0,
                "avg_win_pips": 0.0, "avg_loss_pips": 0.0,
                "profit_factor": 0.0, "max_drawdown_pips": 0.0, "sharpe": 0.0,
                "data_source": "no_data",
            }
        
        # Try to read pips from CSV if available
        pips_data = [float(s.get("pips", 0)) for s in active if s.get("pips") is not None]
        
        if not pips_data:
            # Return placeholder stats with clear indication
            return {
                "n_trades": len(active),
                "win_rate": 0.0,
                "total_pips": 0.0,
                "avg_win_pips": 0.0,
                "avg_loss_pips": 0.0,
                "profit_factor": 0.0,
                "max_drawdown_pips": 0.0,
                "sharpe": 0.0,
                "data_source": "pending_backtest",
            }
        
        import numpy as np
        wins = [p for p in pips_data if p > 0]
        loses = [p for p in pips_data if p <= 0]
        
        win_rate = len(wins) / len(pips_data) if pips_data else 0
        total_pips = sum(pips_data)
        avg_win = sum(wins) / len(wins) if wins else 0
        avg_loss = sum(loses) / len(loses) if loses else 0
        profit_factor = sum(wins) / abs(sum(loses)) if loses and sum(loses) != 0 else 0
        
        # Max drawdown
        cumulative = np.cumsum(pips_data)
        rolling_max = np.maximum.accumulate(cumulative)
        drawdown = cumulative - rolling_max
        max_dd = float(drawdown.min()) if len(drawdown) > 0 else 0
        
        # Sharpe approximation
        arr = np.array(pips_data)
        sharpe = float(arr.mean() / arr.std() * (24 * 252) ** 0.5) if arr.std() > 0 else 0
        
        return {
            "n_trades": len(pips_data),
            "win_rate": round(win_rate, 4),
            "total_pips": round(total_pips, 1),
            "avg_win_pips": round(avg_win, 1),
            "avg_loss_pips": round(avg_loss, 1),
            "profit_factor": round(profit_factor, 2),
            "max_drawdown_pips": round(max_dd, 2),
            "sharpe": round(sharpe, 2),
            "data_source": "live_signals",
        }
    
    def get_state(self) -> Dict:
        """Get current state (thread-safe)"""
        with self.lock:
            return {
                "signals": self.last_signals,
                "history": self.history,
                "stats": self.stats,
            }
    
    def get_latest_for_pair(self, pair: str) -> Optional[Dict]:
        """Return the most recent signal for a given pair (for AlphaBot context)."""
        with self.lock:
            for s in self.last_signals:
                if str(s.get("pair", "")).replace("=X", "") == pair.replace("=X", ""):
                    return s
        return None
    
    def get_recent_headlines(self, pair: str) -> List[str]:
        """Return headlines stored with the latest signal for a pair."""
        s = self.get_latest_for_pair(pair)
        if not s:
            return []
        raw = s.get("headlines", "[]")
        try:
            return json.loads(raw) if isinstance(raw, str) else raw
        except Exception:
            return []


# Global store instance
signal_store = SignalStore()
