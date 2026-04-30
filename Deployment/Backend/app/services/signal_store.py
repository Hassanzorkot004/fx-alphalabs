"""Signal state management and CSV operations"""

import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

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
                
            # Convert numeric columns
            for col in ["confidence", "position_size", "macro_conf", "tech_conf", "sent_conf"]:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)
            
            # Sort by timestamp descending
            if "timestamp" in df.columns:
                df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
                df = df.sort_values("timestamp", ascending=False)
            
            all_signals = df.to_dict(orient="records")
            
            with self.lock:
                self.last_signals = self._get_latest_signals(all_signals)
                self.history = self._get_active_signals(all_signals)
                self.stats = self._compute_stats(all_signals)
                
            logger.info(
                f"Loaded {len(self.last_signals)} live signals, "
                f"{len(self.history)} history entries from CSV"
            )
            
        except Exception as e:
            logger.error(f"Error loading signals.csv: {e}")
    
    def update(self, signals: List[Dict]):
        """Update state with new signals"""
        if not signals:
            return
            
        # Reload from CSV to get complete picture
        self.load_from_csv()
        
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
        """Compute performance metrics"""
        active = self._get_active_signals(all_signals)
        if not active:
            return {
                "n_trades": 0, "win_rate": 0.0, "total_pips": 0.0,
                "avg_win": 0.0, "avg_loss": 0.0,
                "profit_factor": 0.0, "max_drawdown": 0.0, "sharpe": 0.0,
            }
        
        # Try to read pips from CSV if available
        pips_data = [float(s.get("pips", 0)) for s in active if s.get("pips") is not None]
        
        if not pips_data:
            return {
                "n_trades": len(active), "win_rate": 0.0, "total_pips": 0.0,
                "avg_win": 0.0, "avg_loss": 0.0,
                "profit_factor": 0.0, "max_drawdown": 0.0, "sharpe": 0.0,
            }
        
        import numpy as np
        wins = [p for p in pips_data if p > 0]
        loses = [p for p in pips_data if p <= 0]
        
        win_rate = len(wins) / len(pips_data) if pips_data else 0
        total_pips = sum(pips_data)
        avg_win = sum(wins) / len(wins) if wins else 0
        avg_loss = sum(loses) / len(loses) if loses else 0
        profit_factor = sum(wins) / abs(sum(loses)) if loses else float("inf")
        
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
            "avg_win": round(avg_win, 1),
            "avg_loss": round(avg_loss, 1),
            "profit_factor": round(profit_factor, 2),
            "max_drawdown": round(max_dd, 2),
            "sharpe": round(sharpe, 2),
        }
    
    def get_state(self) -> Dict:
        """Get current state (thread-safe)"""
        with self.lock:
            return {
                "signals": self.last_signals,
                "history": self.history,
                "stats": self.stats,
            }


# Global store instance
signal_store = SignalStore()
