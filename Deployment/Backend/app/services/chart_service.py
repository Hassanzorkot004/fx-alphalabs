"""Chart data service - provides structured data for frontend chart rendering"""

from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

import numpy as np
import pandas as pd
import yfinance as yf
from loguru import logger

from app.services.signal_store import signal_store


class ChartService:
    """Generates chart data for various visualizations"""
    
    def __init__(self):
        self._cache = {}
        self._cache_ttl = 300  # 5 minutes
    
    def get_price_chart(self, pair: str, period: str = "24h") -> Dict:
        """
        Get OHLC price data with signal overlays.
        
        Args:
            pair: e.g., "EURUSD"
            period: "1h", "4h", "24h", "7d"
        
        Returns:
            {
                "type": "price",
                "pair": str,
                "timeframe": str,
                "candles": [{"time": str, "open": float, "high": float, "low": float, "close": float, "volume": int}],
                "signal_levels": {"entry": float, "stop": float, "target": float},
                "current_price": float
            }
        """
        try:
            # Map period to yfinance params
            period_map = {
                "1h": ("1d", "5m"),
                "4h": ("5d", "15m"),
                "24h": ("5d", "1h"),
                "7d": ("1mo", "1d"),
            }
            yf_period, yf_interval = period_map.get(period, ("5d", "1h"))
            
            # Download data
            ticker = f"{pair}=X"
            data = yf.download(ticker, period=yf_period, interval=yf_interval, progress=False, auto_adjust=True)
            
            if data.empty:
                return {"error": f"No data available for {pair}"}
            
            # Format candles
            candles = []
            for idx, row in data.iterrows():
                candles.append({
                    "time": idx.isoformat(),
                    "open": round(float(row["Open"]), 5),
                    "high": round(float(row["High"]), 5),
                    "low": round(float(row["Low"]), 5),
                    "close": round(float(row["Close"]), 5),
                    "volume": int(row["Volume"]) if "Volume" in row else 0,
                })
            
            # Get signal levels
            signal = signal_store.get_latest_for_pair(pair)
            signal_levels = None
            if signal:
                signal_levels = {
                    "entry_low": signal.get("entry_low"),
                    "entry_high": signal.get("entry_high"),
                    "stop": signal.get("stop_estimate"),
                    "target": signal.get("target_estimate"),
                    "direction": signal.get("direction"),
                }
            
            return {
                "type": "price",
                "pair": pair,
                "timeframe": period,
                "candles": candles,
                "signal_levels": signal_levels,
                "current_price": candles[-1]["close"] if candles else None,
            }
            
        except Exception as e:
            logger.error(f"Price chart generation failed for {pair}: {e}")
            return {"error": str(e)}
    
    def get_indicator_chart(self, pair: str, indicator: str, period: str = "24h") -> Dict:
        """
        Get technical indicator data.
        
        Args:
            pair: e.g., "EURUSD"
            indicator: "rsi", "macd", "bb" (Bollinger Bands)
            period: "1h", "4h", "24h", "7d"
        
        Returns:
            {
                "type": "indicator",
                "indicator": str,
                "pair": str,
                "timeframe": str,
                "data": [{"time": str, "value": float, ...}],
                "levels": {...}  # indicator-specific levels
            }
        """
        try:
            # Get price data first
            period_map = {
                "1h": ("1d", "5m"),
                "4h": ("5d", "15m"),
                "24h": ("5d", "1h"),
                "7d": ("1mo", "1d"),
            }
            yf_period, yf_interval = period_map.get(period, ("5d", "1h"))
            
            ticker = f"{pair}=X"
            data = yf.download(ticker, period=yf_period, interval=yf_interval, progress=False, auto_adjust=True)
            
            if data.empty:
                return {"error": f"No data available for {pair}"}
            
            close = data["Close"].values
            high = data["High"].values
            low = data["Low"].values
            timestamps = [idx.isoformat() for idx in data.index]
            
            if indicator == "rsi":
                rsi_values = self._calculate_rsi(close, period=14)
                chart_data = [
                    {"time": t, "rsi": round(float(v), 2)}
                    for t, v in zip(timestamps, rsi_values)
                    if not np.isnan(v)
                ]
                
                # Get current RSI from signal
                signal = signal_store.get_latest_for_pair(pair)
                current_rsi = signal.get("rsi14") if signal else None
                
                return {
                    "type": "indicator",
                    "indicator": "rsi",
                    "pair": pair,
                    "timeframe": period,
                    "data": chart_data,
                    "levels": {"oversold": 30, "overbought": 70},
                    "current_value": current_rsi,
                }
            
            elif indicator == "macd":
                macd_line, signal_line, histogram = self._calculate_macd(close)
                chart_data = [
                    {
                        "time": t,
                        "macd": round(float(m), 6),
                        "signal": round(float(s), 6),
                        "histogram": round(float(h), 6),
                    }
                    for t, m, s, h in zip(timestamps, macd_line, signal_line, histogram)
                    if not np.isnan(m)
                ]
                
                return {
                    "type": "indicator",
                    "indicator": "macd",
                    "pair": pair,
                    "timeframe": period,
                    "data": chart_data,
                    "levels": {"zero": 0},
                }
            
            elif indicator == "bb":
                middle, upper, lower = self._calculate_bollinger_bands(close)
                chart_data = [
                    {
                        "time": t,
                        "price": round(float(c), 5),
                        "middle": round(float(m), 5),
                        "upper": round(float(u), 5),
                        "lower": round(float(l), 5),
                    }
                    for t, c, m, u, l in zip(timestamps, close, middle, upper, lower)
                    if not np.isnan(m)
                ]
                
                return {
                    "type": "indicator",
                    "indicator": "bollinger_bands",
                    "pair": pair,
                    "timeframe": period,
                    "data": chart_data,
                }
            
            else:
                return {"error": f"Unknown indicator: {indicator}"}
                
        except Exception as e:
            logger.error(f"Indicator chart generation failed for {pair}/{indicator}: {e}")
            return {"error": str(e)}
    
    def get_agent_confidence_chart(self, pair: str) -> Dict:
        """
        Get agent confidence evolution over recent signals.
        
        Returns:
            {
                "type": "agent_confidence",
                "pair": str,
                "data": [{"time": str, "macro": float, "technical": float, "sentiment": float, "overall": float}]
            }
        """
        try:
            # This would ideally come from a history of signals
            # For now, we'll return the current signal's agent breakdown
            signal = signal_store.get_latest_for_pair(pair)
            
            if not signal:
                return {"error": f"No signal data for {pair}"}
            
            # Create a single data point (in production, you'd have historical data)
            data_point = {
                "time": signal.get("timestamp"),
                "macro": {
                    "regime": signal.get("macro_regime"),
                    "bull_prob": signal.get("regime_prob_bull", 0),
                    "neut_prob": signal.get("regime_prob_neut", 0),
                    "bear_prob": signal.get("regime_prob_bear", 0),
                },
                "technical": {
                    "signal": signal.get("tech_signal"),
                    "p_buy": signal.get("p_buy", 0),
                    "p_sell": signal.get("p_sell", 0),
                    "p_hold": signal.get("p_hold", 0),
                    "confidence": signal.get("model_conf", 0),
                },
                "sentiment": {
                    "signal": signal.get("sent_signal"),
                    "p_bullish": signal.get("p_bullish", 0),
                    "n_articles": signal.get("n_articles", 0),
                },
                "overall": {
                    "direction": signal.get("direction"),
                    "confidence": signal.get("confidence", 0),
                    "agreement": signal.get("agent_agreement"),
                }
            }
            
            return {
                "type": "agent_confidence",
                "pair": pair,
                "data": [data_point],
            }
            
        except Exception as e:
            logger.error(f"Agent confidence chart failed for {pair}: {e}")
            return {"error": str(e)}
    
    def get_risk_visualization(self, pair: str) -> Dict:
        """
        Get risk/reward visualization data.
        
        Returns:
            {
                "type": "risk",
                "pair": str,
                "current_price": float,
                "entry_range": [float, float],
                "stop_loss": float,
                "take_profit": float,
                "risk_pips": float,
                "reward_pips": float,
                "rr_ratio": float,
                "position_size": float,
                "risk_level": str
            }
        """
        try:
            signal = signal_store.get_latest_for_pair(pair)
            
            if not signal:
                return {"error": f"No signal data for {pair}"}
            
            from app.services.live_context_service import calculate_risk_metrics
            current_price = signal.get("price_at_signal", 0)
            risk_metrics = calculate_risk_metrics(signal, current_price)
            
            return {
                "type": "risk",
                "pair": pair,
                "direction": signal.get("direction"),
                "current_price": current_price,
                "entry_low": signal.get("entry_low"),
                "entry_high": signal.get("entry_high"),
                "stop_loss": signal.get("stop_estimate"),
                "take_profit": signal.get("target_estimate"),
                "risk_pips": risk_metrics["stop_distance_pips"],
                "reward_pips": risk_metrics["target_distance_pips"],
                "rr_ratio": risk_metrics["risk_reward_ratio"],
                "position_size": risk_metrics["position_risk_pct"],
                "risk_level": risk_metrics["risk_level"],
                "max_loss": risk_metrics["max_loss_estimate"],
            }
            
        except Exception as e:
            logger.error(f"Risk visualization failed for {pair}: {e}")
            return {"error": str(e)}
    
    # Helper methods for indicator calculations
    
    def _calculate_rsi(self, prices: np.ndarray, period: int = 14) -> np.ndarray:
        """Calculate RSI indicator"""
        deltas = np.diff(prices)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        avg_gain = np.zeros_like(prices)
        avg_loss = np.zeros_like(prices)
        
        # Initial averages
        avg_gain[period] = np.mean(gains[:period])
        avg_loss[period] = np.mean(losses[:period])
        
        # Smoothed averages
        for i in range(period + 1, len(prices)):
            avg_gain[i] = (avg_gain[i-1] * (period - 1) + gains[i-1]) / period
            avg_loss[i] = (avg_loss[i-1] * (period - 1) + losses[i-1]) / period
        
        rs = np.divide(avg_gain, avg_loss, out=np.zeros_like(avg_gain), where=avg_loss!=0)
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    def _calculate_macd(self, prices: np.ndarray, fast: int = 12, slow: int = 26, signal: int = 9):
        """Calculate MACD indicator"""
        ema_fast = self._ema(prices, fast)
        ema_slow = self._ema(prices, slow)
        macd_line = ema_fast - ema_slow
        signal_line = self._ema(macd_line, signal)
        histogram = macd_line - signal_line
        
        return macd_line, signal_line, histogram
    
    def _calculate_bollinger_bands(self, prices: np.ndarray, period: int = 20, std_dev: float = 2.0):
        """Calculate Bollinger Bands"""
        middle = self._sma(prices, period)
        std = np.zeros_like(prices)
        
        for i in range(period - 1, len(prices)):
            std[i] = np.std(prices[i - period + 1:i + 1])
        
        upper = middle + (std * std_dev)
        lower = middle - (std * std_dev)
        
        return middle, upper, lower
    
    def _ema(self, prices: np.ndarray, period: int) -> np.ndarray:
        """Calculate Exponential Moving Average"""
        ema = np.zeros_like(prices)
        ema[period - 1] = np.mean(prices[:period])
        multiplier = 2 / (period + 1)
        
        for i in range(period, len(prices)):
            ema[i] = (prices[i] - ema[i-1]) * multiplier + ema[i-1]
        
        return ema
    
    def _sma(self, prices: np.ndarray, period: int) -> np.ndarray:
        """Calculate Simple Moving Average"""
        sma = np.zeros_like(prices)
        
        for i in range(period - 1, len(prices)):
            sma[i] = np.mean(prices[i - period + 1:i + 1])
        
        return sma


# Global service instance
chart_service = ChartService()
