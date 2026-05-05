"""Backtest and performance analysis service"""

from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import pandas as pd
from loguru import logger

from app.config import settings


class BacktestService:
    """Analyzes historical signal performance (simulated outcomes)"""
    
    def __init__(self):
        self._cache = {}
        self._cache_time = None
        self._cache_ttl = 300  # 5 minutes
    
    def get_performance_summary(self, pair: Optional[str] = None) -> Dict:
        """
        Get overall signal performance metrics.
        
        Args:
            pair: Optional pair filter (e.g., "EURUSD"). If None, returns all pairs.
        
        Returns:
            {
                "total_signals": int,
                "winning_signals": int,
                "losing_signals": int,
                "win_rate": float,
                "total_pips": float,
                "avg_win_pips": float,
                "avg_loss_pips": float,
                "profit_factor": float,
                "max_drawdown_pips": float,
                "max_drawdown_pct": float,
                "sharpe_ratio": float,
                "best_signal_pips": float,
                "worst_signal_pips": float,
                "avg_signal_duration_hours": float,
            }
        """
        try:
            signals = self._load_and_simulate_outcomes(pair)
            
            if not signals:
                return {"error": "No signal data available"}
            
            df = pd.DataFrame(signals)
            
            # Basic counts
            total_signals = len(df)
            winning_signals = len(df[df["pips"] > 0])
            losing_signals = len(df[df["pips"] <= 0])
            
            # Win rate
            win_rate = winning_signals / total_signals if total_signals > 0 else 0
            
            # Pips metrics
            total_pips = df["pips"].sum()
            wins = df[df["pips"] > 0]["pips"]
            losses = df[df["pips"] <= 0]["pips"]
            
            avg_win_pips = wins.mean() if len(wins) > 0 else 0
            avg_loss_pips = losses.mean() if len(losses) > 0 else 0
            
            # Profit factor
            gross_profit = wins.sum() if len(wins) > 0 else 0
            gross_loss = abs(losses.sum()) if len(losses) > 0 else 0
            profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0
            
            # Drawdown
            cumulative = df["pips"].cumsum()
            running_max = cumulative.expanding().max()
            drawdown = cumulative - running_max
            max_drawdown_pips = drawdown.min()
            
            # Drawdown percentage: relative to peak equity
            # If peak is negative or zero, percentage doesn't make sense
            if running_max.max() > 0:
                max_drawdown_pct = abs(max_drawdown_pips / running_max.max() * 100)
            else:
                max_drawdown_pct = 0
            
            # Sharpe ratio (annualized, assuming 252 trading days)
            returns = df["pips"].values
            sharpe_ratio = (returns.mean() / returns.std() * np.sqrt(252)) if returns.std() > 0 else 0
            
            # Best/worst trades
            best_trade_pips = df["pips"].max()
            worst_trade_pips = df["pips"].min()
            
            # Average duration
            avg_duration = df["duration_hours"].mean() if "duration_hours" in df.columns else 0
            
            return {
                "total_signals": int(total_signals),
                "winning_signals": int(winning_signals),
                "losing_signals": int(losing_signals),
                "win_rate": round(win_rate, 4),
                "total_pips": round(total_pips, 1),
                "avg_win_pips": round(avg_win_pips, 1),
                "avg_loss_pips": round(avg_loss_pips, 1),
                "profit_factor": round(profit_factor, 2),
                "max_drawdown_pips": round(max_drawdown_pips, 1),
                "max_drawdown_pct": round(max_drawdown_pct, 1),
                "sharpe_ratio": round(sharpe_ratio, 2),
                "best_signal_pips": round(best_trade_pips, 1),
                "worst_signal_pips": round(worst_trade_pips, 1),
                "avg_signal_duration_hours": round(avg_duration, 1),
            }
            
        except Exception as e:
            logger.error(f"Performance summary failed: {e}")
            return {"error": str(e)}
    
    def get_equity_curve(self, pair: Optional[str] = None) -> Dict:
        """
        Get cumulative pips over time.
        
        Returns:
            {
                "type": "equity_curve",
                "data": [{"time": str, "cumulative_pips": float, "signal_pips": float}]
            }
        """
        try:
            signals = self._load_and_simulate_outcomes(pair)
            
            if not signals:
                return {"error": "No signal data available"}
            
            df = pd.DataFrame(signals)
            df = df.sort_values("timestamp")
            
            # Calculate cumulative pips
            df["cumulative_pips"] = df["pips"].cumsum()
            
            data = [
                {
                    "time": row["timestamp"].isoformat() if isinstance(row["timestamp"], datetime) else row["timestamp"],
                    "cumulative_pips": round(row["cumulative_pips"], 1),
                    "signal_pips": round(row["pips"], 1),
                    "pair": row["pair"],
                    "direction": row["direction"],
                }
                for _, row in df.iterrows()
            ]
            
            return {
                "type": "equity_curve",
                "data": data,
                "pair_filter": pair,
            }
            
        except Exception as e:
            logger.error(f"Equity curve generation failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {"error": str(e)}
    
    def get_drawdown_curve(self, pair: Optional[str] = None) -> Dict:
        """
        Get drawdown over time.
        
        Returns:
            {
                "type": "drawdown_curve",
                "data": [{"time": str, "drawdown_pips": float, "drawdown_pct": float}]
            }
        """
        try:
            signals = self._load_and_simulate_outcomes(pair)
            
            if not signals:
                return {"error": "No signal data available"}
            
            df = pd.DataFrame(signals)
            df = df.sort_values("timestamp")
            
            # Calculate drawdown
            df["cumulative_pips"] = df["pips"].cumsum()
            df["running_max"] = df["cumulative_pips"].expanding().max()
            df["drawdown_pips"] = df["cumulative_pips"] - df["running_max"]
            df["drawdown_pct"] = (df["drawdown_pips"] / df["running_max"] * 100).fillna(0)
            
            data = [
                {
                    "time": row["timestamp"].isoformat() if isinstance(row["timestamp"], datetime) else row["timestamp"],
                    "drawdown_pips": round(row["drawdown_pips"], 1),
                    "drawdown_pct": round(row["drawdown_pct"], 2),
                }
                for _, row in df.iterrows()
            ]
            
            return {
                "type": "drawdown_curve",
                "data": data,
                "pair_filter": pair,
            }
            
        except Exception as e:
            logger.error(f"Drawdown curve generation failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {"error": str(e)}
    
    def get_pair_comparison(self) -> Dict:
        """
        Compare signal performance across all pairs.
        
        Returns:
            {
                "type": "pair_comparison",
                "pairs": [
                    {
                        "pair": str,
                        "total_signals": int,
                        "win_rate": float,
                        "total_pips": float,
                        "profit_factor": float,
                        "sharpe_ratio": float,
                    }
                ]
            }
        """
        try:
            signals = self._load_and_simulate_outcomes()
            
            if not signals:
                return {"error": "No signal data available"}
            
            df = pd.DataFrame(signals)
            
            pairs_data = []
            for pair in df["pair"].unique():
                pair_df = df[df["pair"] == pair]
                
                total_signals = len(pair_df)
                winning_signals = len(pair_df[pair_df["pips"] > 0])
                win_rate = winning_signals / total_signals if total_signals > 0 else 0
                total_pips = pair_df["pips"].sum()
                
                wins = pair_df[pair_df["pips"] > 0]["pips"]
                losses = pair_df[pair_df["pips"] <= 0]["pips"]
                gross_profit = wins.sum() if len(wins) > 0 else 0
                gross_loss = abs(losses.sum()) if len(losses) > 0 else 0
                profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0
                
                returns = pair_df["pips"].values
                sharpe_ratio = (returns.mean() / returns.std() * np.sqrt(252)) if returns.std() > 0 else 0
                
                pairs_data.append({
                    "pair": pair.replace("=X", ""),
                    "total_signals": int(total_signals),
                    "win_rate": round(win_rate, 4),
                    "total_pips": round(total_pips, 1),
                    "profit_factor": round(profit_factor, 2),
                    "sharpe_ratio": round(sharpe_ratio, 2),
                })
            
            # Sort by total pips descending
            pairs_data.sort(key=lambda x: x["total_pips"], reverse=True)
            
            return {
                "type": "pair_comparison",
                "pairs": pairs_data,
            }
            
        except Exception as e:
            logger.error(f"Pair comparison failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {"error": str(e)}
    
    def get_recent_signals(self, limit: int = 20, pair: Optional[str] = None) -> Dict:
        """
        Get recent signals with simulated outcomes.
        
        Returns:
            {
                "type": "recent_signals",
                "signals": [
                    {
                        "timestamp": str,
                        "pair": str,
                        "direction": str,
                        "entry": float,
                        "exit": float,
                        "pips": float,
                        "outcome": "win" | "loss",
                    }
                ]
            }
        """
        try:
            signals = self._load_and_simulate_outcomes(pair)
            
            if not signals:
                return {"error": "No signal data available"}
            
            df = pd.DataFrame(signals)
            df = df.sort_values("timestamp", ascending=False).head(limit)
            
            signals_data = [
                {
                    "timestamp": row["timestamp"].isoformat() if isinstance(row["timestamp"], datetime) else row["timestamp"],
                    "pair": row["pair"].replace("=X", ""),
                    "direction": row["direction"],
                    "entry": round(row["entry"], 5),
                    "exit": round(row["exit"], 5),
                    "pips": round(row["pips"], 1),
                    "outcome": "win" if row["pips"] > 0 else "loss",
                    "confidence": row.get("confidence", 0),
                }
                for _, row in df.iterrows()
            ]
            
            return {
                "type": "recent_signals",
                "signals": signals_data,
            }
            
        except Exception as e:
            logger.error(f"Recent signals failed: {e}")
            return {"error": str(e)}
    
    def _load_and_simulate_outcomes(self, pair: Optional[str] = None) -> List[Dict]:
        """
        Load signals from CSV and simulate their outcomes.
        
        This simulates "what if you followed this signal":
        - Entry: entry_low or entry_high (depending on direction)
        - Exit: stop_estimate (loss) or target_estimate (win)
        - Outcome: Based on confidence (>0.5 = likely hit target)
        - Pips: difference * pip_multiplier
        
        NOTE: These are SIMULATED outcomes, not actual trades.
        """
        try:
            if not settings.SIGNALS_CSV.exists():
                logger.warning("No signals.csv found")
                return []
            
            df = pd.read_csv(settings.SIGNALS_CSV)
            
            if df.empty:
                return []
            
            # Filter by pair if specified
            if pair:
                clean_pair = pair.replace("=X", "")
                df = df[df["pair"].str.replace("=X", "") == clean_pair]
            
            # Only process signals with entry/stop/target data
            df = df.dropna(subset=["entry_low", "entry_high", "stop_estimate", "target_estimate"])
            
            if df.empty:
                return []
            
            simulated_signals = []
            
            for _, row in df.iterrows():
                direction = row.get("direction", "HOLD")
                
                if direction == "HOLD":
                    continue
                
                # Determine entry price
                if direction == "BUY":
                    entry = row["entry_low"]
                    stop = row["stop_estimate"]
                    target = row["target_estimate"]
                else:  # SELL
                    entry = row["entry_high"]
                    stop = row["stop_estimate"]
                    target = row["target_estimate"]
                
                # Simulate outcome (simplified: assume 60% hit target, 40% hit stop based on confidence)
                confidence = row.get("confidence", 0.5)
                
                # Higher confidence = more likely to hit target
                hit_target = confidence > 0.5
                
                if hit_target:
                    exit_price = target
                else:
                    exit_price = stop
                
                # Calculate pips (JPY pairs use 100 multiplier, others use 10000)
                pair_name = row["pair"]
                pip_multiplier = 100 if "JPY" in pair_name else 10000
                
                if direction == "BUY":
                    pips = (exit_price - entry) * pip_multiplier
                else:  # SELL
                    pips = (entry - exit_price) * pip_multiplier
                
                # Estimate duration (simplified: 12-48 hours)
                duration_hours = np.random.uniform(12, 48)
                
                simulated_signals.append({
                    "timestamp": pd.to_datetime(row["timestamp"], utc=True),
                    "pair": row["pair"],
                    "direction": direction,
                    "entry": entry,
                    "exit": exit_price,
                    "stop": stop,
                    "target": target,
                    "pips": pips,
                    "confidence": confidence,
                    "duration_hours": duration_hours,
                })
            
            return simulated_signals
            
        except Exception as e:
            logger.error(f"Failed to load and simulate signal outcomes: {e}")
            return []


# Global service instance
backtest_service = BacktestService()
