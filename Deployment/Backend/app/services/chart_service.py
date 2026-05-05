"""Chart data service - provides structured data for frontend chart rendering"""

from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

import numpy as np
import pandas as pd
import yfinance as yf
from loguru import logger

from app.config import settings
from app.services.signal_store import signal_store


class ChartService:
    """Generates chart data for various visualizations"""
    
    def __init__(self):
        self._cache = {}
        self._cache_ttl = 300  # 5 minutes
        self._correlation_cache = {}
        self._correlation_cache_time = {}
    
    def get_correlation_heatmap(self, pairs: List[str] = None, period: str = "24h") -> Dict:
        """
        Calculate correlation matrix between currency pairs.
        
        Args:
            pairs: List of pairs (e.g., ["EURUSD", "GBPUSD", "USDJPY"])
            period: "1h", "4h", "24h", "7d"
        
        Returns:
            {
                "type": "correlation_heatmap",
                "timeframe": str,
                "pairs": [str],
                "matrix": [[float]],  # correlation matrix
                "timestamp": str
            }
        """
        try:
            # Default pairs
            if pairs is None:
                pairs = ["EURUSD", "GBPUSD", "USDJPY"]
            
            # Check cache
            cache_key = f"{'-'.join(pairs)}_{period}"
            now = datetime.now(timezone.utc)
            if cache_key in self._correlation_cache_time:
                cache_age = (now - self._correlation_cache_time[cache_key]).total_seconds()
                if cache_age < self._cache_ttl:
                    logger.info(f"Returning cached correlation data (age: {cache_age:.0f}s)")
                    return self._correlation_cache[cache_key]
            
            # Map period to yfinance params
            period_map = {
                "1h": ("2d", "5m"),
                "4h": ("7d", "15m"),
                "24h": ("30d", "1h"),
                "7d": ("90d", "1d"),
            }
            yf_period, yf_interval = period_map.get(period, ("30d", "1h"))
            
            # Download data for all pairs
            price_data = {}
            for pair in pairs:
                ticker = f"{pair}=X" if not pair.endswith("=X") else pair
                clean_pair = pair.replace("=X", "")
                
                data = yf.download(ticker, period=yf_period, interval=yf_interval, progress=False, auto_adjust=True)
                
                if data.empty:
                    logger.warning(f"No data for {ticker}")
                    continue
                
                # Flatten MultiIndex if present
                if isinstance(data.columns, pd.MultiIndex):
                    data.columns = data.columns.get_level_values(0)
                
                # Extract close prices
                if "Close" in data.columns:
                    price_data[clean_pair] = data["Close"].values
                else:
                    logger.warning(f"No Close column for {ticker}")
            
            if len(price_data) < 2:
                return {"error": "Insufficient data to calculate correlations"}
            
            # Create DataFrame with aligned data
            min_length = min(len(prices) for prices in price_data.values())
            df = pd.DataFrame({
                pair: prices[-min_length:] for pair, prices in price_data.items()
            })
            
            # Calculate returns (percentage change)
            returns = df.pct_change().dropna()
            
            if len(returns) < 10:
                return {"error": "Insufficient data points for correlation"}
            
            # Calculate correlation matrix
            corr_matrix = returns.corr()
            
            # Convert to list format
            pairs_list = list(corr_matrix.columns)
            matrix = corr_matrix.values.tolist()
            
            result = {
                "type": "correlation_heatmap",
                "timeframe": period,
                "pairs": pairs_list,
                "matrix": matrix,
                "timestamp": now.isoformat(),
                "data_points": len(returns),
            }
            
            # Cache result
            self._correlation_cache[cache_key] = result
            self._correlation_cache_time[cache_key] = now
            
            logger.info(f"Calculated correlation matrix for {len(pairs_list)} pairs over {len(returns)} data points")
            return result
            
        except Exception as e:
            logger.error(f"Correlation heatmap generation failed: {e}")
            return {"error": str(e)}
    
    def get_price_chart(self, pair: str, period: str = "24h") -> Dict:
        """
        Get OHLC price data with signal overlays.
        
        Args:
            pair: e.g., "EURUSD" (will add =X suffix automatically)
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
            
            # Add =X suffix if not present
            ticker = f"{pair}=X" if not pair.endswith("=X") else pair
            
            # Download data
            data = yf.download(ticker, period=yf_period, interval=yf_interval, progress=False, auto_adjust=True)
            
            if data.empty:
                logger.warning(f"No data returned from yfinance for {ticker}")
                return {"error": f"No data available for {pair}"}
            
            # Flatten MultiIndex columns if present (yfinance returns MultiIndex for single ticker sometimes)
            if isinstance(data.columns, pd.MultiIndex):
                data.columns = data.columns.get_level_values(0)
            
            logger.info(f"Downloaded {len(data)} candles for {ticker}")
            
            # Format candles - use iloc for safer row access
            candles = []
            for idx in range(len(data)):
                try:
                    row = data.iloc[idx]
                    candle = {
                        "time": data.index[idx].isoformat(),
                        "open": round(float(row["Open"]), 5),
                        "high": round(float(row["High"]), 5),
                        "low": round(float(row["Low"]), 5),
                        "close": round(float(row["Close"]), 5),
                        "volume": int(row["Volume"]) if "Volume" in data.columns and not pd.isna(row["Volume"]) else 0,
                    }
                    candles.append(candle)
                except (KeyError, ValueError, TypeError, IndexError) as e:
                    logger.warning(f"Skipping candle at index {idx}: {e}")
                    continue
            
            if not candles:
                logger.error(f"No valid candles extracted from {len(data)} rows")
                return {"error": "Failed to parse candle data"}
            
            # Get signal levels (use pair without =X for signal store lookup)
            clean_pair = pair.replace("=X", "")
            signal = signal_store.get_latest_for_pair(clean_pair)
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
                "pair": clean_pair,
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
            pair: e.g., "EURUSD" (will add =X suffix automatically)
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
            
            # Add =X suffix if not present
            ticker = f"{pair}=X" if not pair.endswith("=X") else pair
            clean_pair = pair.replace("=X", "")
            
            data = yf.download(ticker, period=yf_period, interval=yf_interval, progress=False, auto_adjust=True)
            
            if data.empty:
                return {"error": f"No data available for {pair}"}
            
            # Flatten MultiIndex columns if present
            if isinstance(data.columns, pd.MultiIndex):
                data.columns = data.columns.get_level_values(0)
            
            # Check minimum data requirements
            min_required = 50  # Need at least 50 candles for indicators
            if len(data) < min_required:
                logger.warning(f"Insufficient data for {pair}: {len(data)} candles (need {min_required})")
                return {"error": f"Insufficient data: {len(data)} candles (need {min_required})"}
            
            # Extract arrays safely
            try:
                close = data["Close"].values if isinstance(data["Close"], pd.Series) else np.array(data["Close"])
                high = data["High"].values if isinstance(data["High"], pd.Series) else np.array(data["High"])
                low = data["Low"].values if isinstance(data["Low"], pd.Series) else np.array(data["Low"])
                timestamps = [idx.isoformat() for idx in data.index]
            except Exception as e:
                logger.error(f"Failed to extract price data: {e}")
                return {"error": f"Failed to parse price data: {str(e)}"}
            
            if indicator == "rsi":
                rsi_values = self._calculate_rsi(close, period=14)
                chart_data = [
                    {"time": t, "rsi": round(float(v), 2)}
                    for t, v in zip(timestamps, rsi_values)
                    if not np.isnan(v) and v > 0
                ]
                
                if not chart_data:
                    return {"error": "Failed to calculate RSI values"}
                
                # Get current RSI from signal
                signal = signal_store.get_latest_for_pair(clean_pair)
                current_rsi = signal.get("rsi14") if signal else None
                
                return {
                    "type": "indicator",
                    "indicator": "rsi",
                    "pair": clean_pair,
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
                    if not np.isnan(m) and not np.isnan(s)
                ]
                
                if not chart_data:
                    return {"error": "Failed to calculate MACD values"}
                
                return {
                    "type": "indicator",
                    "indicator": "macd",
                    "pair": clean_pair,
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
                
                if not chart_data:
                    return {"error": "Failed to calculate Bollinger Bands"}
                
                return {
                    "type": "indicator",
                    "indicator": "bollinger_bands",
                    "pair": clean_pair,
                    "timeframe": period,
                    "data": chart_data,
                }
            
            else:
                return {"error": f"Unknown indicator: {indicator}"}
                
        except Exception as e:
            logger.error(f"Indicator chart generation failed for {pair}/{indicator}: {e}")
            return {"error": str(e)}
    
    def get_agent_confidence_chart(self, pair: str, limit: int = 20) -> Dict:
        """
        Get agent confidence evolution over recent signals.
        
        Args:
            pair: Currency pair (e.g., "EURUSD")
            limit: Number of recent signals to include (default 20)
        
        Returns:
            {
                "type": "agent_confidence",
                "pair": str,
                "data": [{"time": str, "overall_confidence": float, "macro_conf": float, 
                         "tech_conf": float, "sent_conf": float, "direction": str, "agreement": str}]
            }
        """
        try:
            # Load historical signals from CSV
            if not settings.SIGNALS_CSV.exists():
                logger.warning("No signals.csv found for historical data")
                return {"error": "No historical data available"}
            
            df = pd.read_csv(settings.SIGNALS_CSV)
            
            if df.empty:
                return {"error": "No historical data available"}
            
            # Filter for this pair
            clean_pair = pair.replace("=X", "")
            pair_df = df[df["pair"].str.replace("=X", "") == clean_pair].copy()
            
            if pair_df.empty:
                return {"error": f"No historical data for {pair}"}
            
            # Sort by timestamp descending and take most recent
            if "timestamp" in pair_df.columns:
                pair_df["timestamp"] = pd.to_datetime(pair_df["timestamp"], utc=True, errors="coerce")
                pair_df = pair_df.sort_values("timestamp", ascending=False)
            
            # Take last N signals
            pair_df = pair_df.head(limit)
            
            # Reverse to show oldest to newest
            pair_df = pair_df.iloc[::-1]
            
            # Build data points
            data_points = []
            for _, row in pair_df.iterrows():
                data_point = {
                    "time": row.get("timestamp").isoformat() if pd.notna(row.get("timestamp")) else "",
                    "overall_confidence": float(row.get("confidence", 0)),
                    "macro_conf": float(row.get("macro_conf", 0)),
                    "tech_conf": float(row.get("tech_conf", 0)),
                    "sent_conf": float(row.get("sent_conf", 0)),
                    "direction": str(row.get("direction", "HOLD")),
                    "agreement": str(row.get("agent_agreement", "UNKNOWN")),
                    # Additional agent details for tooltip/detail view
                    "macro_regime": str(row.get("macro_regime", "")),
                    "tech_signal": str(row.get("tech_signal", "")),
                    "sent_signal": str(row.get("sent_signal", "")),
                }
                data_points.append(data_point)
            
            if not data_points:
                return {"error": "No valid data points found"}
            
            return {
                "type": "agent_confidence",
                "pair": clean_pair,
                "data": data_points,
                "count": len(data_points),
            }
            
        except Exception as e:
            logger.error(f"Agent confidence chart failed for {pair}: {e}")
            return {"error": str(e)}
    
    def get_volatility_chart(self, pair: str, period: str = "24h") -> Dict:
        """
        Get ATR (Average True Range) volatility chart.
        
        Args:
            pair: Currency pair (e.g., "EURUSD")
            period: "1h", "4h", "24h", "7d"
        
        Returns:
            {
                "type": "volatility",
                "pair": str,
                "timeframe": str,
                "data": [{"time": str, "atr": float, "high": float, "low": float, "close": float}],
                "current_atr": float,
                "avg_atr": float,
                "volatility_state": str  # "low", "normal", "high", "extreme"
            }
        """
        try:
            # Map period to yfinance params
            period_map = {
                "1h": ("2d", "5m"),
                "4h": ("7d", "15m"),
                "24h": ("30d", "1h"),
                "7d": ("90d", "1d"),
            }
            yf_period, yf_interval = period_map.get(period, ("30d", "1h"))
            
            # Add =X suffix if not present
            ticker = f"{pair}=X" if not pair.endswith("=X") else pair
            clean_pair = pair.replace("=X", "")
            
            # Download data
            data = yf.download(ticker, period=yf_period, interval=yf_interval, progress=False, auto_adjust=True)
            
            if data.empty:
                logger.warning(f"No data returned from yfinance for {ticker}")
                return {"error": f"No data available for {pair}"}
            
            # Flatten MultiIndex columns if present
            if isinstance(data.columns, pd.MultiIndex):
                data.columns = data.columns.get_level_values(0)
            
            # Check minimum data requirements
            min_required = 30  # Need at least 30 candles for ATR
            if len(data) < min_required:
                logger.warning(f"Insufficient data for {pair}: {len(data)} candles (need {min_required})")
                return {"error": f"Insufficient data: {len(data)} candles (need {min_required})"}
            
            # Extract OHLC data
            high = data["High"].values
            low = data["Low"].values
            close = data["Close"].values
            timestamps = [idx.isoformat() for idx in data.index]
            
            # Calculate ATR (14 period)
            atr_period = 14
            atr_values = self._calculate_atr(high, low, close, period=atr_period)
            
            # Format chart data
            chart_data = []
            for i in range(len(timestamps)):
                if not np.isnan(atr_values[i]) and atr_values[i] > 0:
                    chart_data.append({
                        "time": timestamps[i],
                        "atr": round(float(atr_values[i]), 6),
                        "high": round(float(high[i]), 5),
                        "low": round(float(low[i]), 5),
                        "close": round(float(close[i]), 5),
                    })
            
            if not chart_data:
                return {"error": "Failed to calculate ATR values"}
            
            # Calculate statistics
            valid_atr = [d["atr"] for d in chart_data]
            current_atr = valid_atr[-1]
            avg_atr = np.mean(valid_atr)
            std_atr = np.std(valid_atr)
            
            # Determine volatility state
            z_score = (current_atr - avg_atr) / std_atr if std_atr > 0 else 0
            
            if z_score > 2:
                volatility_state = "extreme"
            elif z_score > 1:
                volatility_state = "high"
            elif z_score < -1:
                volatility_state = "low"
            else:
                volatility_state = "normal"
            
            return {
                "type": "volatility",
                "pair": clean_pair,
                "timeframe": period,
                "data": chart_data,
                "current_atr": round(current_atr, 6),
                "avg_atr": round(avg_atr, 6),
                "std_atr": round(std_atr, 6),
                "volatility_state": volatility_state,
                "z_score": round(z_score, 2),
            }
            
        except Exception as e:
            logger.error(f"Volatility chart generation failed for {pair}: {e}")
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
        if len(prices) < period + 1:
            logger.warning(f"Insufficient data for RSI: {len(prices)} prices (need {period + 1})")
            return np.full_like(prices, np.nan)
        
        deltas = np.diff(prices)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        avg_gain = np.zeros(len(prices))
        avg_loss = np.zeros(len(prices))
        
        # Initial averages (need at least 'period' deltas)
        if len(gains) >= period:
            avg_gain[period] = np.mean(gains[:period])
            avg_loss[period] = np.mean(losses[:period])
        
        # Smoothed averages
        for i in range(period + 1, len(prices)):
            avg_gain[i] = (avg_gain[i-1] * (period - 1) + gains[i-1]) / period
            avg_loss[i] = (avg_loss[i-1] * (period - 1) + losses[i-1]) / period
        
        # Calculate RS and RSI
        rs = np.divide(avg_gain, avg_loss, out=np.zeros_like(avg_gain), where=avg_loss!=0)
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    def _calculate_macd(self, prices: np.ndarray, fast: int = 12, slow: int = 26, signal: int = 9):
        """Calculate MACD indicator"""
        if len(prices) < slow + signal:
            logger.warning(f"Insufficient data for MACD: {len(prices)} prices (need {slow + signal})")
            return np.full_like(prices, np.nan), np.full_like(prices, np.nan), np.full_like(prices, np.nan)
        
        ema_fast = self._ema(prices, fast)
        ema_slow = self._ema(prices, slow)
        macd_line = ema_fast - ema_slow
        signal_line = self._ema(macd_line, signal)
        histogram = macd_line - signal_line
        
        return macd_line, signal_line, histogram
    
    def _calculate_bollinger_bands(self, prices: np.ndarray, period: int = 20, std_dev: float = 2.0):
        """Calculate Bollinger Bands"""
        if len(prices) < period:
            logger.warning(f"Insufficient data for Bollinger Bands: {len(prices)} prices (need {period})")
            return np.full_like(prices, np.nan), np.full_like(prices, np.nan), np.full_like(prices, np.nan)
        
        middle = self._sma(prices, period)
        std = np.zeros_like(prices, dtype=float)
        std[:period-1] = np.nan
        
        for i in range(period - 1, len(prices)):
            std[i] = np.std(prices[i - period + 1:i + 1])
        
        upper = middle + (std * std_dev)
        lower = middle - (std * std_dev)
        
        return middle, upper, lower
    
    def _calculate_atr(self, high: np.ndarray, low: np.ndarray, close: np.ndarray, period: int = 14) -> np.ndarray:
        """
        Calculate Average True Range (ATR).
        
        ATR measures volatility by calculating the average of true ranges over a period.
        True Range is the greatest of:
        - Current High - Current Low
        - abs(Current High - Previous Close)
        - abs(Current Low - Previous Close)
        """
        if len(high) < period + 1:
            logger.warning(f"Insufficient data for ATR: {len(high)} candles (need {period + 1})")
            return np.full_like(high, np.nan)
        
        # Calculate True Range
        tr = np.zeros(len(high))
        
        for i in range(1, len(high)):
            hl = high[i] - low[i]
            hc = abs(high[i] - close[i-1])
            lc = abs(low[i] - close[i-1])
            tr[i] = max(hl, hc, lc)
        
        # Calculate ATR using EMA smoothing
        atr = np.zeros_like(high, dtype=float)
        atr[:period] = np.nan
        
        # Initial ATR is simple average of first 'period' TRs
        atr[period] = np.mean(tr[1:period+1])
        
        # Subsequent ATRs use smoothing: ATR = ((prior ATR * (period-1)) + current TR) / period
        for i in range(period + 1, len(high)):
            atr[i] = ((atr[i-1] * (period - 1)) + tr[i]) / period
        
        return atr
        for i in range(period - 1, len(prices)):
            std[i] = np.std(prices[i - period + 1:i + 1])
        
        upper = middle + (std * std_dev)
        lower = middle - (std * std_dev)
        
        return middle, upper, lower
    
    def _ema(self, prices: np.ndarray, period: int) -> np.ndarray:
        """Calculate Exponential Moving Average"""
        if len(prices) < period:
            logger.warning(f"Insufficient data for EMA: {len(prices)} prices (need {period})")
            return np.full_like(prices, np.nan)
        
        ema = np.zeros_like(prices, dtype=float)
        ema[:] = np.nan  # Initialize all as NaN
        
        # Find first valid index (skip leading NaNs)
        valid_indices = np.where(~np.isnan(prices))[0]
        if len(valid_indices) < period:
            logger.warning(f"Insufficient valid data for EMA: {len(valid_indices)} valid prices (need {period})")
            return ema
        
        first_valid = valid_indices[0]
        
        # Need 'period' valid values to start
        if first_valid + period > len(prices):
            logger.warning(f"Not enough data after first valid index for EMA")
            return ema
        
        # Calculate initial EMA from first 'period' valid values
        start_idx = first_valid + period - 1
        ema[start_idx] = np.mean(prices[first_valid:first_valid + period])
        multiplier = 2 / (period + 1)
        
        # Calculate EMA for remaining values
        for i in range(start_idx + 1, len(prices)):
            if not np.isnan(prices[i]):
                ema[i] = (prices[i] - ema[i-1]) * multiplier + ema[i-1]
            else:
                ema[i] = ema[i-1]  # Carry forward previous EMA if current price is NaN
        
        return ema
    
    def _sma(self, prices: np.ndarray, period: int) -> np.ndarray:
        """Calculate Simple Moving Average"""
        if len(prices) < period:
            logger.warning(f"Insufficient data for SMA: {len(prices)} prices (need {period})")
            return np.full_like(prices, np.nan)
        
        sma = np.zeros_like(prices, dtype=float)
        sma[:period-1] = np.nan  # First values are NaN
        
        for i in range(period - 1, len(prices)):
            sma[i] = np.mean(prices[i - period + 1:i + 1])
        
        return sma


# Global service instance
chart_service = ChartService()
