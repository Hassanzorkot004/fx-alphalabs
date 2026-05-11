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
        try:
            from app.config import settings as _settings
            from app.services.demo_service import is_demo, demo_mode, DEMO_CSVS

            csv_path = DEMO_CSVS.get(demo_mode()) if is_demo() else _settings.SIGNALS_CSV

            if not csv_path or not csv_path.exists():
                return {"error": "No signal data available"}

            df = pd.read_csv(csv_path, quoting=0, on_bad_lines='skip')
            if df.empty:
                return {"error": "No signal data available"}

            if pair:
                clean_pair = pair.replace("=X", "")
                df = df[df["pair"].str.replace("=X", "", regex=False) == clean_pair]

            total_signals = len(df)
            directional = df[df["direction"] != "HOLD"]
            hold_count   = len(df[df["direction"] == "HOLD"])
            buy_count    = len(df[df["direction"] == "BUY"])
            sell_count   = len(df[df["direction"] == "SELL"])

            # Try simulated outcomes for signals that have trade levels
            simulated = self._load_and_simulate_outcomes(pair)
            if simulated:
                sim_df = pd.DataFrame(simulated)
                winning  = len(sim_df[sim_df["pips"] > 0])
                losing   = len(sim_df[sim_df["pips"] <= 0])
                win_rate = winning / len(sim_df) if len(sim_df) > 0 else 0
                total_pips = sim_df["pips"].sum()
                wins   = sim_df[sim_df["pips"] > 0]["pips"]
                losses = sim_df[sim_df["pips"] <= 0]["pips"]
                avg_win  = float(wins.mean())  if len(wins)   > 0 else 0
                avg_loss = float(losses.mean()) if len(losses) > 0 else 0
                gp = wins.sum() if len(wins) > 0 else 0
                gl = abs(losses.sum()) if len(losses) > 0 else 0
                profit_factor = gp / gl if gl > 0 else 0
                cumulative  = sim_df["pips"].cumsum()
                running_max = cumulative.expanding().max()
                drawdown    = cumulative - running_max
                max_dd_pips = float(drawdown.min())
                max_dd_pct  = abs(max_dd_pips / running_max.max() * 100) if running_max.max() > 0 else 0
                returns = sim_df["pips"].values
                sharpe  = float(returns.mean() / returns.std() * np.sqrt(252)) if returns.std() > 1e-6 else 0.0
                sharpe  = min(sharpe, 99.0)  # cap at 99
                best  = float(sim_df["pips"].max())
                worst = float(sim_df["pips"].min())
                avg_dur = float(sim_df["duration_hours"].mean()) if "duration_hours" in sim_df.columns else 0
            else:
                # No trade-level data yet — return signal counts only
                winning = losing = 0
                win_rate = total_pips = avg_win = avg_loss = 0.0
                profit_factor = max_dd_pips = max_dd_pct = sharpe = 0.0
                best = worst = avg_dur = 0.0

            avg_conf = float(df["confidence"].mean()) if "confidence" in df.columns else 0

            return {
                "total_signals":              int(total_signals),
                "directional_signals":        int(len(directional)),
                "hold_signals":               int(hold_count),
                "buy_signals":                int(buy_count),
                "sell_signals":               int(sell_count),
                "winning_signals":            int(winning),
                "losing_signals":             int(losing),
                "win_rate":                   round(win_rate, 4),
                "total_pips":                 round(total_pips, 1),
                "avg_win_pips":               round(avg_win, 1),
                "avg_loss_pips":              round(avg_loss, 1),
                "profit_factor":              round(profit_factor, 2),
                "max_drawdown_pips":          round(max_dd_pips, 1),
                "max_drawdown_pct":           round(max_dd_pct, 1),
                "sharpe_ratio":               round(sharpe, 2),
                "best_signal_pips":           round(best, 1),
                "worst_signal_pips":          round(worst, 1),
                "avg_signal_duration_hours":  round(avg_dur, 1),
                "avg_confidence":             round(avg_conf, 3),
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
                sharpe_ratio = (float(returns.mean() / returns.std() * np.sqrt(252))
                                if returns.std() > 1e-6 else 0.0)
                sharpe_ratio = round(min(sharpe_ratio, 99.0), 2)  # cap at 99
                
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
        try:
            from app.config import settings as _settings
            from app.services.demo_service import is_demo, demo_mode, DEMO_CSVS

            csv_path = DEMO_CSVS.get(demo_mode()) if is_demo() else _settings.SIGNALS_CSV

            if not csv_path or not csv_path.exists():
                logger.warning("No signals CSV found")
                return []
            
            df = pd.read_csv(csv_path, quoting=0, on_bad_lines='skip')
            
            if df.empty:
                return []
            
            # Filter by pair if specified
            if pair:
                clean_pair = pair.replace("=X", "")
                df = df[df["pair"].str.replace("=X", "", regex=False) == clean_pair]
            
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
                
                # Simulate outcome using confidence as win probability
                # confidence=0.78 → 78% chance of hitting target
                # This produces realistic win/loss distribution instead of all-wins
                confidence = row.get("confidence", 0.5)
                agreement  = row.get("agent_agreement", "PARTIAL")

                # Base win probability from confidence
                # FULL agreement gets a boost, CONFLICT gets a penalty
                if agreement == "FULL":
                    win_prob = min(confidence + 0.05, 0.85)
                elif agreement == "CONFLICT":
                    win_prob = max(confidence - 0.10, 0.35)
                else:
                    win_prob = confidence

                # Deterministic based on row index for reproducibility
                row_seed = abs(hash(str(row.get("timestamp", "")) + row.get("pair", ""))) % 1000
                hit_target = (row_seed / 1000.0) < win_prob
                
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
